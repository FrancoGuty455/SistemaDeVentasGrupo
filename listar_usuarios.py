from config import get_connection
conn = get_connection()
try:
    with conn.cursor() as cur:
        cur.execute("SELECT UsuarioID, Numero, Nombre, Rol, Activo, ForzarCambio FROM dbo.Usuarios ORDER BY Numero")
        for r in cur.fetchall():
            print(r)
finally:
    conn.close()
