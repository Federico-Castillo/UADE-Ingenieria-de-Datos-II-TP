CREATE CONSTRAINT envio_id_unique IF NOT EXISTS FOR (e:Envio) REQUIRE e.id_envio IS UNIQUE;
CREATE CONSTRAINT tramo_id_unique IF NOT EXISTS FOR (t:Tramo) REQUIRE t.id_tramo IS UNIQUE;
CREATE CONSTRAINT vehiculo_id_unique IF NOT EXISTS FOR (v:Vehiculo) REQUIRE v.id_vehiculo IS UNIQUE;
CREATE CONSTRAINT operador_id_unique IF NOT EXISTS FOR (o:Operador) REQUIRE o.id_operador_logistico IS UNIQUE;
CREATE INDEX ubicacion_nombre IF NOT EXISTS FOR (u:Ubicacion) ON (u.nombre);
