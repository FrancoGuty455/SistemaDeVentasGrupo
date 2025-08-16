import pyodbc

SERVER = r'localhost\SQLEXPRESS'  
DATABASE = 'VentasDB'
TRUSTED = True                      
USER = 'sa'                         
PASSWORD = 'yourStrong(!)Password'  

_DRIVERS = [
    '{ODBC Driver 18 for SQL Server}',
    '{ODBC Driver 17 for SQL Server}',
    '{SQL Server Native Client 11.0}',
    '{SQL Server}'
]

def _connect(database: str) -> pyodbc.Connection:
    last_error = None
    for drv in _DRIVERS:
        try:
            if TRUSTED:
                conn_str = (
                    f'DRIVER={drv};SERVER={SERVER};DATABASE={database};'
                    'Trusted_Connection=yes;Encrypt=no;'
                )
            else:
                conn_str = (
                    f'DRIVER={drv};SERVER={SERVER};DATABASE={database};'
                    f'UID={USER};PWD={PASSWORD};Encrypt=no;'
                )
            return pyodbc.connect(conn_str, timeout=5)
        except Exception as e:
            last_error = e
            continue
    raise RuntimeError(f"No se pudo conectar a SQL Server. Último error: {last_error}")

def get_connection() -> pyodbc.Connection:
    """Conexión directa a la DB de negocio (VentasDB)."""
    return _connect(DATABASE)


def _ensure_database():
    conn = _connect('master')
    try:
        conn.autocommit = True        
        with conn.cursor() as cur:
            cur.execute("""
IF DB_ID(?) IS NULL
BEGIN
    DECLARE @name sysname = ?;
    DECLARE @sql  nvarchar(400) = N'CREATE DATABASE [' + REPLACE(@name, N']', N']]') + N']';
    EXEC(@sql);
END
""", (DATABASE, DATABASE))
    finally:
        conn.close()


def _ensure_core_tables(conn: pyodbc.Connection):
    """Tablas base: Productos, Clientes, Ventas, VentaDetalle, Usuarios y FKs."""
    with conn.cursor() as cur:

        cur.execute("""
IF OBJECT_ID('dbo.Empresa','U') IS NULL
BEGIN
    CREATE TABLE dbo.Empresa(
        EmpresaID     INT IDENTITY(1,1) PRIMARY KEY,
        Nombre        NVARCHAR(160) NOT NULL,
        CUIT          NVARCHAR(20)  NULL,
        CondicionIVA  NVARCHAR(40)  NULL,   -- Responsable Inscripto / Monotributo / etc.
        Direccion     NVARCHAR(200) NULL,
        Telefono      NVARCHAR(60)  NULL,
        Email         NVARCHAR(120) NULL,
        LogoPath      NVARCHAR(260) NULL,   -- ruta local a un .png/.jpg si querés
        ActualizadoEn DATETIME2 NOT NULL CONSTRAINT DF_Empresa_Upd DEFAULT SYSUTCDATETIME()
    );
END;
IF NOT EXISTS (SELECT 1 FROM dbo.Empresa)
BEGIN
    INSERT INTO dbo.Empresa(Nombre, CUIT, CondicionIVA, Direccion, Telefono, Email, LogoPath)
    VALUES (N'Tu Empresa', N'00-00000000-0', N'Responsable Inscripto', N'Dirección', N'Teléfono', N'correo@dominio.com', NULL);
END;
""")
        cur.execute("""
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
END
    """)
    cur.execute("""
    IF OBJECT_ID('dbo.Productos','U') IS NOT NULL
    AND COL_LENGTH('dbo.Productos','CodigoBarras') IS NULL
    BEGIN
        ALTER TABLE dbo.Productos ADD CodigoBarras NVARCHAR(32) NULL;
    END
    """)

    cur.execute("""
    IF OBJECT_ID('dbo.Productos','U') IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM sys.indexes 
                    WHERE name='UX_Productos_CodigoBarras' 
                    AND object_id = OBJECT_ID('dbo.Productos'))
    BEGIN
        BEGIN TRY
            CREATE UNIQUE INDEX UX_Productos_CodigoBarras
                ON dbo.Productos(CodigoBarras)
                WHERE CodigoBarras IS NOT NULL;
        END TRY
        BEGIN CATCH
            IF NOT EXISTS (SELECT 1 FROM sys.indexes 
                        WHERE name='IX_Productos_CodigoBarras' 
                            AND object_id = OBJECT_ID('dbo.Productos'))
                CREATE INDEX IX_Productos_CodigoBarras ON dbo.Productos(CodigoBarras);
            -- No relanzamos el error para no romper el bootstrap
        END CATCH
    END
    """)

    cur.execute("""
    SELECT TOP 5 CodigoBarras, COUNT(*) AS Cant
    FROM dbo.Productos
    WHERE CodigoBarras IS NOT NULL
    GROUP BY CodigoBarras
    HAVING COUNT(*) > 1
    ORDER BY Cant DESC, CodigoBarras
    """)
    dups = cur.fetchall()
    if dups:
        print("[SCHEMA] Aviso: hay códigos de barras duplicados; no se pudo crear índice único.")
        for cb, cnt in dups:
            print(f"         {cb}: {cnt} ocurrencias")



        cur.execute("""
IF OBJECT_ID('dbo.Clientes','U') IS NULL
BEGIN
    CREATE TABLE dbo.Clientes(
        ClienteID INT IDENTITY(1,1) PRIMARY KEY,
        Nombre    NVARCHAR(120) NOT NULL,
        Email     NVARCHAR(200) NULL,
        Telefono  NVARCHAR(50)  NULL,
        Activo    BIT NOT NULL CONSTRAINT DF_Clientes_Activo DEFAULT(1)
    );
END
""")

        cur.execute("""
IF OBJECT_ID('dbo.Ventas','U') IS NULL
BEGIN
    CREATE TABLE dbo.Ventas(
        VentaID   INT IDENTITY(1,1) PRIMARY KEY,
        ClienteID INT NULL,
        Fecha     DATETIME2 NOT NULL CONSTRAINT DF_Ventas_Fecha DEFAULT SYSUTCDATETIME(),
        Total     DECIMAL(18,2) NOT NULL CONSTRAINT DF_Ventas_Total DEFAULT(0)
        -- columnas opcionales se agregan abajo
    );
END
""")
        cur.execute("IF COL_LENGTH('dbo.Ventas','MetodoPago') IS NULL ALTER TABLE dbo.Ventas ADD MetodoPago NVARCHAR(30) NULL;")
        cur.execute("IF COL_LENGTH('dbo.Ventas','Entregado')  IS NULL ALTER TABLE dbo.Ventas ADD Entregado  DECIMAL(18,2) NULL;")
        cur.execute("IF COL_LENGTH('dbo.Ventas','Vuelto')     IS NULL ALTER TABLE dbo.Ventas ADD Vuelto     DECIMAL(18,2) NULL;")
        cur.execute("IF COL_LENGTH('dbo.Ventas','DescuentoPct') IS NULL ALTER TABLE dbo.Ventas ADD DescuentoPct DECIMAL(5,2) NULL CONSTRAINT DF_Ventas_DescPct DEFAULT(0);")
        cur.execute("IF COL_LENGTH('dbo.Ventas','RecargoPct')   IS NULL ALTER TABLE dbo.Ventas ADD RecargoPct   DECIMAL(5,2) NULL CONSTRAINT DF_Ventas_RecPct DEFAULT(0);")

        cur.execute("""
IF OBJECT_ID('dbo.VentaDetalle','U') IS NULL
BEGIN
    CREATE TABLE dbo.VentaDetalle(
        DetalleID      INT IDENTITY(1,1) PRIMARY KEY,
        VentaID        INT NOT NULL,
        ProductoID     INT NOT NULL,
        Cantidad       DECIMAL(18,3) NOT NULL, -- fraccionados
        PrecioUnitario DECIMAL(18,2) NOT NULL CHECK (PrecioUnitario >= 0)
    );
END
""")
        cur.execute("""
IF COL_LENGTH('dbo.VentaDetalle','Cantidad') IS NOT NULL
BEGIN TRY
    ALTER TABLE dbo.VentaDetalle ALTER COLUMN Cantidad DECIMAL(18,3) NOT NULL;
END TRY
BEGIN CATCH
    -- Si no se puede, lo dejamos como está (no fallamos el bootstrap)
END CATCH
""")


        cur.execute("""
IF OBJECT_ID('dbo.Usuarios','U') IS NULL
BEGIN
    CREATE TABLE dbo.Usuarios(
        UsuarioID    INT IDENTITY(1,1) PRIMARY KEY,
        Numero       NVARCHAR(50) NOT NULL UNIQUE,              -- legajo/login
        Nombre       NVARCHAR(120) NULL,
        Rol          NVARCHAR(20) NOT NULL CONSTRAINT DF_Usr_Rol DEFAULT('Vendedor'), -- 'Admin' | 'Vendedor'
        Hash         VARBINARY(64) NOT NULL,
        Salt         VARBINARY(32) NOT NULL,
        ForzarCambio BIT NOT NULL CONSTRAINT DF_Usr_Forzar DEFAULT(0),
        Activo       BIT NOT NULL CONSTRAINT DF_Usr_Activo DEFAULT(1),
        CreadoEn     DATETIME2 NOT NULL CONSTRAINT DF_Usr_Creado DEFAULT SYSUTCDATETIME()
    );
END
""")

        cur.execute("""
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Ventas_Clientes')
BEGIN
    ALTER TABLE dbo.Ventas
        ADD CONSTRAINT FK_Ventas_Clientes
        FOREIGN KEY (ClienteID) REFERENCES dbo.Clientes(ClienteID);
END
""")
        cur.execute("""
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_VD_Ventas')
BEGIN
    ALTER TABLE dbo.VentaDetalle
        ADD CONSTRAINT FK_VD_Ventas
        FOREIGN KEY (VentaID) REFERENCES dbo.Ventas(VentaID);
END
""")
        cur.execute("""
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_VD_Productos')
BEGIN
    ALTER TABLE dbo.VentaDetalle
        ADD CONSTRAINT FK_VD_Productos
        FOREIGN KEY (ProductoID) REFERENCES dbo.Productos(ProductoID);
END
""")

        cur.execute("""
IF OBJECT_ID('dbo.Ventas','U') IS NOT NULL
AND COL_LENGTH('dbo.Ventas','Fecha') IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Ventas_Fecha' AND object_id=OBJECT_ID('dbo.Ventas'))
BEGIN
    CREATE INDEX IX_Ventas_Fecha ON dbo.Ventas(Fecha DESC);
END
""")

        cur.execute("""
IF OBJECT_ID('dbo.Ventas','U') IS NOT NULL
AND COL_LENGTH('dbo.Ventas','Fecha') IS NOT NULL
AND COL_LENGTH('dbo.Ventas','MetodoPago') IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Ventas_Fecha_Metodo' AND object_id=OBJECT_ID('dbo.Ventas'))
BEGIN
    CREATE INDEX IX_Ventas_Fecha_Metodo ON dbo.Ventas(Fecha, MetodoPago);
END
""")
        conn.commit()

def _ensure_optional_tables(conn: pyodbc.Connection):
    """Tablas opcionales que tu app usa si existen: Pagos, IngresosStock, HistorialPrecios, StockMov, CierresCaja, FacturaInfo, Auditoria."""
    with conn.cursor() as cur:
    


        conn.commit()

def _ensure_default_admin(conn: pyodbc.Connection):
    """Crea un Admin por defecto si no existe ninguno."""
    from security import hash_password
    with conn.cursor() as cur:
        
        cur.execute("SELECT COUNT(*) FROM sys.objects WHERE object_id = OBJECT_ID('dbo.Usuarios') AND type='U'")
        if cur.fetchone()[0] == 0:
            return
      
        cur.execute("SELECT COUNT(*) FROM dbo.Usuarios WHERE Rol='Admin'")
        if cur.fetchone()[0] > 0:
            return

        salt, h = hash_password('1')
        cur.execute("""
            INSERT INTO dbo.Usuarios(Numero, Nombre, Rol, Hash, Salt, ForzarCambio, Activo)
            VALUES (?,?,?,?,?,1,1)
        """, ('1', 'Administrador', 'Admin', h, salt))
        conn.commit()



def ensure_schema():

    _ensure_database()

    conn = get_connection()
    try:
        conn.autocommit = True        
        _ensure_core_tables(conn)
        _ensure_optional_tables(conn)
        _ensure_default_admin(conn)
    finally:
        conn.close()