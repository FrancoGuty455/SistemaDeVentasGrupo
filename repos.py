from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from config import get_connection 
from security import hash_password, verify_password


def _dict_rows(cur) -> List[Dict[str, Any]]:
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def _dict_one(cur) -> Optional[Dict[str, Any]]:
    row = cur.fetchone()
    if not row:
        return None
    cols = [c[0] for c in cur.description]
    return dict(zip(cols, row))

def query_all(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return _dict_rows(cur)
    finally:
        conn.close()

def query_one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return _dict_one(cur)
    finally:
        conn.close()

def exec_nonquery(sql: str, params: tuple = ()) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        try:
            return cur.rowcount
        except Exception:
            return -1
    finally:
        conn.close()

def _table_exists(cur, schema: str, name: str) -> bool:
    cur.execute("""
        SELECT 1
        FROM sys.tables t
        JOIN sys.schemas s ON s.schema_id = t.schema_id
        WHERE s.name = ? AND t.name = ?;
    """, (schema, name))
    return cur.fetchone() is not None

def _column_exists(cur, schema: str, table: str, col: str) -> bool:
    cur.execute("""
        SELECT 1
        FROM sys.columns c
        JOIN sys.tables t ON t.object_id = c.object_id
        JOIN sys.schemas s ON s.schema_id = t.schema_id
        WHERE s.name = ? AND t.name = ? AND c.name = ?;
    """, (schema, table, col))
    return cur.fetchone() is not None

class ProductoRepo:
    @staticmethod
    def _has_barcode(cur) -> bool:
        """Devuelve True si existe la columna dbo.Productos.CodigoBarras."""
        try:
            return _column_exists(cur, "dbo", "Productos", "CodigoBarras")
        except Exception:
            return False

    @staticmethod
    def listar() -> List[Dict]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            has_cb = ProductoRepo._has_barcode(cur)
            sql = """
                SELECT ProductoID, Nombre, Precio, Stock, Activo {extra}
                FROM dbo.Productos
                ORDER BY Nombre
            """.format(extra=", CodigoBarras" if has_cb else "")
            cur.execute(sql)
            rows = _dict_rows(cur)

            if not has_cb:
                for r in rows:
                    r["CodigoBarras"] = None
            return rows
        finally:
            conn.close()

    @staticmethod
    def crear(nombre: str, precio: float, stock: float, codigo_barras: Optional[str] = None):
        conn = get_connection()
        try:
            cur = conn.cursor()
            has_cb = ProductoRepo._has_barcode(cur)
            if has_cb:
                cur.execute("""
                    INSERT INTO dbo.Productos (Nombre, Precio, Stock, Activo, CodigoBarras)
                    VALUES (?,?,?,?,?)
                """, (nombre, precio, stock, 1, codigo_barras))
            else:
                cur.execute("""
                    INSERT INTO dbo.Productos (Nombre, Precio, Stock, Activo)
                    VALUES (?,?,?,1)
                """, (nombre, precio, stock))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def actualizar_stock(producto_id: int, delta: float):
        """Suma (o resta) stock. Usa delta positivo/negativo (float)."""
        exec_nonquery(
            "UPDATE dbo.Productos SET Stock = Stock + ? WHERE ProductoID = ?",
            (float(delta), producto_id),
        )

    @staticmethod
    def buscar_por_codigo_barras(codigo: str) -> Optional[Dict]:
        """Busca por Código de Barras exacto. Si la columna no existe, devuelve None."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            if not ProductoRepo._has_barcode(cur):
                return None
            cur.execute("""
                SELECT ProductoID, Nombre, Precio, Stock, Activo, CodigoBarras
                  FROM dbo.Productos
                 WHERE CodigoBarras = ?
            """, (codigo,))
            row = _dict_one(cur)
            return row
        finally:
            conn.close()

    @staticmethod
    def buscar_por_codigo(codigo: str) -> Optional[Dict]:
        """
        Compat: intenta por Código de Barras si existe; si no, por ID exacto o Nombre exacto.
        Útil para entrada rápida/lector.
        """

        prod = ProductoRepo.buscar_por_codigo_barras(codigo)
        if prod:
            return prod

        conn = get_connection()
        try:
            cur = conn.cursor()
            has_cb = ProductoRepo._has_barcode(cur)
            sql = """
                SELECT ProductoID, Nombre, Precio, Stock, Activo {extra}
                  FROM dbo.Productos
                 WHERE ProductoID = ? OR Nombre = ?
            """.format(extra=", CodigoBarras" if has_cb else "")
            cur.execute(sql, (codigo, codigo))
            row = _dict_one(cur)
            if row and not has_cb:
                row["CodigoBarras"] = None
            return row
        finally:
            conn.close()

    @staticmethod
    def buscar_nombre_contiene(texto: str) -> List[Dict]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            has_cb = ProductoRepo._has_barcode(cur)
            sql = """
                SELECT TOP 100 ProductoID, Nombre, Precio, Stock, Activo {extra}
                  FROM dbo.Productos
                 WHERE Nombre LIKE ?
                 ORDER BY Nombre
            """.format(extra=", CodigoBarras" if has_cb else "")
            cur.execute(sql, (f"%{texto}%",))
            rows = _dict_rows(cur)
            if not has_cb:
                for r in rows:
                    r["CodigoBarras"] = None
            return rows
        finally:
            conn.close()

    @staticmethod
    def buscar_por_id(pid: int) -> Optional[Dict]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            has_cb = ProductoRepo._has_barcode(cur)
            sql = """
                SELECT ProductoID, Nombre, Precio, Stock, Activo {extra}
                  FROM dbo.Productos
                 WHERE ProductoID = ?
            """.format(extra=", CodigoBarras" if has_cb else "")
            cur.execute(sql, (pid,))
            row = _dict_one(cur)
            if row and not has_cb:
                row["CodigoBarras"] = None
            return row
        finally:
            conn.close()

    @staticmethod
    def actualizar(producto_id: int, nombre: str, precio: float, codigo_barras: Optional[str] = None):
        conn = get_connection()
        try:
            cur = conn.cursor()
            if ProductoRepo._has_barcode(cur):
                cur.execute("""
                    UPDATE dbo.Productos
                       SET Nombre = ?, Precio = ?, CodigoBarras = ?
                     WHERE ProductoID = ?
                """, (nombre, precio, codigo_barras, producto_id))
            else:
                cur.execute("""
                    UPDATE dbo.Productos
                       SET Nombre = ?, Precio = ?
                     WHERE ProductoID = ?
                """, (nombre, precio, producto_id))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def set_estado(producto_id: int, activo: bool):
        exec_nonquery("UPDATE dbo.Productos SET Activo = ? WHERE ProductoID = ?",
                      (1 if activo else 0, producto_id))

    @staticmethod
    def bloquear(producto_id: int):
        ProductoRepo.set_estado(producto_id, False)

    @staticmethod
    def desbloquear(producto_id: int):
        ProductoRepo.set_estado(producto_id, True)

    @staticmethod
    def eliminar(producto_id: int):

        ProductoRepo.bloquear(producto_id)

class ClienteRepo:
    @staticmethod
    def listar() -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ClienteID, Nombre, Email, Telefono, Activo
                    FROM dbo.Clientes
                    ORDER BY Nombre
                """)
                return _dict_rows(cur)
        finally:
            conn.close()

    @staticmethod
    def crear(nombre: str, email: Optional[str] = None, telefono: Optional[str] = None) -> None:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO dbo.Clientes (Nombre, Email, Telefono, Activo)
                    VALUES (?, ?, ?, 1)
                """, (nombre, email, telefono))
                conn.commit()
        finally:
            conn.close()


class VentaRepo:
    @staticmethod
    def crear_venta(
        cliente_id: Optional[int],
        items: List[Dict[str, Any]],
        *,
        descuento_pct: float = 0.0,   
        recargo_pct: float = 0.0,    
        metodo_pago: Optional[str] = None,
        entregado: Optional[float] = None,
        vuelto: Optional[float] = None,
        pagos: Optional[List[Dict[str, Any]]] = None 
    ) -> Tuple[int, float, List[Dict[str, Any]]]:
        """
        Crea una venta con detalle y descuenta stock.
        - Verifica stock.
        - Aplica descuento/recargo (%).
        - Registra pagos y movimientos de stock si existen esas tablas.
        Retorna: (venta_id, total_final, items_guardados)
        """
        conn = get_connection()
        try:
            conn.autocommit = False
            cur = conn.cursor()


            for it in items:
                cur.execute("SELECT Stock, Nombre FROM dbo.Productos WHERE ProductoID=?", (it['producto_id'],))
                row = cur.fetchone()
                if not row:
                    raise ValueError("Producto no existe")
                stock_actual, nombre = row
                cant = float(it['cantidad'])
                if stock_actual is not None and float(stock_actual) < cant:
                    raise ValueError(f"Stock insuficiente para '{nombre}'. Disponible: {stock_actual}")

            subtotal = sum(float(it['cantidad']) * float(it['precio']) for it in items)
            total = subtotal
            if descuento_pct and descuento_pct > 0:
                total = total * (1 - (descuento_pct / 100.0))
            if recargo_pct and recargo_pct > 0:
                total = total * (1 + (recargo_pct / 100.0))
            total = round(total, 2)


            cur.execute("""
                INSERT INTO dbo.Ventas (ClienteID, Fecha, Total)
                OUTPUT INSERTED.VentaID
                VALUES (?, ?, ?)
            """, (cliente_id, datetime.utcnow(), total))
            row = cur.fetchone()
            if not row or row[0] is None:
                raise RuntimeError("No se pudo obtener el VentaID después del INSERT.")
            venta_id = int(row[0])

            for col, val in [
                ("MetodoPago", metodo_pago),
                ("Entregado", entregado),
                ("Vuelto", vuelto),
                ("DescuentoPct", descuento_pct),
                ("RecargoPct", recargo_pct),
            ]:
                if val is None:
                    continue
                if _column_exists(cur, "dbo", "Ventas", col):
                    cur.execute(f"UPDATE dbo.Ventas SET {col}=? WHERE VentaID=?", (val, venta_id))


            stockmov_exists = _table_exists(cur, "dbo", "StockMov")
            for it in items:
                cant = float(it['cantidad'])
                price = float(it['precio'])

                cur.execute("""
                    INSERT INTO dbo.VentaDetalle (VentaID, ProductoID, Cantidad, PrecioUnitario)
                    VALUES (?,?,?,?)
                """, (venta_id, it['producto_id'], cant, price))


                cur.execute("UPDATE dbo.Productos SET Stock = Stock - ? WHERE ProductoID=?",
                            (cant, it['producto_id']))

                if stockmov_exists:
                    cur.execute("""
                        INSERT INTO dbo.StockMov (ProductoID, Cantidad, Tipo, RefID)
                        VALUES (?, ?, 'VENTA', ?)
                    """, (it['producto_id'], -abs(cant), venta_id))

            if pagos:
                pagos_exists = _table_exists(cur, "dbo", "Pagos")
                if pagos_exists:
                    for p in pagos:
                        cur.execute("""
                            INSERT INTO dbo.Pagos (VentaID, Monto, Medio, Referencia)
                            VALUES (?, ?, ?, ?)
                        """, (venta_id, float(p['monto']), p['medio'], p.get('ref')))

            conn.commit()
            return venta_id, total, items
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def obtener_cabecera(venta_id: int) -> Optional[Dict[str, Any]]:
        return query_one("""
            SELECT v.VentaID, v.ClienteID, v.Fecha, v.Total,
                   v.MetodoPago, v.Entregado, v.Vuelto,
                   v.DescuentoPct, v.RecargoPct,
                   c.Nombre AS ClienteNombre
            FROM dbo.Ventas v
            LEFT JOIN dbo.Clientes c ON c.ClienteID = v.ClienteID
            WHERE v.VentaID = ?
        """, (venta_id,))

    @staticmethod
    def obtener_detalle(venta_id: int) -> List[Dict[str, Any]]:
        return query_all("""
            SELECT d.ProductoID, p.Nombre, d.Cantidad, d.PrecioUnitario
            FROM dbo.VentaDetalle d
            JOIN dbo.Productos p ON p.ProductoID = d.ProductoID
            WHERE d.VentaID = ?
            ORDER BY d.DetalleID
        """, (venta_id,))
    
    # 👉 AÑADIR ESTE MÉTODO AQUÍ, dentro de VentaRepo
    @staticmethod
    def listar(limit: int = 200) -> List[Dict[str, Any]]:
        """
        Devuelve las últimas `limit` ventas con datos de cliente y pago.
        """
        sql = f"""
            SELECT TOP {int(limit)}
                   v.VentaID, v.Fecha, v.Total,
                   v.MetodoPago, v.Entregado, v.Vuelto,
                   v.DescuentoPct, v.RecargoPct,
                   c.ClienteID, c.Nombre AS ClienteNombre
              FROM dbo.Ventas v
              LEFT JOIN dbo.Clientes c ON c.ClienteID = v.ClienteID
             ORDER BY v.VentaID DESC
        """
        return query_all(sql)


class UsuarioRepo:
    @staticmethod
    def autenticar(numero: str, password: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT UsuarioID, Numero, Nombre, Rol, Hash, Salt, ForzarCambio, Activo, CreadoEn
                    FROM dbo.Usuarios
                    WHERE Numero = ?
                """, (numero,))
                row = cur.fetchone()
                if not row:
                    return None
                cols = [c[0] for c in cur.description]
                data = dict(zip(cols, row))
                if not data.get('Activo', 1):
                    return None
                if verify_password(password, data['Salt'], data['Hash']):
                    return data
                return None
        finally:
            conn.close()

    @staticmethod
    def crear(numero: str, nombre: str, rol: str, password: str, forzar_cambio: bool = False) -> None:
        conn = get_connection()
        try:
            salt, h = hash_password(password)
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO dbo.Usuarios (Numero, Nombre, Rol, Hash, Salt, ForzarCambio, Activo)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (numero, nombre, rol, h, salt, 1 if forzar_cambio else 0))
                conn.commit()
        finally:
            conn.close()

    @staticmethod
    def cambiar_password(usuario_id: int, password_nuevo: str, forzar_cambio: bool = False) -> None:
        conn = get_connection()
        try:
            salt, h = hash_password(password_nuevo)
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE dbo.Usuarios
                    SET Hash = ?, Salt = ?, ForzarCambio = ?
                    WHERE UsuarioID = ?
                """, (h, salt, 1 if forzar_cambio else 0, usuario_id))
                conn.commit()
        finally:
            conn.close()

    @staticmethod
    def listar() -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT UsuarioID, Numero, Nombre, Rol, Activo, ForzarCambio, CreadoEn
                    FROM dbo.Usuarios
                    ORDER BY Rol, Numero
                """)
                return _dict_rows(cur)
        finally:
            conn.close()

    @staticmethod
    def set_rol(usuario_id: int, rol: str) -> None:
        exec_nonquery("UPDATE dbo.Usuarios SET Rol=? WHERE UsuarioID=?", (rol, usuario_id))

    @staticmethod
    def set_estado(usuario_id: int, activo: bool) -> None:
        exec_nonquery("UPDATE dbo.Usuarios SET Activo=? WHERE UsuarioID=?", (1 if activo else 0, usuario_id))

class FacturaRepo:
    @staticmethod
    def tomar_numero_siguiente() -> int:
        """
        Devuelve y avanza un número de comprobante simple.
        Si la tabla FacturaInfo no existe, devuelve 1 sin fallar.
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            if not _table_exists(cur, "dbo", "FacturaInfo"):
                return 1
            cur.execute("SELECT TOP 1 NumeroActual FROM dbo.FacturaInfo WITH (UPDLOCK, ROWLOCK)")
            row = cur.fetchone()
            if not row:
                cur.execute("INSERT INTO dbo.FacturaInfo (NumeroActual) VALUES (1)")
                conn.commit()
                return 1
            numero = int(row[0])
            cur.execute("UPDATE dbo.FacturaInfo SET NumeroActual = NumeroActual + 1")
            conn.commit()
            return numero
        finally:
            conn.close()

class AuditRepo:
    @staticmethod
    def log(usuario_numero: str, accion: str, entidad: Optional[str] = None,
            refid: Optional[int] = None, datos: Optional[str] = None) -> None:
        conn = get_connection()
        try:
            cur = conn.cursor()
            if not _table_exists(cur, "dbo", "Auditoria"):
                return
            cur.execute("""
                INSERT INTO dbo.Auditoria (Usuario, Accion, Entidad, RefID, Datos)
                VALUES (?, ?, ?, ?, ?)
            """, (usuario_numero, accion, entidad, refid, datos))
            conn.commit()
        finally:
            conn.close()

class IngresoStockRepo:
    @staticmethod
    def ingresar(
        usuario_id: int,
        producto_id: int,
        cantidad: float,
        costo_unit: float,
        precio_venta: float,
    ) -> Dict[str, Any]:
        conn = get_connection()
        try:
            conn.autocommit = False
            cur = conn.cursor()

            cur.execute("SELECT Stock, Precio, Activo FROM dbo.Productos WHERE ProductoID=?", (producto_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("El producto no existe.")
            stock_anterior, precio_anterior, activo = row
            if not activo:
                raise ValueError("El producto está inactivo.")

            stock_nuevo = float(stock_anterior or 0) + float(cantidad)

            cur.execute("""
                UPDATE dbo.Productos
                   SET Stock = ?, Precio = ?
                 WHERE ProductoID = ?
            """, (stock_nuevo, precio_venta, producto_id))

            cur.execute("""
                INSERT INTO dbo.IngresosStock (UsuarioID, ProductoID, Cantidad, CostoUnitario, PrecioVenta)
                OUTPUT INSERTED.IngresoID
                VALUES (?,?,?,?,?)
            """, (usuario_id, producto_id, cantidad, costo_unit, precio_venta))
            row = cur.fetchone()
            if not row or row[0] is None:
                raise RuntimeError("No se pudo obtener el IngresoID después del INSERT.")
            ingreso_id = int(row[0])

            if float(precio_anterior or 0) != float(precio_venta):
                cur.execute("""
                    INSERT INTO dbo.HistorialPrecios (ProductoID, FechaHora, CostoUnit, PrecioVenta)
                    VALUES (?, SYSDATETIME(), ?, ?)
                """, (producto_id, costo_unit, precio_venta))

            if _table_exists(cur, "dbo", "StockMov"):
                cur.execute("""
                    INSERT INTO dbo.StockMov (ProductoID, Cantidad, Tipo, RefID)
                    VALUES (?, ?, 'INGRESO', ?)
                """, (producto_id, abs(float(cantidad)), ingreso_id))

            conn.commit()
            return {
                "producto_id": producto_id,
                "stock_anterior": float(stock_anterior or 0),
                "stock_nuevo": stock_nuevo,
                "precio_anterior": float(precio_anterior or 0),
                "precio_nuevo": float(precio_venta),
                "ingreso_id": ingreso_id,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def listar_ingresos(limit: int = 200) -> List[Dict[str, Any]]:
        sql = f"""
            SELECT TOP {int(limit)}
                   i.IngresoID, i.Fecha, i.UsuarioID, u.Numero AS Usuario,
                   i.ProductoID, p.Nombre AS Producto,
                   i.Cantidad, i.CostoUnitario, i.PrecioVenta
              FROM dbo.IngresosStock i
              JOIN dbo.Productos p ON p.ProductoID = i.ProductoID
              LEFT JOIN dbo.Usuarios  u ON u.UsuarioID  = i.UsuarioID
            ORDER BY i.IngresoID DESC
        """
        return query_all(sql)

    @staticmethod
    def ultimos_precios(producto_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        sql = f"""
            SELECT TOP {int(limit)} HistID, FechaHora, CostoUnit, PrecioVenta
              FROM dbo.HistorialPrecios
             WHERE ProductoID = ?
             ORDER BY HistID DESC
        """
        return query_all(sql, (producto_id,))

class EmpresaRepo:
    @staticmethod
    def obtener() -> Dict[str, Any]:
        sql = """
            SELECT TOP 1 EmpresaID, Nombre, CUIT, CondicionIVA, Direccion, Telefono, Email, LogoPath, ActualizadoEn
            FROM dbo.Empresa ORDER BY EmpresaID
        """
        row = query_one(sql)
        if not row:
            # fallback vacío si la tabla existe pero sin filas (no debería pasar)
            return {"EmpresaID": None, "Nombre": "Empresa", "CUIT": None, "CondicionIVA": None,
                    "Direccion": None, "Telefono": None, "Email": None, "LogoPath": None}
        return row

    @staticmethod
    def guardar(nombre: str, cuit: str | None, condicion: str | None,
                direccion: str | None, telefono: str | None, email: str | None,
                logo_path: str | None) -> None:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT TOP 1 EmpresaID FROM dbo.Empresa ORDER BY EmpresaID")
                row = cur.fetchone()
                if row:
                    eid = int(row[0])
                    cur.execute("""
                        UPDATE dbo.Empresa
                           SET Nombre=?, CUIT=?, CondicionIVA=?, Direccion=?, Telefono=?, Email=?, LogoPath=?, ActualizadoEn=SYSUTCDATETIME()
                         WHERE EmpresaID=?
                    """, (nombre, cuit, condicion, direccion, telefono, email, logo_path, eid))
                else:
                    cur.execute("""
                        INSERT INTO dbo.Empresa(Nombre, CUIT, CondicionIVA, Direccion, Telefono, Email, LogoPath)
                        VALUES (?,?,?,?,?,?,?)
                    """, (nombre, cuit, condicion, direccion, telefono, email, logo_path))
                conn.commit()
        finally:
            conn.close()
