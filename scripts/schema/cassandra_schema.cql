CREATE KEYSPACE IF NOT EXISTS tp_logistica
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE tp_logistica;

CREATE TABLE IF NOT EXISTS lecturas_sensor (
  id_sensor INT,
  fecha_hora TIMESTAMP,
  id_lectura UUID,
  temperatura DOUBLE,
  humedad DOUBLE,
  vibracion DOUBLE,
  gps_lat DOUBLE,
  gps_lon DOUBLE,
  nivel_bateria DOUBLE,
  PRIMARY KEY ((id_sensor), fecha_hora, id_lectura)
) WITH CLUSTERING ORDER BY (fecha_hora DESC);
