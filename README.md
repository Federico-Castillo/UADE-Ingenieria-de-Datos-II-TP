# TP Persistencia Políglota — Ingeniería de Datos II (UADE)

Plataforma de gestión de logística internacional y monitoreo de cargas IoT,
con persistencia políglota en 5 motores. La aplicación principal es de
**consola** (`main.py`); hay además una interfaz web local **opcional**
(`main_nicegui.py`) que usa los mismos Services.

## Qué se guarda en cada motor

| Motor | Paradigma | Datos |
|---|---|---|
| MySQL | Relacional | Maestros y transaccional: clientes, usuarios, roles, proveedores, operadores, contenedores, sensores, vehículos, envíos, reglas, facturación y cuentas corrientes (clientes y proveedores/operadores), reportes (metadata), outbox |
| MongoDB | Documental | Eventos logísticos, incidentes, mensajes, grupos de trabajo, predicciones de riesgo |
| Neo4j | Grafos | Tramos y rutas de los envíos; red cliente-operador |
| Redis | Clave-valor | Sesiones y alertas (con TTL) |
| Cassandra | Columnar | Lecturas de sensores IoT (alto volumen de escritura) |

MySQL es la fuente de verdad de las entidades; los demás motores guardan su
ID como referencia y la validan en la capa de aplicación.

## Arquitectura

`CLI / UI web → Services (reglas de negocio) → Repositories (acceso a datos) → app/db (un módulo por motor)`

Sin ORM: SQL parametrizado en los Repositories. Excepciones propias en
`app/core/exceptions.py`; los Repositories traducen los errores del driver y
los Services validan las reglas de negocio.

## Puesta en marcha

Requisitos: Python 3.12+ y Docker + docker-compose.

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt     # Windows; usar venv\Scripts\python en los comandos siguientes
copy .env.example .env                            # los valores por defecto coinciden con docker-compose.yml
docker-compose up -d
python scripts/schema/init_all.py                 # crea el esquema en los 5 motores
python scripts/seed_datos_prueba.py               # carga datos de demostración (opcional)
python main.py                                    # aplicación de consola
```

Neo4j y Cassandra tardan en estar listos: si `init_all.py` informa ERROR en
alguno, esperar y reintentar. Para empezar de cero: `docker-compose down -v` y
repetir. El esquema de MySQL no se puede volver a aplicar sobre tablas
existentes.

> En Windows, la contraseña del alta de Usuario usa `getpass`, que solo
> funciona en una terminal interactiva (no por pipe).

## Funcionalidades

- **ABM** de clientes, usuarios, roles, proveedores, operadores logísticos,
  contenedores, sensores, vehículos, envíos (con asignación de contenedores) y reglas.
- **Facturación:** facturas, pagos y cuentas corrientes de clientes; facturas
  recibidas, pagos emitidos y cuentas corrientes de proveedores y operadores.
  El alta de factura y de pago actualiza el saldo en la misma transacción.
- **Seguimiento:** eventos logísticos (que actualizan el estado del envío),
  incidentes, mensajería privada y grupal, tramos y rutas.
- **Monitoreo IoT:** lecturas de sensores, alertas, mapa GPS por contenedor
  (HTML con folium).
- **Consultas avanzadas (Neo4j):** ruta completa de un envío y red de
  relaciones cliente-operador.
- **Reportes operativos y analíticos** que combinan MySQL, MongoDB y Neo4j
  (envíos por país/estado/cliente, tiempos de entrega, incidentes promedio,
  costos por tipo de transporte, rankings de rutas y clientes).
- **Predicción de atrasos** con scikit-learn (regresión logística sobre los
  envíos ya resueltos), guardada en MongoDB.
- **Procesos periódicos** (se ejecutan a demanda desde la consola):
  cierre mensual de cuentas corrientes y detección de sensores inactivos.

## Pipeline de sensores y rollback entre motores

Registrar una lectura de sensor (Cassandra) evalúa las reglas activas; si
alguna se viola, se crea un **Incidente** (MongoDB) y una **Alerta** (Redis).
Como no existe un commit único entre motores, la atomicidad es manual: si la
Alerta falla, se compensa eliminando el Incidente. De forma análoga, registrar
un evento logístico que cambia el estado del envío revierte el evento si falla
la actualización en MySQL.

Para ver el rollback:

```bash
docker stop redis
python scripts/simulador_iot.py --once --anomaly-prob 1.0
# logs/app.log: "se revierte el incidente (rollback)"
docker start redis
```

## Sincronización MySQL → Neo4j (Outbox)

Las altas, modificaciones y bajas de clientes y envíos se encolan en
`outbox_eventos` dentro de la misma transacción de MySQL. Un worker las
proyecta a Neo4j de forma idempotente (tras 5 fallos pasan a `dead_letter`):

```bash
python worker/outbox_worker.py          # loop cada 5 s
python worker/outbox_worker.py --once   # un solo ciclo
```

## Simulador de sensores IoT

No hay hardware: el script inserta lecturas sintéticas en Cassandra para los
sensores dados de alta, con anomalías ocasionales que disparan el pipeline.

```bash
python scripts/simulador_iot.py                                 # cada 10 s hasta Ctrl+C
python scripts/simulador_iot.py --once                          # un solo tick
python scripts/simulador_iot.py --interval 5 --anomaly-prob 0.2
```

## Datos de demostración

```bash
python scripts/seed_datos_prueba.py                 # limpia y carga el set (prefijo DEMO_)
python scripts/seed_datos_prueba.py --solo-limpiar  # solo borra los datos DEMO_
python scripts/seed_envio_completo.py               # recarga solo el envío de ejemplo
```

El seed incluye un **envío de ejemplo completo**: Córdoba → Dubái, en
tránsito, con 3 tramos (camión, barco, camión), 2 contenedores con 8 sensores
y lecturas GPS a lo largo de la ruta, una alerta de temperatura con su
incidente, eventos logísticos, predicción de riesgo, mensajería y facturación
con pagos. Es el mejor caso para recorrer los 5 motores.

## Interfaz web (opcional)

```bash
python main_nicegui.py     # http://localhost:8090
```

Complemento de la consola, no un reemplazo: ABM por entidad, explorador de
Services, ficha 360° de un envío (los 5 motores en una pantalla), reportes con
gráficos, alertas en vivo, grafo de Neo4j y mapa GPS. No tiene autenticación,
por eso escucha solo en `127.0.0.1`.

## Tests

Requieren `docker-compose up -d` y el esquema de MySQL creado:

```bash
python -m pytest -v                  # suite completa
python -m pytest tests/test_ui_*.py  # solo la UI web (no necesita Docker)
```

Los tests usan datos con prefijo `TEST_` y limpian lo que crean. Los logs van
a `logs/app.log` (nivel en `LOG_LEVEL` del `.env`).
