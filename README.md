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
cliente-operador), y Monitoreo IoT (Cassandra) — el alta de factura/pago
actualiza el saldo de forma transaccional, y los Services de Mongo/Neo4j/
Cassandra validan sus referencias a MySQL en la capa de aplicación (no hay FK
nativas cross-engine). **Los 5 motores del TP ya tienen código real.** El
registro de una lectura de sensor dispara automáticamente el pipeline
Cassandra → MongoDB → Redis del desafío de complejidad adicional: si viola
una Regla activa, se crea un Incidente y una Alerta vinculados. Solo
Inteligencia Analítica queda como "próximamente" en el menú.

> **Nota Windows:** `getpass.getpass()` (usado para la contraseña en el alta de
> Usuario) lee directo de la consola, no de stdin redirigido — no se puede
> automatizar ese flujo por pipe, solo funciona en una terminal interactiva real.

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
