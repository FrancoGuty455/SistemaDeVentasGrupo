IF DB_ID('VentasDB') IS NULL
BEGIN
    CREATE DATABASE VentasDB;
END;
GO

USE VentasDB;
GO

-- Empresa
IF OBJECT_ID('dbo.Empresa','U') IS NULL
BEGIN
    CREATE TABLE dbo.Empresa(
        EmpresaID     INT IDENTITY(1,1) PRIMARY KEY,
        Nombre        NVARCHAR(160) NOT NULL,
        CUIT          NVARCHAR(20)  NULL,
        CondicionIVA  NVARCHAR(40)  NULL,
        Direccion     NVARCHAR(200) NULL,
        Telefono      NVARCHAR(60)  NULL,
        Email         NVARCHAR(120) NULL,
        LogoPath      NVARCHAR(260) NULL,
        ActualizadoEn DATETIME2 NOT NULL CONSTRAINT DF_Empresa_Upd DEFAULT SYSUTCDATETIME()
    );
    INSERT INTO dbo.Empresa(Nombre, CUIT, CondicionIVA, Direccion, Telefono, Email)
    VALUES (N'Tu Empresa', N'00-00000000-0', N'Responsable Inscripto',
            N'Dirección', N'Teléfono', N'correo@dominio.com');
END;

-- Productos
IF OBJECT_ID('dbo.Productos','U') IS NULL
BEGIN
    CREATE TABLE dbo.Productos(
        ProductoID   INT IDENTITY(1,1) PRIMARY KEY,
        Nombre       NVARCHAR(120) NOT NULL,
        Precio       DECIMAL(18,2) NOT NULL CONSTRAINT DF_Productos_Precio DEFAULT(0),
        Stock        INT           NOT NULL CONSTRAINT DF_Productos_Stock  DEFAULT(0),
        Activo       BIT           NOT NULL CONSTRAINT DF_Productos_Activo DEFAULT(1),
        CodigoBarras NVARCHAR(32)  NULL
    );
END;

-- Clientes
IF OBJECT_ID('dbo.Clientes','U') IS NULL
BEGIN
    CREATE TABLE dbo.Clientes(
        ClienteID INT IDENTITY(1,1) PRIMARY KEY,
        Nombre    NVARCHAR(120) NOT NULL,
        Email     NVARCHAR(200) NULL,
        Telefono  NVARCHAR(50)  NULL,
        Activo    BIT NOT NULL CONSTRAINT DF_Clientes_Activo DEFAULT(1)
    );
END;

-- Ventas
IF OBJECT_ID('dbo.Ventas','U') IS NULL
BEGIN
    CREATE TABLE dbo.Ventas(
        VentaID      INT IDENTITY(1,1) PRIMARY KEY,
        ClienteID    INT NULL,
        Fecha        DATETIME2 NOT NULL CONSTRAINT DF_Ventas_Fecha DEFAULT SYSUTCDATETIME(),
        Total        DECIMAL(18,2) NOT NULL CONSTRAINT DF_Ventas_Total DEFAULT(0),
        MetodoPago   NVARCHAR(30) NULL,
        Entregado    DECIMAL(18,2) NULL,
        Vuelto       DECIMAL(18,2) NULL,
        DescuentoPct DECIMAL(5,2) NULL CONSTRAINT DF_Ventas_DescPct DEFAULT(0),
        RecargoPct   DECIMAL(5,2) NULL CONSTRAINT DF_Ventas_RecPct DEFAULT(0)
    );
END;

-- VentaDetalle
IF OBJECT_ID('dbo.VentaDetalle','U') IS NULL
BEGIN
    CREATE TABLE dbo.VentaDetalle(
        DetalleID      INT IDENTITY(1,1) PRIMARY KEY,
        VentaID        INT NOT NULL,
        ProductoID     INT NOT NULL,
        Cantidad       DECIMAL(18,2) NOT NULL,
        PrecioUnitario DECIMAL(18,2) NOT NULL,
        CONSTRAINT FK_VD_Venta FOREIGN KEY (VentaID) REFERENCES dbo.Ventas(VentaID),
        CONSTRAINT FK_VD_Producto FOREIGN KEY (ProductoID) REFERENCES dbo.Productos(ProductoID)
    );
END;

-- Usuarios
IF OBJECT_ID('dbo.Usuarios','U') IS NULL
BEGIN
    CREATE TABLE dbo.Usuarios(
        UsuarioID     INT IDENTITY(1,1) PRIMARY KEY,
        Numero        NVARCHAR(50) NOT NULL UNIQUE,
        Nombre        NVARCHAR(100) NOT NULL,
        Rol           NVARCHAR(50) NOT NULL,
        Hash          VARBINARY(256) NOT NULL,
        Salt          VARBINARY(256) NOT NULL,
        ForzarCambio  BIT NOT NULL DEFAULT 0,
        Activo        BIT NOT NULL DEFAULT 1,
        CreadoEn      DATETIME NOT NULL DEFAULT GETDATE()
    );
END;

-- CierresCaja (para el módulo de caja)
IF OBJECT_ID('dbo.CierresCaja','U') IS NULL
BEGIN
    CREATE TABLE dbo.CierresCaja (
        CierreID     INT IDENTITY(1,1) PRIMARY KEY,
        Desde        DATETIME2(0) NOT NULL,
        Hasta        DATETIME2(0) NOT NULL,
        Apertura     DECIMAL(18,2) NOT NULL DEFAULT 0,
        VentasEfvo   DECIMAL(18,2) NOT NULL DEFAULT 0,
        VentasTarj   DECIMAL(18,2) NOT NULL DEFAULT 0,
        VentasTrans  DECIMAL(18,2) NOT NULL DEFAULT 0,
        IngresosExt  DECIMAL(18,2) NOT NULL DEFAULT 0,
        Egresos      DECIMAL(18,2) NOT NULL DEFAULT 0,
        Esperado     DECIMAL(18,2) NOT NULL DEFAULT 0,
        Contado      DECIMAL(18,2) NOT NULL DEFAULT 0,
        Diferencia   DECIMAL(18,2) NOT NULL DEFAULT 0,
        Usuario      NVARCHAR(64) NULL,
        Observacion  NVARCHAR(MAX) NULL,
        CreadoEn     DATETIME2(0) NOT NULL DEFAULT SYSDATETIME()
    );
    CREATE INDEX IX_CierresCaja_Periodo ON dbo.CierresCaja(Desde, Hasta);
END;
--- Insertar usuario admin por defecto
USE VentasDB;
GO

DELETE FROM dbo.Usuarios WHERE Numero = '1'; -- limpiar si ya existía

INSERT INTO dbo.Usuarios (Numero, Nombre, Rol, Hash, Salt, ForzarCambio, Activo)
VALUES (
    '1',                   -- Numero de usuario
    'Administrador',       -- Nombre
    'Admin',               -- Rol
    0x2f972100befdbdb0f5bb2317d512212da19f78b4768bfe24d4b024ff22db8274, -- Hash en hex
    0xb9df1026cd8f43b4dd80b88f77a5fa20,                                 -- Salt en hex
    0, -- ForzarCambio (0 = no)
    1  -- Activo
);
