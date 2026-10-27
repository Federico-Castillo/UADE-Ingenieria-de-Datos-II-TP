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
Proveedores y Operadores Logísticos. El resto de las opciones del menú
principal están reservadas como "próximamente".

> **Nota Windows:** `getpass.getpass()` (usado para la contraseña en el alta de
> Usuario) lee directo de la consola, no de stdin redirigido — no se puede
> automatizar ese flujo por pipe, solo funciona en una terminal interactiva real.

## Tests

Requieren `docker-compose up -d` y el esquema de MySQL ya creado:

```bash
python -m pytest -m integration -v
```

## Logs

Se escriben en `logs/app.log` (nivel controlado por `LOG_LEVEL` en `.env`).

## Notas técnicas

- Acceso a MySQL con SQL parametrizado (`mysql-connector-python`) dentro de
  clases Repository, sin ORM.
- `app/db/` tiene un módulo de conexión por motor, reusable por futuros scripts
  (ej. el simulador de sensores IoT reusará `app/db/cassandra_client.py`).
- Jerarquía de excepciones propia en `app/core/exceptions.py`; el Repository
  traduce errores de driver, el Service valida reglas de negocio, la CLI es la
  única capa que atrapa excepciones para mostrarlas sin traceback.
- `cassandra-driver` en Python 3.12 necesita forzar `AsyncioConnection`
  explícitamente (ver comentario en `app/db/cassandra_client.py` y
  `app/db/_cassandra_compat.py`) porque el driver no tiene fallback a asyncio
  en su selección automática y `asyncore` fue removido del stdlib en 3.12.
