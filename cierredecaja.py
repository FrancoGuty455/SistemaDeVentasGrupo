
from datetime import datetime, time
from decimal import Decimal
import tkinter as tk
from tkinter import ttk, messagebox
try:
    import ttkbootstrap as tb
except Exception:
    tb = None


from config import get_connection
from repos import _table_exists, _column_exists   # reusamos tus utilidades
try:
    from repos import VentaRepo
except Exception:
    VentaRepo = None

def parse_float(val: str) -> float:
    try:
        return float(str(val).replace(",", "."))
    except Exception:
        return 0.0

def _today_00_00():
    now = datetime.now()
    return datetime.combine(now.date(), time(0, 0, 0))

def _now():
    return datetime.now()


class CajaRepo:
    """
    Maneja la tabla dbo.CierresCaja en SQL Server.
    Crea la tabla si no existe.
    Ofrece:
      - guardar_cierre(data)
      - listar_cierres(limit)
      - resumen_para_cierre(f0, f1)  -> {'Efectivo': x, 'Tarjeta': y, 'Transferencia': z}
    """
    def __init__(self):
        self._ensure_schema()

    def _ensure_schema(self):
        conn = get_connection()
        try:
            cur = conn.cursor()
            if not _table_exists(cur, "dbo", "CierresCaja"):
                cur.execute("""
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
                """)
                conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _dt(val):
        if isinstance(val, datetime):
            return val
        s = str(val).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try: return datetime.strptime(s, fmt)
            except Exception: pass
        return datetime.fromisoformat(s)

    def guardar_cierre(self, c: dict) -> int:
        """
        c = {
          'desde','hasta','apertura','efectivo','tarjeta','transfer',
          'ingresos','egresos','esperado','contado','diferencia','usuario','obs'
        }
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO dbo.CierresCaja
                (Desde, Hasta, Apertura, VentasEfvo, VentasTarj, VentasTrans,
                 IngresosExt, Egresos, Esperado, Contado, Diferencia,
                 Usuario, Observacion)
                OUTPUT INSERTED.CierreID
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                self._dt(c["desde"]), self._dt(c["hasta"]),
                c["apertura"], c["efectivo"], c["tarjeta"], c["transfer"],
                c["ingresos"], c["egresos"], c["esperado"], c["contado"], c["diferencia"],
                c.get("usuario"), c.get("obs")
            ))
            row = cur.fetchone()
            conn.commit()
            return int(row[0])
        finally:
            conn.close()

    def listar_cierres(self, limit=100):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"""
                SELECT TOP ({int(limit)})
                       CierreID, Desde, Hasta, Apertura, VentasEfvo, VentasTarj, VentasTrans,
                       IngresosExt, Egresos, Esperado, Contado, Diferencia, Usuario, CreadoEn
                  FROM dbo.CierresCaja
                 ORDER BY CierreID DESC
            """)
            cols = [c[0] for c in cur.description]
            rows = []
            for r in cur.fetchall():
                d = dict(zip(cols, r))
                # normalizo decimales → float para mostrar
                for k in ("Apertura","VentasEfvo","VentasTarj","VentasTrans",
                          "IngresosExt","Egresos","Esperado","Contado","Diferencia"):
                    if isinstance(d[k], Decimal):
                        d[k] = float(d[k])
                for k in ("Desde","Hasta","CreadoEn"):
                    if isinstance(d[k], datetime):
                        d[k] = d[k].strftime("%Y-%m-%d %H:%M:%S")
                rows.append(d)
            return rows
        finally:
            conn.close()

    def resumen_para_cierre(self, f0: datetime, f1: datetime):
        """
        Devuelve totales por método en el período:
        {'Efectivo': x, 'Tarjeta': y, 'Transferencia': z}
        - Si existe dbo.Pagos: agrupa por Pagos.Medio (suma Monto)
        - Si no: si Ventas.MetodoPago existe: agrupa por Ventas.MetodoPago (suma Total)
        """
        res = {"Efectivo": 0.0, "Tarjeta": 0.0, "Transferencia": 0.0}
        conn = get_connection()
        try:
            cur = conn.cursor()

            tiene_pagos = _table_exists(cur, "dbo", "Pagos")
            if tiene_pagos:
                cur.execute("""
                    SELECT p.Medio, SUM(p.Monto) AS Monto
                      FROM dbo.Pagos p
                      JOIN dbo.Ventas v ON v.VentaID = p.VentaID
                     WHERE v.Fecha >= ? AND v.Fecha <= ?
                     GROUP BY p.Medio
                """, (f0, f1))
                rows = cur.fetchall()
                for medio, monto in rows:
                    medio_s = (medio or "").lower()
                    if "efec" in medio_s:
                        res["Efectivo"] += float(monto or 0)
                    elif "tarj" in medio_s or "crédi" in medio_s or "credi" in medio_s or "debito" in medio_s or "débito" in medio_s:
                        res["Tarjeta"] += float(monto or 0)
                    elif "trans" in medio_s:
                        res["Transferencia"] += float(monto or 0)
                return res


            if _column_exists(cur, "dbo", "Ventas", "MetodoPago"):
                cur.execute("""
                    SELECT v.MetodoPago, SUM(v.Total) AS Monto
                      FROM dbo.Ventas v
                     WHERE v.Fecha >= ? AND v.Fecha <= ?
                     GROUP BY v.MetodoPago
                """, (f0, f1))
                rows = cur.fetchall()
                for medio, monto in rows:
                    medio_s = (medio or "").lower()
                    if "efec" in medio_s:
                        res["Efectivo"] += float(monto or 0)
                    elif "tarj" in medio_s or "crédi" in medio_s or "credi" in medio_s or "debito" in medio_s or "débito" in medio_s:
                        res["Tarjeta"] += float(monto or 0)
                    elif "trans" in medio_s:
                        res["Transferencia"] += float(monto or 0)
                return res

            # Fallback si no hay nada para agrupar
            return res
        finally:
            conn.close()



class CierreDeCajaFrame(ttk.Frame):
    """
    - Selección de período
    - Totales por método (auto/manual)
    - Apertura / Ingresos extra / Egresos / Contado
    - Guarda en dbo.CierresCaja
    - Historial de cierres
    """
    def __init__(self, parent, current_user=None):
        super().__init__(parent)
        self.current_user = current_user or {}
        self.repo = CajaRepo()


        top = ttk.LabelFrame(self, text="Período del cierre")
        top.pack(fill="x", padx=8, pady=(8, 4))

        ttk.Label(top, text="Desde (YYYY-MM-DD HH:MM):").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.ent_desde = ttk.Entry(top, width=20); self.ent_desde.grid(row=0, column=1, sticky="w", padx=(0,12), pady=6)

        ttk.Label(top, text="Hasta (YYYY-MM-DD HH:MM):").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        self.ent_hasta = ttk.Entry(top, width=20); self.ent_hasta.grid(row=0, column=3, sticky="w", padx=(0,12), pady=6)

        btns_top = ttk.Frame(top); btns_top.grid(row=0, column=4, sticky="e", padx=8, pady=6)
        self._preset_hoy()


        mid = ttk.LabelFrame(self, text="Totales de ventas por método")
        mid.pack(fill="x", padx=8, pady=4)

        ttk.Label(mid, text="Efectivo:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.ent_efectivo = ttk.Entry(mid, width=12); self.ent_efectivo.grid(row=0, column=1, sticky="w")
        ttk.Label(mid, text="Tarjeta:").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        self.ent_tarjeta = ttk.Entry(mid, width=12); self.ent_tarjeta.grid(row=0, column=3, sticky="w")
        ttk.Label(mid, text="Transferencia:").grid(row=0, column=4, sticky="w", padx=8, pady=6)
        self.ent_transfer = ttk.Entry(mid, width=12); self.ent_transfer.grid(row=0, column=5, sticky="w")


        mov = ttk.LabelFrame(self, text="Otros movimientos")
        mov.pack(fill="x", padx=8, pady=4)

        ttk.Label(mov, text="Apertura:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.ent_apertura = ttk.Entry(mov, width=12); self.ent_apertura.grid(row=0, column=1, sticky="w")

        ttk.Label(mov, text="Ingresos extra:").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        self.ent_ingresos = ttk.Entry(mov, width=12); self.ent_ingresos.grid(row=0, column=3, sticky="w")

        ttk.Label(mov, text="Egresos / Retiros:").grid(row=0, column=4, sticky="w", padx=8, pady=6)
        self.ent_egresos = ttk.Entry(mov, width=12); self.ent_egresos.grid(row=0, column=5, sticky="w")


        res = ttk.LabelFrame(self, text="Resultado")
        res.pack(fill="x", padx=8, pady=4)

        ttk.Label(res, text="Efectivo esperado:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.lbl_esperado = ttk.Label(res, text="$0.00", font=("Segoe UI", 11, "bold"))
        self.lbl_esperado.grid(row=0, column=1, sticky="w")

        ttk.Label(res, text="Efectivo contado:").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        self.ent_contado = ttk.Entry(res, width=12); self.ent_contado.grid(row=0, column=3, sticky="w")

        ttk.Label(res, text="Diferencia:").grid(row=0, column=4, sticky="w", padx=8, pady=6)
        self.lbl_dif = ttk.Label(res, text="$0.00", font=("Segoe UI", 11, "bold"))
        self.lbl_dif.grid(row=0, column=5, sticky="w")


        obs = ttk.LabelFrame(self, text="Observaciones")
        obs.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.txt_obs = tk.Text(obs, height=4)
        self.txt_obs.pack(fill="both", expand=True, padx=8, pady=8)


        bottom = ttk.Frame(self); bottom.pack(fill="x", padx=8, pady=(0,8))
        ttk.Button(bottom, text="Guardar cierre", style="success.TButton" if tb else None,
                   command=self._guardar).pack(side="left")
        ttk.Button(bottom, text="Ver historial", command=self._ver_historial).pack(side="left", padx=6)
        ttk.Button(bottom, text="Limpiar", command=self._limpiar).pack(side="left")


        for ent in (self.ent_efectivo, self.ent_tarjeta, self.ent_transfer,
                    self.ent_apertura, self.ent_ingresos, self.ent_egresos,
                    self.ent_contado):
            ent.bind("<KeyRelease>", lambda e: self._recalc())

        self._recalc()


    def _preset_hoy(self):
        d0 = _today_00_00()
        d1 = _now()
        self.ent_desde.delete(0, tk.END); self.ent_desde.insert(0, d0.strftime("%Y-%m-%d %H:%M"))
        self.ent_hasta.delete(0, tk.END); self.ent_hasta.insert(0, d1.strftime("%Y-%m-%d %H:%M"))

    def _parse_periodo(self):
        def _p(s):
            s = (s or "").strip()
            return datetime.strptime(s, "%Y-%m-%d %H:%M")
        f0 = _p(self.ent_desde.get())
        f1 = _p(self.ent_hasta.get())
        if f1 < f0:
            messagebox.showerror("Período", "'Hasta' debe ser >= 'Desde'.")
            raise ValueError("rango")
        return f0, f1

    def _recalc(self):
        ef = parse_float(self.ent_efectivo.get())
        ap = parse_float(self.ent_apertura.get())
        inx = parse_float(self.ent_ingresos.get())
        eg = parse_float(self.ent_egresos.get())
        esperado = round(ap + ef + inx - eg, 2)   # efectivo esperado en caja
        self.lbl_esperado.config(text=f"${esperado:,.2f}")
        contado = parse_float(self.ent_contado.get())
        dif = round(contado - esperado, 2)
        self.lbl_dif.config(text=f"${dif:,.2f}")

    def _limpiar(self):
        for ent in (self.ent_efectivo, self.ent_tarjeta, self.ent_transfer,
                    self.ent_apertura, self.ent_ingresos, self.ent_egresos,
                    self.ent_contado):
            ent.delete(0, tk.END); ent.insert(0, "0")
        self.txt_obs.delete("1.0", tk.END)
        self._recalc()


    def _auto_calc(self):
        try:
            f0, f1 = self._parse_periodo()
        except Exception:
            return

        # 1) Si tu VentaRepo ya tiene algo, usalo:
        for name in ("resumen_para_cierre", "resumen_por_periodo", "totales_por_periodo"):
            if VentaRepo and hasattr(VentaRepo, name):
                try:
                    res = getattr(VentaRepo, name)(f0, f1)
                    ef = float(res.get("Efectivo", 0))
                    tj = float(res.get("Tarjeta", 0))
                    tr = float(res.get("Transferencia", 0))
                    self._set_totales(ef, tj, tr)
                    return
                except Exception:
                    pass


        try:
            res = self.repo.resumen_para_cierre(f0, f1)
            self._set_totales(res["Efectivo"], res["Tarjeta"], res["Transferencia"])
        except Exception as e:
            messagebox.showwarning("Cierre de caja", f"No se pudo calcular automáticamente.\n{e}")

    def _set_totales(self, ef, tj, tr):
        self.ent_efectivo.delete(0, tk.END); self.ent_efectivo.insert(0, f"{ef:.2f}")
        self.ent_tarjeta.delete(0, tk.END);  self.ent_tarjeta.insert(0, f"{tj:.2f}")
        self.ent_transfer.delete(0, tk.END); self.ent_transfer.insert(0, f"{tr:.2f}")
        self._recalc()

    def _guardar(self):
        try:
            f0, f1 = self._parse_periodo()
        except Exception:
            return

        data = {
            "desde": f0,
            "hasta": f1,
            "apertura": parse_float(self.ent_apertura.get()),
            "efectivo": parse_float(self.ent_efectivo.get()),
            "tarjeta": parse_float(self.ent_tarjeta.get()),
            "transfer": parse_float(self.ent_transfer.get()),
            "ingresos": parse_float(self.ent_ingresos.get()),
            "egresos": parse_float(self.ent_egresos.get()),
            "contado": parse_float(self.ent_contado.get()),
            "usuario": (self.current_user or {}).get("Numero") if self.current_user else None,
            "obs": self.txt_obs.get("1.0", tk.END).strip()
        }
        esperado = round(data["apertura"] + data["efectivo"] + data["ingresos"] - data["egresos"], 2)
        dif = round(data["contado"] - esperado, 2)
        data["esperado"] = esperado
        data["diferencia"] = dif

        try:
            cierre_id = self.repo.guardar_cierre(data)
            messagebox.showinfo(
                "Cierre de caja",
                f"Cierre #{cierre_id} guardado.\n"
                f"Esperado: ${esperado:,.2f}\n"
                f"Contado:  ${data['contado']:,.2f}\n"
                f"Diferencia: ${dif:,.2f}"
            )
            self._limpiar()
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))

    def _ver_historial(self):
        rows = self.repo.listar_cierres(limit=200)
        if not rows:
            messagebox.showinfo("Historial", "No hay cierres aún.")
            return

        win = tk.Toplevel(self)
        win.title("Historial de cierres de caja")
        win.geometry("980x380")
        win.transient(self)
        try: win.grab_set()
        except Exception: pass

        cols = ("id","desde","hasta","apertura","efectivo","tarjeta","transfer",
                "ingresos","egresos","esperado","contado","diferencia","usuario","creado")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
        headers = [
            ("id","ID"),("desde","Desde"),("hasta","Hasta"),("apertura","Apertura"),
            ("efectivo","Efvo."),("tarjeta","Tarj."),("transfer","Transf."),
            ("ingresos","Ing.Ext."),("egresos","Egresos"),("esperado","Esperado"),
            ("contado","Contado"),("diferencia","Dif."),("usuario","Usuario"),("creado","Creado en")
        ]
        for c,title in headers:
            tree.heading(c, text=title)
            tree.column(c, width=90 if c not in ("desde","hasta","creado") else 140, anchor="center")
        tree.pack(fill="both", expand=True, padx=8, pady=8)

        for r in rows:
            tree.insert("", tk.END, values=(
                r["CierreID"], r["Desde"], r["Hasta"], f"{float(r['Apertura']):.2f}",
                f"{float(r['VentasEfvo']):.2f}", f"{float(r['VentasTarj']):.2f}", f"{float(r['VentasTrans']):.2f}",
                f"{float(r['IngresosExt']):.2f}", f"{float(r['Egresos']):.2f}",
                f"{float(r['Esperado']):.2f}", f"{float(r['Contado']):.2f}", f"{float(r['Diferencia']):.2f}",
                r.get("Usuario") or "", r["CreadoEn"]
            ))

        ttk.Button(win, text="Cerrar", command=win.destroy).pack(pady=(0,8))
