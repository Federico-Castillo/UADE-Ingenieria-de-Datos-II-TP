-- Esquema MySQL (relacional) — transcripción fiel de
-- "2. modelado.md" / Punto 2 — MySQL — Relacional.

CREATE DATABASE IF NOT EXISTS tp_logistica;
USE tp_logistica;

CREATE TABLE rol (
  id_rol INT AUTO_INCREMENT PRIMARY KEY,
  descripcion VARCHAR(100) NOT NULL,
  nivel_permisos INT NOT NULL DEFAULT 0
);

CREATE TABLE cliente (
  id_cliente INT AUTO_INCREMENT PRIMARY KEY,
  razon_social VARCHAR(150) NOT NULL,
  cuit VARCHAR(13) NOT NULL,
  email VARCHAR(150) NOT NULL,
  telefono VARCHAR(30),
  direccion VARCHAR(200),
  pais VARCHAR(80),
  estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
  UNIQUE KEY uq_cliente_cuit (cuit),
  UNIQUE KEY uq_cliente_email (email)
);

CREATE TABLE proveedor (
  id_proveedor INT AUTO_INCREMENT PRIMARY KEY,
  razon_social VARCHAR(150) NOT NULL,
  cuit VARCHAR(13) NOT NULL,
  email VARCHAR(150) NOT NULL,
  telefono VARCHAR(30),
  direccion VARCHAR(200),
  pais VARCHAR(80),
  estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
  UNIQUE KEY uq_proveedor_cuit (cuit),
  UNIQUE KEY uq_proveedor_email (email)
);

CREATE TABLE operador_logistico (
  id_operador_logistico INT AUTO_INCREMENT PRIMARY KEY,
  razon_social VARCHAR(150) NOT NULL,
  cuit VARCHAR(13) NOT NULL,
  email VARCHAR(150) NOT NULL,
  telefono VARCHAR(30),
  estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
  UNIQUE KEY uq_operador_cuit (cuit),
  UNIQUE KEY uq_operador_email (email)
);

CREATE TABLE usuario (
  id_usuario INT AUTO_INCREMENT PRIMARY KEY,
  id_cliente INT NULL,
  id_rol INT NOT NULL,
  nombre VARCHAR(80) NOT NULL,
  apellido VARCHAR(80) NOT NULL,
  email VARCHAR(150) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
  fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_usuario_email (email),
  CONSTRAINT fk_usuario_cliente FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_usuario_rol FOREIGN KEY (id_rol) REFERENCES rol(id_rol)
    ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE contenedor (
  id_contenedor INT AUTO_INCREMENT PRIMARY KEY,
  codigo_internacional VARCHAR(20) NOT NULL,
  tipo VARCHAR(50) NOT NULL,
  capacidad DECIMAL(10,2) NOT NULL,
  estado VARCHAR(30) NOT NULL,
  UNIQUE KEY uq_contenedor_codigo (codigo_internacional)
);

CREATE TABLE sensor_iot (
  id_sensor INT AUTO_INCREMENT PRIMARY KEY,
  id_contenedor INT NOT NULL,
  tipo VARCHAR(50) NOT NULL,
  fabricante VARCHAR(100),
  fecha_instalacion DATE,
  estado VARCHAR(30) NOT NULL,
  CONSTRAINT fk_sensor_contenedor FOREIGN KEY (id_contenedor) REFERENCES contenedor(id_contenedor)
    ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE regla (
  id_regla INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  tipo_sensor VARCHAR(50) NOT NULL,
  operador_comparacion ENUM('>','>=','<','<=','=') NOT NULL,
  valor_umbral DECIMAL(10,2) NOT NULL,
  severidad VARCHAR(20) NOT NULL,
  estado ENUM('activa','inactiva') NOT NULL DEFAULT 'activa',
  id_usuario_creador INT NOT NULL,
  fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_regla_usuario FOREIGN KEY (id_usuario_creador) REFERENCES usuario(id_usuario)
    ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE envio (
  id_envio INT AUTO_INCREMENT PRIMARY KEY,
  id_cliente INT NOT NULL,
  fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  origen VARCHAR(150) NOT NULL,
  destino VARCHAR(150) NOT NULL,
  estado VARCHAR(30) NOT NULL,
  prioridad VARCHAR(20) NOT NULL DEFAULT 'normal',
  CONSTRAINT fk_envio_cliente FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente)
    ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE vehiculo (
  id_vehiculo INT AUTO_INCREMENT PRIMARY KEY,
  tipo VARCHAR(50) NOT NULL,
  identificacion VARCHAR(50) NOT NULL,
  empresa_operadora VARCHAR(150) NOT NULL,
  estado VARCHAR(30) NOT NULL,
  UNIQUE KEY uq_vehiculo_identificacion (identificacion)
);

CREATE TABLE reporte (
  id_reporte INT AUTO_INCREMENT PRIMARY KEY,
  id_usuario INT NOT NULL,
  tipo VARCHAR(50) NOT NULL,
  fecha_generacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  formato VARCHAR(20) NOT NULL,
  estado VARCHAR(30) NOT NULL,
  CONSTRAINT fk_reporte_usuario FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
    ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE factura (
  id_factura INT AUTO_INCREMENT PRIMARY KEY,
  id_cliente INT NOT NULL,
  fecha_emision DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  importe_total DECIMAL(12,2) NOT NULL CHECK (importe_total >= 0),
  estado VARCHAR(30) NOT NULL,
  CONSTRAINT fk_factura_cliente FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente)
    ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE pago (
  id_pago INT AUTO_INCREMENT PRIMARY KEY,
  id_factura INT NOT NULL,
  fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  monto DECIMAL(12,2) NOT NULL CHECK (monto > 0),
  medio_pago VARCHAR(50) NOT NULL,
  CONSTRAINT fk_pago_factura FOREIGN KEY (id_factura) REFERENCES factura(id_factura)
    ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE cuenta_corriente (
  id_cuenta INT AUTO_INCREMENT PRIMARY KEY,
  id_cliente INT NOT NULL,
  saldo DECIMAL(12,2) NOT NULL DEFAULT 0,
  fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_cuenta_cliente (id_cliente),
  CONSTRAINT fk_cuenta_cliente FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente)
    ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Facturación y pagos hacia proveedores/operadores logísticos (plata que SALE,
-- a diferencia de factura/pago/cuenta_corriente de cliente que es plata que ENTRA).
-- id_proveedor e id_operador_logistico son mutuamente excluyentes: cada fila le
-- pertenece a un proveedor O a un operador, nunca a ambos ni a ninguno.
CREATE TABLE factura_recibida (
  id_factura_recibida INT AUTO_INCREMENT PRIMARY KEY,
  id_proveedor INT NULL,
  id_operador_logistico INT NULL,
  fecha_emision DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  importe_total DECIMAL(12,2) NOT NULL CHECK (importe_total >= 0),
  estado VARCHAR(30) NOT NULL,
  -- ON UPDATE RESTRICT (no CASCADE): MySQL 8 prohibe (error 3823) que una
  -- columna con acción referencial CASCADE participe también en un CHECK.
  -- Sin impacto real: estas FK apuntan a PK AUTO_INCREMENT, que nunca se actualizan.
  CONSTRAINT fk_facturarecibida_proveedor FOREIGN KEY (id_proveedor) REFERENCES proveedor(id_proveedor)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  CONSTRAINT fk_facturarecibida_operador FOREIGN KEY (id_operador_logistico) REFERENCES operador_logistico(id_operador_logistico)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  CONSTRAINT chk_facturarecibida_emisor CHECK (
    (id_proveedor IS NOT NULL AND id_operador_logistico IS NULL) OR
    (id_proveedor IS NULL AND id_operador_logistico IS NOT NULL)
  )
);

CREATE TABLE pago_emitido (
  id_pago_emitido INT AUTO_INCREMENT PRIMARY KEY,
  id_factura_recibida INT NOT NULL,
  fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  monto DECIMAL(12,2) NOT NULL CHECK (monto > 0),
  medio_pago VARCHAR(50) NOT NULL,
  CONSTRAINT fk_pagoemitido_factura FOREIGN KEY (id_factura_recibida) REFERENCES factura_recibida(id_factura_recibida)
    ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE cuenta_corriente_pagable (
  id_cuenta_pagable INT AUTO_INCREMENT PRIMARY KEY,
  id_proveedor INT NULL,
  id_operador_logistico INT NULL,
  saldo DECIMAL(12,2) NOT NULL DEFAULT 0,
  fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_cuentapagable_proveedor (id_proveedor),
  UNIQUE KEY uq_cuentapagable_operador (id_operador_logistico),
  CONSTRAINT fk_cuentapagable_proveedor FOREIGN KEY (id_proveedor) REFERENCES proveedor(id_proveedor)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  CONSTRAINT fk_cuentapagable_operador FOREIGN KEY (id_operador_logistico) REFERENCES operador_logistico(id_operador_logistico)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  CONSTRAINT chk_cuentapagable_titular CHECK (
    (id_proveedor IS NOT NULL AND id_operador_logistico IS NULL) OR
    (id_proveedor IS NULL AND id_operador_logistico IS NOT NULL)
  )
);

-- Índices adicionales documentados en modelado.md (más allá de los UNIQUE KEY
-- y FK ya declarados inline, que MySQL indexa automáticamente).
CREATE INDEX idx_envio_cliente_estado ON envio (id_cliente, estado);
CREATE INDEX idx_envio_fecha ON envio (fecha_creacion);
CREATE INDEX idx_factura_cliente_estado ON factura (id_cliente, estado);
CREATE INDEX idx_facturarecibida_proveedor_estado ON factura_recibida (id_proveedor, estado);
CREATE INDEX idx_facturarecibida_operador_estado ON factura_recibida (id_operador_logistico, estado);
CREATE INDEX idx_sensor_contenedor_estado ON sensor_iot (id_contenedor, estado);
CREATE INDEX idx_regla_tipo_estado ON regla (tipo_sensor, estado);
