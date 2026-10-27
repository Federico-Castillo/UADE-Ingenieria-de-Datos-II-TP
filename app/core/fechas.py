"""Helpers de fecha compartidos entre Services que comparan datetimes de
motores distintos (Cassandra/Mongo pueden devolver naive o aware según la
config del driver, y las comparaciones tienen que ser agnósticas a eso)."""
from datetime import datetime


def sin_tz(momento: datetime) -> datetime:
    return momento.replace(tzinfo=None) if momento.tzinfo else momento
