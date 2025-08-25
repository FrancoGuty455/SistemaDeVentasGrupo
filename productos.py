import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from repos import ProductoRepo, IngresoStockRepo
def fmt_money(x) -> str:
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return str(x)

class ProductosFrame(ttk.Frame):
    def __init__(self, parent, current_user: dict):
        super().__init__(parent)
        self.current_user = current_user
        self._all_rows = []
        self._sort_state = {}  

        top = ttk.Frame(self); top.pack(fill="x", padx=10, pady=(10,2))
        ttk.Label(top, text="Productos", font=("Segoe UI", 12, "bold")).pack(side="left")
        spacer = ttk.Frame(top); spacer.pack(side="left", padx=8)
        ttk.Label(top, text="Buscar:").pack(side="left")
        self.e_search = ttk.Entry(top, width=32)
        self.e_search.pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Aplicar", command=self._apply_filter).pack(side="left", padx=6)
        ttk.Button(top, text="Limpiar", command=self._clear_filter).pack(side="left")


        bar = ttk.Frame(self); bar.pack(fill="x", padx=10, pady=(4,8))
        ttk.Button(bar, text="Añadir producto", command=self._add_producto).pack(side="left")
        ttk.Button(bar, text="Editar", command=self._edit_producto).pack(side="left", padx=6)
        ttk.Button(bar, text="Ingresar stock", command=self._open_ingreso_dialog).pack(side="left", padx=6)
        ttk.Button(bar, text="Bloquear / Desbloquear", command=self._toggle_bloqueo).pack(side="left", padx=6)
        ttk.Button(bar, text="Actualizar (F5)", command=self.load).pack(side="left", padx=(12,0))


        grid = ttk.Frame(self); grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,6))
        cols = ("id","nombre","codigo","precio","stock","estado")
        self.tree = ttk.Treeview(grid, columns=cols, show="headings", height=16)
        self.tree.heading("codigo", text="Código", command=lambda: self._sort_by("codigo"))
        self.tree.column("codigo", width=160, anchor="w")
        self.tree.heading("id", text="ID", command=lambda: self._sort_by("id"))
        self.tree.heading("nombre", text="Nombre", command=lambda: self._sort_by("nombre"))
        self.tree.heading("precio", text="Precio", command=lambda: self._sort_by("precio"))
        self.tree.heading("stock", text="Stock", command=lambda: self._sort_by("stock"))
        self.tree.heading("estado", text="Estado", command=lambda: self._sort_by("estado"))

        self.tree.column("id", width=70, anchor="center")
        self.tree.column("nombre", width=360, anchor="w")
        self.tree.column("precio", width=120, anchor="e")
        self.tree.column("stock", width=100, anchor="e")
        self.tree.column("estado", width=110, anchor="center")

        self.tree.pack(side="left", fill=tk.BOTH, expand=True)
        yscroll = ttk.Scrollbar(grid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=yscroll.set)
        yscroll.pack(side="right", fill="y")


        self.tree.tag_configure("even", background=self._get_alt_row_color())
        self.tree.tag_configure("bloq", foreground="#8a0000")  


        self.status = ttk.Label(self, text="Listo", anchor="w")
        self.status.pack(fill="x", padx=10, pady=(0,8))


        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Editar", command=self._edit_producto)
        self.menu.add_command(label="Ingresar stock", command=self._open_ingreso_dialog)
        self.menu.add_separator()
        self.menu.add_command(label="Bloquear / Desbloquear", command=self._toggle_bloqueo)
        self.menu.add_separator()
        self.menu.add_command(label="Copiar ID", command=self._copiar_id)
        self.menu.add_command(label="Actualizar", command=self.load)


        self.tree.bind("<Double-Button-1>", lambda e: self._edit_producto())
        self.tree.bind("<Button-3>", self._show_context) 
        self.e_search.bind("<Return>", lambda e: self._apply_filter())

        self.bind_all("<F5>", lambda e: self.load())
        self.bind_all("<Control-e>", lambda e: self._edit_producto())
        self.bind_all("<Control-E>", lambda e: self._edit_producto())
        self.bind_all("<Control-i>", lambda e: self._open_ingreso_dialog())
        self.bind_all("<Control-I>", lambda e: self._open_ingreso_dialog())
        self.bind_all("<Control-b>", lambda e: self._toggle_bloqueo())
        self.bind_all("<Control-B>", lambda e: self._toggle_bloqueo())

        self.load()

    def _get_alt_row_color(self) -> str:
        return "#f7f9fc"

    def _show_context(self, event):
        try:
            row = self.tree.identify_row(event.y)
            if row:
                self.tree.selection_set(row)
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _selected_item(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Productos", "Seleccioná un producto de la lista")
            return None
        vals = self.tree.item(sel[0], "values")

        return {
            "ProductoID": int(vals[0]),
            "Nombre": vals[1],
            "CodigoBarras": vals[2],
            "PrecioTxt": vals[3],
            "Stock": vals[4],
            "Estado": vals[5],
            "iid": sel[0],
        }

    def _selected_product_full(self):
        row = self._selected_item()
        if not row:
            return None

        activo = (row["Estado"].lower() == "activo")
        return {"ProductoID": row["ProductoID"], "Nombre": row["Nombre"], "Activo": activo}
    
    def load(self):

        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            data = ProductoRepo.listar()
            self._all_rows = data[:] 
            self._render_rows(self._all_rows)
            self.status.config(text=f"{len(self._all_rows)} productos")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _render_rows(self, rows):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for idx, d in enumerate(rows):
            estado = "Activo" if d["Activo"] else "Bloqueado"
            tags = ("even",) if idx % 2 == 0 else ()
            if not d["Activo"]:
                tags = tags + ("bloq",)
            self.tree.insert(
                "", tk.END,
                values=(d["ProductoID"], d["Nombre"], d.get("CodigoBarras") or "",
                        fmt_money(d["Precio"]), d["Stock"], estado),
                tags=tags
            )

    def _apply_filter(self):
        q = (self.e_search.get() or "").strip().lower()
        if not q:
            self._render_rows(self._all_rows)
            self.status.config(text=f"{len(self._all_rows)} productos")
            return
        filtered = []
        for d in self._all_rows:
            if q.isdigit():
                if str(d["ProductoID"]) == q:
                    filtered.append(d)
            else:
                if q in (d["Nombre"] or "").lower() or q in (d.get("CodigoBarras") or "").lower():
                    filtered.append(d)
        self._render_rows(filtered)
        self.status.config(text=f"{len(filtered)} productos (filtrado)")

    def _clear_filter(self):
        self.e_search.delete(0, tk.END)
        self._render_rows(self._all_rows)
        self.status.config(text=f"{len(self._all_rows)} productos")

    def _sort_by(self, key):
        def keyfn(d):
            if key == "codigo": return (d.get("CodigoBarras") or "").lower()
            if key == "id":     return d["ProductoID"]
            if key == "nombre": return (d["Nombre"] or "").lower()
            if key == "precio": return float(d["Precio"] or 0)
            if key == "stock":  return float(d["Stock"] or 0)
            if key == "estado": return 1 if d["Activo"] else 0
            return 0

        asc = not self._sort_state.get(key, True)
        self._sort_state[key] = asc
        rows = sorted(self._all_rows, key=keyfn, reverse=not asc)

        q = (self.e_search.get() or "").strip().lower()
        if q:
            self._render_rows([
                r for r in rows
                if (q.isdigit() and str(r["ProductoID"]) == q)
                or (not q.isdigit() and (
                        q in (r["Nombre"] or "").lower()
                        or q in (r.get("CodigoBarras") or "").lower()
                ))
            ])
        else:
            self._render_rows(rows)

    def _add_producto(self):
        nombre = simpledialog.askstring("Producto", "Nombre:", parent=self)
        if not nombre:
            return
        try:
            precio = float(simpledialog.askstring("Producto", "Precio:", parent=self))
            stock = int(simpledialog.askstring("Producto", "Stock inicial:", parent=self) or "0")
        except Exception:
            messagebox.showerror("Error", "Precio/Stock inválidos")
            return

        codigo = simpledialog.askstring("Producto", "Código de barras (opcional):", parent=self) or ""
        codigo = codigo.strip() or None

        try:

            ProductoRepo.crear(nombre, precio, stock, codigo_barras=codigo)
            self.load()
            self.status.config(text=f"Producto '{nombre}' creado")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _edit_producto(self):
        sel = self._selected_item()
        if not sel:
            return
        dlg = EditarProductoDialog(self, sel["ProductoID"])
        self.wait_window(dlg)
        if getattr(dlg, "ok", False):
            self.load()

    def _open_ingreso_dialog(self):
        p = self._selected_product_full()
        if not p:
            return
        if not p["Activo"]:
            messagebox.showwarning("Bloqueado", "Este producto está bloqueado. Desbloquealo para operar.")
            return
        dlg = IngresoStockDialog(self, p, self.current_user)
        self.wait_window(dlg)
        if getattr(dlg, "ok", False):
            self.load()

    def _toggle_bloqueo(self):
        p = self._selected_product_full()
        if not p:
            return
        pid = p["ProductoID"]
        try:
            if p["Activo"]:
                if not messagebox.askyesno(
                    "Bloquear producto",
                    f"¿Bloquear '{p['Nombre']}'?\nNo podrá venderse ni recibir stock hasta desbloquearlo.",
                    parent=self
                ):
                    return
                ProductoRepo.set_estado(pid, False)
                self.status.config(text=f"'{p['Nombre']}' bloqueado")
            else:
                if not messagebox.askyesno(
                    "Desbloquear producto",
                    f"¿Desbloquear '{p['Nombre']}'?", parent=self
                ):
                    return
                ProductoRepo.set_estado(pid, True)
                self.status.config(text=f"'{p['Nombre']}' desbloqueado")
            self.load()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _copiar_id(self):
        sel = self._selected_item()
        if not sel:
            return
        self.clipboard_clear()
        self.clipboard_append(str(sel["ProductoID"]))
        self.status.config(text=f"ID {sel['ProductoID']} copiado")

class EditarProductoDialog(tk.Toplevel):
    def __init__(self, master, producto_id: int):
        super().__init__(master)
        self.title(f"Editar producto — ID {producto_id}")
        self.resizable(False, False)
        self.transient(master); self.grab_set()
        self.ok = False

        p = ProductoRepo.buscar_por_id(producto_id)
        if not p:
            messagebox.showerror("Error", "Producto no encontrado")
            self.destroy(); return

        ttk.Label(self, text=f"ID: {producto_id}").grid(row=0, column=0, columnspan=2,
                                                        sticky="w", padx=12, pady=(12,2))

        ttk.Label(self, text="Nombre:").grid(row=1, column=0, sticky="e", padx=12, pady=6)
        self.e_nombre = ttk.Entry(self, width=34); self.e_nombre.grid(row=1, column=1, sticky="w", padx=12, pady=6)
        self.e_nombre.insert(0, p["Nombre"] or "")

        ttk.Label(self, text="Precio:").grid(row=2, column=0, sticky="e", padx=12, pady=6)
        self.e_precio = ttk.Entry(self, width=14); self.e_precio.grid(row=2, column=1, sticky="w", padx=12, pady=6)
        self.e_precio.insert(0, f"{float(p['Precio'] or 0):.2f}")

        ttk.Label(self, text="Código de barras:").grid(row=3, column=0, sticky="e", padx=12, pady=6)
        self.e_codigo = ttk.Entry(self, width=34); self.e_codigo.grid(row=3, column=1, sticky="w", padx=12, pady=6)
        self.e_codigo.insert(0, p.get("CodigoBarras") or "")

        btns = ttk.Frame(self); btns.grid(row=10, column=0, columnspan=2, pady=(8,12))
        ttk.Button(btns, text="Guardar", command=lambda: self._guardar(producto_id)).pack(side="left", padx=6)
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side="left")

        self.bind("<Return>", lambda e: self._guardar(producto_id))
        self.e_nombre.focus()

    def _guardar(self, producto_id: int):
        nombre = (self.e_nombre.get() or "").strip()
        if not nombre:
            messagebox.showerror("Error", "El nombre no puede estar vacío"); return
        try:
            precio = float(self.e_precio.get())
        except Exception:
            messagebox.showerror("Error", "Precio inválido"); return
        codigo = (self.e_codigo.get() or "").strip() or None

        try:
            ProductoRepo.actualizar(producto_id, nombre, precio, codigo_barras=codigo)
            self.ok = True
            self.destroy()
        except Exception as e:
            messagebox.showerror("DB", str(e))

class IngresoStockDialog(tk.Toplevel):
    """Registrar ingresos de stock para un producto activo."""
    def __init__(self, master, producto: dict, current_user: dict):
        super().__init__(master)
        self.title(f"Ingreso de stock — {producto['Nombre']}")
        self.resizable(False, False)
        self.transient(master); self.grab_set()
        self.ok = False

        ttk.Label(self, text=f"Producto: {producto['Nombre']} (ID {producto['ProductoID']})").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12,2)
        )

        ttk.Label(self, text="Cantidad (+):").grid(row=1, column=0, sticky="e", padx=12, pady=6)
        self.e_cant = ttk.Entry(self, width=14); self.e_cant.grid(row=1, column=1, sticky="w", padx=12, pady=6)

        ttk.Label(self, text="Costo unit.:").grid(row=2, column=0, sticky="e", padx=12, pady=6)
        self.e_costo = ttk.Entry(self, width=14); self.e_costo.grid(row=2, column=1, sticky="w", padx=12, pady=6)

        ttk.Label(self, text="Precio venta:").grid(row=3, column=0, sticky="e", padx=12, pady=6)
        self.e_pven = ttk.Entry(self, width=14); self.e_pven.grid(row=3, column=1, sticky="w", padx=12, pady=6)

        btns = ttk.Frame(self); btns.grid(row=10, column=0, columnspan=2, pady=(8,12))
        ttk.Button(btns, text="Registrar",
                   command=lambda: self._ok(producto, current_user)).pack(side="left", padx=6)
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side="left")

        self.bind("<Return>", lambda e: self._ok(producto, current_user))
        self.e_cant.focus()

    def _ok(self, producto, current_user):
        try:
            cant = float(self.e_cant.get()); costo = float(self.e_costo.get()); pven = float(self.e_pven.get())
            if cant <= 0 or costo < 0 or pven < 0: raise ValueError
        except Exception:
            messagebox.showerror("Error", "Revisá cantidad, costo y precio"); return

        try:
            info = IngresoStockRepo.ingresar(
                usuario_id=current_user["UsuarioID"],
                producto_id=producto["ProductoID"],
                cantidad=cant,
                costo_unit=costo,
                precio_venta=pven,
            )
            messagebox.showinfo(
                "Ingreso registrado",
                f"Stock: {info['stock_anterior']} → {info['stock_nuevo']}\n"
                f"Precio: {info['precio_anterior']:.2f} → {info['precio_nuevo']:.2f}"
            )
            self.ok = True
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))
