# TP Persistencia Políglota — Ingeniería de Datos II (UADE)

Plataforma de gestión de logística internacional y monitoreo de cargas IoT, con
persistencia políglota en 5 motores: MySQL (relacional), MongoDB (documental),
Neo4j (grafos), Redis (clave-valor), Cassandra (tabular).

El diseño completo (justificación de motores, modelado físico, desafío de
complejidad adicional) está en `UADE-Ingenieria-de-Datos-II-TP-tools/1. Primera
Entrega/`.

## Requisitos

- Python 3.12+
- Docker + docker-compose (para levantar los 5 motores)

## Setup

```bash
python -m venv venv
# Windows:
venv\Scripts\pip install -r requirements.txt
# resto de los comandos con venv\Scripts\python en vez de python

copy .env.example .env    # los valores por defecto ya matchean docker-compose.yml

docker-compose up -d
```

## Crear el esquema en los 5 motores

```bash
python scripts/schema/init_all.py
```

Imprime un resumen OK/ERROR por motor al final. También se pueden correr
individualmente: `python scripts/schema/mysql_schema.py`,
`mongo_schema.py`, `neo4j_schema.py`, `cassandra_schema.py` (Redis no tiene
esquema, ver `scripts/schema/redis_conventions.md`).

## Correr la app

```bash
python main.py
```

Implementados de punta a punta: Clientes, Usuarios, Roles, Sesiones (Redis),
Proveedores, Operadores Logísticos, Contenedores, Sensores IoT, Vehículos,
Envíos (con asignación de Contenedores vía `envio_contenedor`), Reglas,
Alertas (Redis), Facturas/Pagos/Cuentas Corrientes (clientes), Facturas
Recibidas/Pagos Emitidos/Cuentas Corrientes Pagables (proveedores/operadores),
Reportes, Eventos Logísticos/Incidentes/Mensajería/Grupos de Trabajo/
Predicciones de Riesgo (MongoDB), Tramos/Rutas (Neo4j, con las 2 "Consultas
Avanzadas" de la consigna: ruta completa de un envío y red de relaciones
cliente-operador, más costos por tipo de transporte), Monitoreo IoT
(Cassandra), Reportes Operativos y Analíticos (agregaciones cross-engine:
envíos por país/estado/cliente, tiempos de entrega, incidentes promedio,
análisis predictivo de riesgos, rankings de rutas/clientes), el Worker de
Outbox (sincronización MySQL -> Neo4j del desafío de complejidad adicional),
predicción real de atrasos con scikit-learn, y visualización geográfica de
GPS (mapa HTML por contenedor) — el alta de factura/pago
actualiza el saldo de forma transaccional, y los Services de Mongo/Neo4j/
Cassandra validan sus referencias a MySQL en la capa de aplicación (no hay FK
nativas cross-engine). **Los 5 motores del TP ya tienen código real.** El
registro de una lectura de sensor dispara automáticamente el pipeline
Cassandra → MongoDB → Redis del desafío de complejidad adicional: si viola
una Regla activa, se crea un Incidente y una Alerta vinculados. Dos procesos
periódicos de la consigna ya implementados: Cierre Mensual de Cuentas
Corrientes (snapshot idempotente del saldo por período, clientes y
proveedores/operadores) y Detección de Sensores Inactivos (compara la última
lectura en Cassandra contra un umbral de horas, marca el sensor y genera una
Alerta). No queda nada como "próximamente" en el menú.

> **Nota Windows:** `getpass.getpass()` (usado para la contraseña en el alta de
> Usuario) lee directo de la consola, no de stdin redirigido — no se puede
> automatizar ese flujo por pipe, solo funciona en una terminal interactiva real.

## Datos de prueba para la defensa

```bash
python scripts/seed_datos_prueba.py                     # limpia y carga un set chico (DEMO_)
python scripts/seed_datos_prueba.py --solo-limpiar        # solo borra los datos DEMO_
```

Reusa los Services existentes de punta a punta (nada de SQL/Cypher nuevo):
6 clientes, proveedores/operadores, vehículos, contenedores+sensores,
reglas, 18 envíos con variedad de estados, facturación (clientes y
proveedores/operadores, con saldos pagado/parcial/pendiente), tramos con
costo, eventos logísticos, incidentes, mensajería, predicciones de riesgo, y
metadata de Reporte — en los 5 motores. Al final corre la actividad
derivada: unos ticks del simulador IoT (deja 2 sensores sin lecturas a
propósito), el cierre mensual del período actual, y la detección de
sensores inactivos, para que esos procesos periódicos y los reportes
operativos no aparezcan vacíos. Todo el texto identificable lleva el
prefijo `DEMO_` (mismo criterio que `TEST_` en los tests, namespace
distinto a propósito) y el script limpia sus propios datos antes de cargar,
así que se puede re-correr sin acumular duplicados.

## Simulador de sensores IoT

No hay hardware real (decisión de alcance del TP). Este script inserta
lecturas sintéticas en Cassandra para los sensores ya dados de alta (menú
"Gestión de Sensores IoT"), con valores normales la mayor parte del tiempo y
anomalías ocasionales que disparan el pipeline completo
Cassandra → MongoDB → Redis (Incidente + Alerta) si hay una Regla activa para
ese tipo de sensor:

```bash
python scripts/simulador_iot.py                        # loop cada 10s hasta Ctrl+C
python scripts/simulador_iot.py --once                  # un solo tick y termina
python scripts/simulador_iot.py --interval 5 --anomaly-prob 0.2
```

## Tests

Requieren `docker-compose up -d` y el esquema de MySQL ya creado:

```bash
python -m pytest -m integration -v   # tests de integración (contra las DB reales)
python -m pytest -v                  # + los unitarios (ej. lógica del simulador, sin DB)
```

## Procesos periódicos

No hay scheduler automático en el alcance del TP: se corren a demanda desde
sus menús en `main.py`.

- **Cierre Mensual de Cuentas Corrientes:** registra, para el período
  indicado (`'YYYY-MM'`, default el mes actual), un snapshot del saldo vivo
  de cada cuenta (`cuenta_corriente` y `cuenta_corriente_pagable`) en
  `cierre_cuenta_corriente`/`cierre_cuenta_corriente_pagable`. No resetea el
  saldo real — es historial de resúmenes mensuales. Reejecutar el cierre de
  un período ya cerrado actualiza el snapshot (upsert por `(id_cliente,
  periodo)` o `(id_proveedor/id_operador_logistico, periodo)`) en vez de
  duplicarlo.
- **Detección de Sensores Inactivos:** compara la última lectura de cada
  sensor activo en Cassandra contra un umbral de horas (default 24hs); el
  que no tiene lecturas recientes (o nunca tuvo) se marca `estado='inactivo'`
  en MySQL y genera una `Alerta` en Redis (`tipo='sensor_inactivo'`).

## Reportes operativos y analíticos

Menú "Reportes Operativos y Analíticos" (`app/services/reporte_operativo_service.py`):
agregaciones de solo lectura, resueltas a nivel aplicación uniendo MySQL
(Envio/Cliente) con MongoDB (Incidente/EventoLogistico/PrediccionRiesgo) —
envíos por país/estado/cliente, envíos demorados, incidentes abiertos,
tiempos de envío por cliente (mín/máx/promedio) y tiempo promedio de entrega
global (calculado contra el `EventoLogistico` con `tipo_evento='entregado'`
de cada envío), incidentes promedio por país/estado/cliente, análisis
predictivo de riesgos (umbral de probabilidad de demora), costos por tipo
de transporte (`Tramo.costo` en Neo4j, agregación nativa `AVG`/`SUM`
agrupada por `medio_transporte`), y 2 rankings: rutas (par origen/destino
del envío) con más incidentes, y clientes por volumen transportado (suma de
`Contenedor.capacidad`, agregación 100% MySQL vía `envio_contenedor`).
Separado a propósito de "Gestión de Reportes", que solo registra metadata
del pedido (`Reporte`/`ReporteService`) sin calcular nada.

## Worker de Outbox

Patrón Outbox transaccional + worker asíncrono (desafío de complejidad
adicional, punto 4): `ClienteRepository`/`EnvioRepository` encolan un evento
en `outbox_eventos`, en la MISMA transacción que el alta/modificación/baja,
para que la propagación a Neo4j nunca se pierda por una caída justo después
del commit. El worker lee los eventos `pendiente` y proyecta
`:Cliente`/`:Envio` vía `MERGE` (idempotente — reintentar nunca duplica
nodos) o, en una baja de Envío, hace `DETACH DELETE` del nodo (evita la
"referencia huérfana" que describe el propio desafío). Tras varios fallos
(default 5) el evento pasa a `dead_letter` en vez de reintentar para
siempre.

```bash
python worker/outbox_worker.py                # loop cada 5s hasta Ctrl+C
python worker/outbox_worker.py --once          # un solo ciclo y termina
```

También hay un menú "Worker de Outbox" en `main.py` para inspeccionar
pendientes/dead-letter y correr un ciclo manual sin salir de la app.

## Predicción de atrasos con scikit-learn

Menú "Predicciones de Riesgo" -> "Calcular predicciones reales con
scikit-learn" (`app/services/prediccion_ml_service.py`): entrena un
`LogisticRegression` sobre los envíos con resultado conocido
(`estado` `entregado`/`demorado`) y predice la probabilidad de demora de los
que todavía están `pendiente`/`en_transito`, persistiendo el resultado en
`PrediccionRiesgo` (Mongo) — reemplaza la carga manual por un cálculo real.
Features: prioridad, medio de transporte del primer tramo, tasa histórica
de demora del cliente (sobre sus otros envíos, nunca el propio, para no
entrenar con fuga del resultado) y cantidad de envíos previos del cliente.
Valida que haya suficientes muestras y más de una clase antes de entrenar.

## Visualización geográfica de GPS

La app es de consola — no hay ventana propia donde dibujar un mapa — así
que "visualizar" las posiciones GPS de un contenedor es generar un archivo
HTML standalone (folium/Leaflet) que se abre aparte en el navegador. Menú
"Monitoreo IoT: Lecturas de Sensor" -> "Generar mapa GPS de un contenedor":
usa `LecturaSensorService.listar_por_contenedor()` (nuevo — combina y
ordena las lecturas de TODOS los sensores del contenedor, no de uno en
particular, resolviendo de paso la reconstrucción del recorrido) y guarda
el mapa en `output/mapas/contenedor_{id}.html` (gitignored).

## Logs

Se escriben en `logs/app.log` (nivel controlado por `LOG_LEVEL` en `.env`).

## Notas técnicas

- Acceso a MySQL con SQL parametrizado (`mysql-connector-python`) dentro de
  clases Repository, sin ORM.
- `app/db/` tiene un módulo de conexión por motor, reusado tal cual por
  `scripts/simulador_iot.py` (vía `LecturaSensorService`/`SensorIoTRepository`,
  sin nada atado a la CLI).
- `CAMPO_POR_TIPO_SENSOR` vive en `app/domain/lectura_sensor.py` (no en el
  Service) justamente para que el simulador y `LecturaSensorService` usen el
  mismo mapeo tipo→campo sin duplicarlo.
- Jerarquía de excepciones propia en `app/core/exceptions.py`; el Repository
  traduce errores de driver, el Service valida reglas de negocio, la CLI es la
  única capa que atrapa excepciones para mostrarlas sin traceback.
- `cassandra-driver` en Python 3.12 necesita forzar `AsyncioConnection`
  explícitamente (ver comentario en `app/db/cassandra_client.py` y
  `app/db/_cassandra_compat.py`) porque el driver no tiene fallback a asyncio
  en su selección automática y `asyncore` fue removido del stdlib en 3.12.
