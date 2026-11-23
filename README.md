# TP Persistencia Políglota — Ingeniería de Datos II (UADE)

Plataforma de gestión de logística internacional y monitoreo de cargas IoT, con
persistencia políglota en 5 motores: MySQL (relacional), MongoDB (documental),
Neo4j (grafos), Redis (clave-valor), Cassandra (tabular).

Tiene dos interfaces sobre los mismos Services (no hay lógica de negocio en
ninguna): una **consola** (`main.py`) y una **interfaz web** (`main_nicegui.py`)
que cubre lo mismo, más reportes con gráficos, mapas, un grafo de Neo4j y una
demo guiada de rollback entre motores.

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
python main.py            # interfaz de consola
python main_nicegui.py    # interfaz web: abre http://localhost:8090
```

Las dos pueden usarse a la vez. La web verifica los 5 motores al arrancar e
informa cuál no responde (arranca igual, ver más abajo).

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
Alerta). No queda nada como "próximamente" en el menú de la consola.

> **Nota Windows:** `getpass.getpass()` (usado para la contraseña en el alta de
> Usuario) lee directo de la consola, no de stdin redirigido — no se puede
> automatizar ese flujo por pipe, solo funciona en una terminal interactiva real.

## Interfaz web (NiceGUI)

```bash
python main_nicegui.py        # http://localhost:8090
```

**Seguridad.** La UI no tiene autenticación y puede dar de baja datos y hasta
detener contenedores de Docker, por eso escucha **solo en `127.0.0.1`** (la propia
máquina). Para abrirla desde otro equipo hay que pedirlo a propósito
(`UI_HOST=0.0.0.0 python main_nicegui.py`) y la app lo avisa en pantalla y en el log.

Un encabezado común a todas las pantallas muestra una insignia verde/roja por
motor (se actualiza cada 3 segundos). Al arrancar, `main_nicegui.py` chequea
los 5 motores (login/ping real, con timeout) y, si alguno no responde, lo
informa junto con el comando para levantarlo; la interfaz abre igual porque
apagar un motor a propósito es parte de la demo de rollback.

| Pantalla | Qué hace |
|---|---|
| `/abm` | ABM por entidad: tabla con selección y botones Nuevo / Editar (formulario precargado) / Baja o Eliminar (con confirmación), filtros del listado y búsqueda. 18 entidades. |
| `/` (Explorador) | Cualquier método de cualquier Service: se elige entidad y operación, el formulario se arma solo y el resultado sale en tabla. Cubre también los procesos especiales (cierres, outbox, predicción, sensores inactivos...). `/?entidad=cliente` preselecciona la entidad. |
| `/envio` | Ficha 360° de un envío: datos y cliente (MySQL), contenedores y sensores (MySQL), última lectura y recorrido GPS (Cassandra), incidentes, predicción de riesgo y eventos (MongoDB), ruta como grafo (Neo4j) y alertas activas (Redis). Cada tarjeta carga y falla por separado: con un motor caído, solo su tarjeta avisa. |
| `/reportes` | Los reportes operativos y analíticos con gráficos, en 5 pestañas (envíos, incidentes, desempeño histórico, riesgo de atrasos, transporte y clientes), y botón para recalcular las predicciones de ML. |
| `/alertas` | Alertas activas con actualización automática y resolución, y un simulador de sensores IoT en vivo (una lectura, un tick o continuo) que dispara el pipeline Cassandra → MongoDB → Redis. |
| `/transaccion` | Demo guiada del rollback de una transacción poliglota (ver abajo). |
| `/red` | Grafo de Neo4j: red cliente-operador y ruta de un envío. |
| `/mapa` | Recorrido GPS de un contenedor (folium/Leaflet embebido). |

**Cómo está hecha.** No hay una pantalla por entidad: `app/ui/reflexion.py`
lee la firma y los type hints de cada método de cada Service y arma el
formulario (los dataclasses se expanden en campos; soporta números, fechas,
listas separadas por coma y diccionarios en JSON). `app/ui/registro.py`
descubre los Services de `app/services/`, así que agregar un Service o un
método nuevo lo expone solo. Sobre esa base:

- **Desplegables de valores fijos** (`app/ui/opciones.py`): salen de fuentes
  que el proyecto ya tiene (las constantes `_XXX_VALIDOS` de los Services, los
  ENUM de `mysql_schema.sql` y `CAMPO_POR_TIPO_SENSOR`), no de listas copiadas.
- **Desplegables de claves foráneas** (`app/ui/referencias.py`): todo campo
  `id_<entidad>` se elige entre los registros reales (`70 · Razón social ·
  mail`) en lugar de tipear el número. Si el Service referenciado no tiene un
  listado simple, el campo queda como texto.
- **Confirmación** antes de bajas, eliminaciones y procesos que modifican
  datos en bloque; las contraseñas se enmascaran y el `password_hash` (que
  calcula el Service) nunca se pide.
- El ABM detecta sus botones por convención de nombres y firmas
  (`app/ui/abm.py`): una entidad sin `modificar` no muestra "Editar", una sin
  baja no muestra "Baja" (por ejemplo, la factura es un documento contable).
  Los incidentes no se borran: su botón es **Cerrar** (pasan a estado
  `cerrado` y quedan en el historial); el `eliminar` del Service existe solo
  como compensación del rollback.

Limitación conocida: las entidades sin un `listar` simple (pagos, lecturas de
sensores, mensajes, alertas, tramos...) no tienen tabla en `/abm`; se operan
desde el Explorador.

### Demo del rollback entre motores

El registro de una lectura anómala crea un Incidente en MongoDB y una Alerta
en Redis. Entre dos motores no existe un `COMMIT` único (2PC), así que la
atomicidad se logra a mano: se confirma el Incidente y, si la Alerta falla, se
**compensa** eliminando el Incidente en vez de dejarlo huérfano
(`LecturaSensorService._registrar_incidente_y_alerta_transaccional`). La
lectura en Cassandra nunca se pierde.

En `/transaccion`: enviar una lectura anómala con todo encendido (COMMIT) →
**Detener Redis** (ejecuta `docker stop redis`, con confirmación) → enviar otra
(ROLLBACK: la tabla muestra que los incidentes no cambiaron, y abajo se ven las
líneas del log que lo documentan) → **Iniciar Redis**. El mismo guion en
consola:

```bash
docker stop redis
python scripts/simulador_iot.py --once --anomaly-prob 1.0
# logs/app.log: "se revierte el incidente (rollback)" / "Incidente eliminado (rollback)"
docker start redis
```

## Datos de prueba para la defensa

```bash
python scripts/seed_datos_prueba.py                     # limpia y carga un set chico (DEMO_)
python scripts/seed_datos_prueba.py --solo-limpiar        # solo borra los datos DEMO_
```

Para empezar de cero (borra los datos de los 5 motores): `docker-compose down -v`,
`docker-compose up -d`, esperar a que Neo4j y Cassandra estén listos (tardan más
que el resto; si el esquema falla, reintentar) y volver a correr
`init_all.py` y el seed.

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

No hay hardware real. Este script inserta lecturas sintéticas en Cassandra 
para los sensores ya dados de alta (menú"Gestión de Sensores IoT"), 
con valores normales la mayor parte del tiempo yanomalías ocasionales 
que disparan el pipeline completo Cassandra → MongoDB → Redis (Incidente + Alerta) 
si hay una Regla activa para ese tipo de sensor:

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
python -m pytest tests/test_ui_*.py  # solo los de la interfaz web: no necesitan Docker
```

Los de `tests/test_ui_*.py` prueban la lógica de la interfaz (reflexión de
firmas, detección del ABM, desplegables, ficha del envío, grafos, chequeo de
motores) con Services falsos, sin motores ni navegador. Lo que queda sin test
automático son los clics y el aspecto de las pantallas.

## Procesos periódicos

No hay scheduler automático: se corren a demanda desde sus menús en `main.py`.

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

Desde la consola no hay ventana propia donde dibujar un mapa — así que
"visualizar" las posiciones GPS de un contenedor es generar un archivo
HTML standalone (folium/Leaflet) que se abre aparte en el navegador (la
interfaz web, en cambio, lo muestra embebido en `/mapa` y en la ficha del
envío). Menú
"Monitoreo IoT: Lecturas de Sensor" -> "Generar mapa GPS de un contenedor":
usa `LecturaSensorService.listar_por_contenedor()` (nuevo — combina y
ordena las lecturas de TODOS los sensores del contenedor, no de uno en
particular, resolviendo de paso la reconstrucción del recorrido) y guarda
el mapa en `output/mapas/contenedor_{id}.html` (gitignored).

## Logs

Se escriben en `logs/app.log` (nivel controlado por `LOG_LEVEL` en `.env`).

## Notas técnicas

- `app/ui/` es la capa de presentación web (NiceGUI), en tres niveles:
  `principal.py` solo arranca el servidor; `paginas/` tiene un módulo por
  pantalla (`explorador`, `entidades` = ABM, `envio`, `reportes`, `alertas`,
  `transaccion`, `red`, `mapa`) y `comun.py` las piezas que comparten
  (encabezado, llamadas a Services con manejo de errores, confirmación,
  formularios generados). El resto es lógica pura sin NiceGUI y testeable sola
  (`reflexion`, `abm`, `opciones`, `referencias`, `ficha`, `grafos`, `salud`,
  `registro`). Solo usa Services, nunca Repositories ni drivers, salvo
  `salud.py`, que abre conexiones propias de vida corta para chequear cada
  motor sin tocar los singletons de `app/db/`.
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
