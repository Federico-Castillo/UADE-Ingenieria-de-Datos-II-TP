# Convenciones de claves en Redis

Redis no tiene esquema que crear (no hay colecciones/tablas que declarar de
antemano). Las convenciones de key naming, tal como están definidas en
"2. modelado.md" / Punto 2 — Redis — Clave-Valor, son:

```
session:{id_sesion}        -> HASH { id_usuario, fecha_inicio, fecha_fin, estado }        (TTL)
user_sessions:{id_usuario}  -> SET de id_sesion activos                                    (sin TTL, se limpia por app)
alert:{id_alerta}          -> HASH { id_sensor, id_evento, id_regla, tipo, fecha, estado }  (TTL)
alerts:active               -> SET de id_alerta actualmente activos
```

`init_all.py` no ejecuta nada contra Redis — solo verifica que la conexión
funcione — porque no hay esquema que crear.
