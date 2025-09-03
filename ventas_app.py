import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from config import ensure_schema
from repos import ProductoRepo, ClienteRepo, VentaRepo, UsuarioRepo
import ttkbootstrap as tb
from productos import ProductosFrame
from pdf_ticket import generar_ticket_pdf
from cierredecaja import CierreDeCajaFrame 
from repos import ProductoRepo, ClienteRepo, VentaRepo, UsuarioRepo, EmpresaRepo
from datosdelaempresa import DatosEmpresaFrame
from reporte_ventas import ReporteVentasFrame

def center_to_parent(win, parent=None, pad=(0, 0)):
    win.update_idletasks()
    try:
        if parent and parent.winfo_ismapped():
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            ww, wh = win.winfo_reqwidth(), win.winfo_reqheight()
            x = px + (pw - ww)//2 + pad[0]
            y = py + (ph - wh)//2 + pad[1]
        else:
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            ww, wh = win.winfo_reqwidth(), win.winfo_reqheight()
            x = (sw - ww)//2
            y = (sh - wh)//2
        win.geometry(f"+{max(0, x)}+{max(0, y)}")
    except Exception:

        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        ww, wh = win.winfo_reqwidth(), win.winfo_reqheight()
        x = (sw - ww)//2
        y = (sh - wh)//2
        win.geometry(f"+{max(0, x)}+{max(0, y)}")


class LoginDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Iniciar sesión")
        self.geometry("360x240")
        self.resizable(False, False)

        ttk.Label(self, text="Número de usuario").pack(pady=(16,4))
        self.ent_num = ttk.Entry(self, width=30); self.ent_num.pack()
        ttk.Label(self, text="Contraseña").pack(pady=(10,4))
        self.ent_pass = ttk.Entry(self, show='*', width=30); self.ent_pass.pack()
        btn_frame = ttk.Frame(self); btn_frame.pack(pady=16, fill=tk.X, padx=16)
        ttk.Button(btn_frame, text="Iniciar", command=self._login).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="Cambiar contraseña", command=self._open_change).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=6)
        ttk.Button(btn_frame, text="Cancelar", command=self._cancel).pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.result = None
        self.ent_num.focus()


        self.update_idletasks()        
        center_to_parent(self, master) 

        self.ent_num.bind('<Return>', lambda e: self.ent_pass.focus_set())
        self.ent_pass.bind('<Return>', lambda e: self._login())
        self.bind('<Escape>', lambda e: self._cancel())

        self.lift(); self.focus_force()
        try:
            self.attributes('-topmost', True)
            self.after(200, lambda: self.attributes('-topmost', False))
        except: 
            pass
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self._busy = False

    def _login(self):
        if self._busy:
            return
        self._busy = True
        try:
            numero = self.ent_num.get().strip()
            pw = self.ent_pass.get()
            if not numero or not pw:
                messagebox.showerror("Error", "Completá usuario y contraseña"); return
            user = UsuarioRepo.autenticar(numero, pw)
            if not user:
                messagebox.showerror("Error", "Credenciales inválidas o usuario inactivo"); return
            if user['ForzarCambio']:
                messagebox.showinfo("Aviso", "Debés cambiar tu contraseña antes de continuar.")
                self._open_change(prefill_num=numero)
                return
            self.result = user
            self.destroy()
        finally:
            self._busy = False

    def _open_change(self, prefill_num: str=None):
        dlg = ChangePasswordDialog(self, prefill_num or self.ent_num.get().strip())
        self.wait_window(dlg)  

    def _cancel(self):
        self.result = None
        self.destroy()




class ChangePasswordDialog(tk.Toplevel):
    def __init__(self, master, numero_prefill: str=''):
        super().__init__(master)
        self.title("Cambiar contraseña")
        self.geometry("360x360"); self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())
        ttk.Label(self, text="Número de usuario").pack(pady=(16,4))
        self.ent_num = ttk.Entry(self, width=30); self.ent_num.pack()
        self.ent_num.insert(0, numero_prefill)

        ttk.Label(self, text="Contraseña actual").pack(pady=(10,4))
        self.ent_old = ttk.Entry(self, show='*', width=30); self.ent_old.pack()

        ttk.Label(self, text="Nueva contraseña").pack(pady=(10,4))
        self.ent_new = ttk.Entry(self, show='*', width=30); self.ent_new.pack()
        ttk.Label(self, text="Repetir nueva").pack(pady=(10,4))
        self.ent_new2 = ttk.Entry(self, show='*', width=30); self.ent_new2.pack()

        btns = ttk.Frame(self); btns.pack(pady=16, fill=tk.X, padx=16)
        ttk.Button(btns, text="Guardar", command=self._save).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(btns, text="Cerrar", command=self.destroy).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=6)
        center_to_parent(self)

        self.lift()
        self.focus_force()
        try:
            self.attributes('-topmost', True)
            self.after(200, lambda: self.attributes('-topmost', False))
        except Exception:
            pass
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _save(self):
        numero = self.ent_num.get().strip()
        old = self.ent_old.get()
        new = self.ent_new.get()
        new2 = self.ent_new2.get()
        if not numero or not old or not new:
            messagebox.showerror("Error", "Completá todos los campos"); return
        if new != new2:
            messagebox.showerror("Error", "Las contraseñas nuevas no coinciden"); return
        user = UsuarioRepo.autenticar(numero, old)
        if not user:
            messagebox.showerror("Error", "Usuario/contraseña actual incorrectos"); return
        UsuarioRepo.cambiar_password(user['UsuarioID'], new, forzar_cambio=False)
        messagebox.showinfo("Éxito", "Contraseña actualizada.")
        self.destroy()


class VentasWindow(tk.Toplevel):
    def __init__(self, master, current_user):
        super().__init__(master)
        self.current_user = current_user
        self.title(f"Sistema de Ventas - {current_user['Numero']} ({current_user['Rol']})")
        self.geometry("1000x680")
        self.resizable(True, True)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        topbar = ttk.Frame(self)
        topbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(
            topbar,
            text=f"Sesión: {current_user['Numero']} ({current_user['Rol']})",
            font=('Segoe UI', 10, 'bold')
        ).pack(side=tk.LEFT, padx=8, pady=6)

        self.lbl_empresa = ttk.Label(topbar, text=self._empresa_text(), foreground="#374151")
        self.lbl_empresa.pack(side=tk.LEFT, padx=12)

        ttk.Button(topbar, text="Cambiar contraseña", style="secondary.Outline.TButton", command=self._open_change_pw).pack(side=tk.RIGHT, padx=6)
        ttk.Button(topbar, text="Cerrar sesión", style="danger.TButton", command=self._logout).pack(side=tk.RIGHT, padx=6)


        self.status = ttk.Label(self, text="Listo", anchor="w")
        self.status.pack(side="bottom", fill="x")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True)

        if self.current_user['Rol'] == 'Admin':
            self.tab_productos = ProductosFrame(self.nb, self.current_user)  
            self.tab_clientes = ClientesFrame(self.nb)
            self.tab_nueva_venta = NuevaVentaFrame(self.nb)
            self.tab_usuarios = UsuariosFrame(self.nb)
            self.tab_cierre = CierreDeCajaFrame(self.nb, self.current_user) 
            self.tab_empresa = DatosEmpresaFrame(self.nb, on_saved=lambda: self.lbl_empresa.config(text=self._empresa_text()))
            self.tab_reporte = ReporteVentasFrame(self.nb)
            
            
            self.nb.add(self.tab_productos, text="Productos")
            self.nb.add(self.tab_nueva_venta, text="Nueva Venta")
            self.nb.add(self.tab_reporte, text="Reporte de Ventas")
            self.nb.add(self.tab_clientes, text="Clientes")
            self.nb.add(self.tab_usuarios, text="Usuarios")
            self.nb.add(self.tab_cierre, text="Cierre de Caja")
            self.nb.add(self.tab_empresa, text="Datos de la Empresa") 
        else:
            self.tab_nueva_venta = NuevaVentaFrame(self.nb)
            self.nb.add(self.tab_nueva_venta, text="Nueva Venta")


        self.bind_all("<F11>", lambda e: self._toggle_fullscreen())
        self.bind_all("<Escape>", lambda e: self._exit_fullscreen())
        self.bind_all("<Control-n>", lambda e: self._nueva_venta_atajo())
        self.bind_all("<Control-l>", lambda e: self._logout())
        self.bind_all("<Insert>", self._handle_insert)

    def _empresa_text(self) -> str:
        try:
            e = EmpresaRepo.obtener()
            partes = [e.get("Nombre") or "Empresa"]
            if e.get("CUIT"): partes.append(f"CUIT {e['CUIT']}")
            if e.get("CondicionIVA"): partes.append(e["CondicionIVA"])
            if e.get("Direccion"): partes.append(e["Direccion"])
            return "  •  ".join(partes)
        except Exception:
            return "Empresa"

    def _handle_insert(self, event=None):
        try:
            
            current = self.nb.nametowidget(self.nb.select())
            
            if hasattr(current, "_open_product_picker"):
                current._open_product_picker()
        except Exception:
            pass



    def _on_close(self):

        try:
            self.master.destroy()
        except Exception:
            pass

    def _open_change_pw(self):
        dlg = ChangePasswordDialog(self, numero_prefill=self.current_user['Numero'])
        self.wait_window(dlg)
    def _toggle_fullscreen(self):
        try:
            is_full = self.master.attributes("-fullscreen")
            self.master.attributes("-fullscreen", not is_full)
        except Exception:
            self.state('zoomed')

    def _exit_fullscreen(self):
        try:
            self.master.attributes("-fullscreen", False)
        except Exception:
            pass

    def _logout(self):

        self.master.withdraw()
        self.destroy()

        dlg = LoginDialog(self.master)
        dlg.update_idletasks()
        try: dlg.wait_visibility()
        except: pass
        self.master.wait_window(dlg)

        if getattr(dlg, "result", None):
            app = VentasWindow(self.master, dlg.result)  
            try:
                app.state('zoomed')                      
            except Exception:
                pass
            self.master.deiconify()
        else:
            self.master.destroy()

    def _nueva_venta_atajo(self):

        for i in range(self.children['!notebook'].index('end')):
            self.children['!notebook'].select(i)  
            break


class ClientesFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        toolbar = ttk.Frame(self); toolbar.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(toolbar, text="Añadir Cliente", command=self.add_cliente).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Actualizar", command=self.load).pack(side=tk.LEFT, padx=6)

        self.tree = ttk.Treeview(self, columns=("id","nombre","email","telefono","activo"), show='headings')
        for col, txt, w in [("id","ID",60),("nombre","Nombre",240),("email","Email",220),("telefono","Teléfono",120),("activo","Activo",70)]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor=tk.CENTER if col!="nombre" else tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.load()

    def load(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            data = ClienteRepo.listar()
            for d in data:
                self.tree.insert('', tk.END, values=(d['ClienteID'], d['Nombre'], d['Email'] or '', d['Telefono'] or '', 'Sí' if d['Activo'] else 'No'))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def add_cliente(self):
        nombre = simpledialog.askstring("Cliente", "Nombre:", parent=self)
        if not nombre: return
        email = simpledialog.askstring("Cliente", "Email (opcional):", parent=self)
        telefono = simpledialog.askstring("Cliente", "Teléfono (opcional):", parent=self)
        try:
            ClienteRepo.crear(nombre, email, telefono)
            self.load()
        except Exception as e:
            messagebox.showerror("Error", str(e))


class NuevaVentaFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.items = []
        self._producto_actual = None
        


        top = ttk.Frame(self); top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 6))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Cliente:").grid(row=0, column=0, sticky="w")
        self.cb_cliente = ttk.Combobox(top, state='readonly', width=40)
        self.cb_cliente.grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(top, text="Actualizar", command=self._load_clientes).grid(row=0, column=2, padx=6)

        ttk.Label(top, text="Código / Búsqueda:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.ent_input = ttk.Entry(top)  
        self.ent_input.grid(row=1, column=1, sticky="ew", padx=6, pady=(8, 0))
        ttk.Button(top, text="Buscar/Agregar (Enter / F2)", command=self._unified_enter)\
            .grid(row=1, column=2, padx=6, pady=(8, 0))


        self.ent_input.bind("<KeyRelease>", self._on_type_product)        
        self.ent_input.bind("<Return>", lambda e: self._unified_enter()) 
        self.bind_all("<F2>", lambda e: self._unified_enter())            

        center = ttk.Frame(self); center.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=6)
        self.rowconfigure(1, weight=1); self.columnconfigure(0, weight=1); center.columnconfigure(0, weight=1)

        tbl = ttk.Frame(center); tbl.grid(row=0, column=0, sticky="nsew")
        tbl.rowconfigure(0, weight=1); tbl.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(tbl, columns=("producto","precio","cantidad","subtotal"), show='headings')
        for col, txt, w, anchor in [
            ("producto","Producto",420,"w"),
            ("precio","Precio",110,"e"),
            ("cantidad","Cant.",90,"center"),
            ("subtotal","Subtotal",130,"e")
        ]:
            self.tree.heading(col, text=txt); self.tree.column(col, width=w, anchor=anchor)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(tbl, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=yscroll.set); yscroll.grid(row=0, column=1, sticky="ns")


        side = ttk.Frame(center); side.grid(row=0, column=1, sticky="nsw", padx=(10, 0))
        ttk.Label(side, text="TOTAL", font=("Segoe UI", 14, "bold")).pack(anchor="e")
        self.lbl_total = ttk.Label(side, text="$0.00", font=("Segoe UI", 28, "bold"))
        self.lbl_total.pack(anchor="e", pady=(0, 10))
        qty = ttk.Frame(side); qty.pack(fill="x", pady=4)
        ttk.Label(qty, text="Precio:").pack(side="left")
        self.ent_precio = ttk.Entry(qty, width=10); self.ent_precio.pack(side="left", padx=6)
        ttk.Label(qty, text="Cant.:").pack(side="left")
        self.ent_cantidad = ttk.Entry(qty, width=6); self.ent_cantidad.pack(side="left", padx=6)
        btns = ttk.Frame(side); btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Añadir (F2)", style="success.TButton", command=self.add_item).pack(fill="x", pady=3)
        ttk.Button(btns, text="Eliminar ítem (Del)", style="secondary.TButton", command=self.eliminar_item).pack(fill="x", pady=3)
        ttk.Button(btns, text="Pagar (F10)", style="primary.TButton", command=self.pagar).pack(fill="x", pady=(10,3))

        ticket = ttk.LabelFrame(side, text="Ticket"); ticket.pack(fill="both", expand=True, pady=(10, 0))
        self.txt_ticket = tk.Text(ticket, width=34, height=18, state="disabled")
        self.txt_ticket.pack(fill="both", expand=True, padx=6, pady=6)

        self.bind_all("<Delete>", lambda e: self.eliminar_item())
        self.bind_all("<F10>", lambda e: self.pagar())


        self._load_clientes()
        self._load_productos_initial()


        self._sug_win = None
        self._sug_list = None
        self._type_after = None


        self.cb_cliente.configure(state="normal")
        self.cb_cliente.bind("<KeyRelease>", self._on_type_cliente)

        self.ent_input.bind("<Down>", lambda e: (self._sug_list and self._sug_list.focus_set()))
        if self._sug_list:
            self._sug_list.bind("<Up>",   lambda e: (self.ent_input.focus_set() if self._sug_list.curselection()==(0,) else None))
        self.bind_all("<Button-1>", lambda e: self._hide_suggestions())


        self.after(200, lambda: self.ent_input.focus_set())

        self._last_key_ts = None
        self._scan_buffer = ""
        self.ent_input.bind("<Key>", self._key_timing)

    def _open_product_picker(self):
        dlg = ProductPickerDialog(self)
        self.wait_window(dlg)
        prod = getattr(dlg, "result", None)
        if prod:
            
            self._set_producto_inputs(prod)
            try:
                self.ent_cantidad.focus_set()
                self.ent_cantidad.selection_range(0, tk.END)
            except Exception:
                pass

    def _key_timing(self, event):
        import time
        now = time.time()
        if self._last_key_ts is None or (now - self._last_key_ts) > 0.12:

            self._scan_buffer = ""
        self._last_key_ts = now
        if len(event.char) == 1 and event.char.isprintable():
            self._scan_buffer += event.char

    def _unified_enter(self):
        q = (self.ent_input.get() or "").strip()
        if not q:
            messagebox.showinfo("Búsqueda", "Escribí código o parte del nombre")
            return

        p = None
        try:
            p = ProductoRepo.buscar_por_codigo(q)
        except Exception:
            p = None
        if p:
            self._set_producto_inputs(p); self.add_item()
            self.ent_input.delete(0, tk.END); self._hide_suggestions()
            self._scan_buffer = ""
            return

        try:
            lst = ProductoRepo.buscar_nombre_contiene(q)
        except Exception:
            lst = []

        if not lst:
            messagebox.showinfo("Búsqueda", "Producto no encontrado")
            return

        if len(lst) == 1:
            self._set_producto_inputs(lst[0]); self.add_item()
            self.ent_input.delete(0, tk.END); self._hide_suggestions()
            self._scan_buffer = ""
            return


        self._show_product_suggestions()

    def _on_type_product(self, event):

        if event.keysym in ("Up","Down","Left","Right","Escape","Return","Tab","Shift_L","Shift_R","Control_L","Control_R","Alt_L","Alt_R"):
            return
        if self._type_after:
            try: self.after_cancel(self._type_after)
            except Exception: pass
        self._type_after = self.after(120, self._show_product_suggestions)


    def _show_product_suggestions(self):
        q = (self.ent_input.get() or "").strip()
        if len(q) < 2:
            self._hide_suggestions()
            return 
        try:
            rows = ProductoRepo.buscar_nombre_contiene(q)
        except Exception:
            rows = []
        if not rows:
            self._hide_suggestions(); return

        if self._sug_win is None or not self._sug_win.winfo_exists():
            self._sug_win = tk.Toplevel(self)
            self._sug_win.wm_overrideredirect(True)
            self._sug_list = tk.Listbox(self._sug_win, height=8, width=46)
            self._sug_list.pack(fill="both", expand=True)
            self._sug_list.bind("<Double-Button-1>", lambda e: self._pick_suggestion())
            self._sug_list.bind("<Return>", lambda e: self._pick_suggestion())
            self._sug_list.bind("<Escape>", lambda e: self._hide_suggestions())
            self._sug_list.bind("<FocusOut>", lambda e: self._hide_suggestions())

        x = self.ent_input.winfo_rootx()
        y = self.ent_input.winfo_rooty() + self.ent_input.winfo_height()
        self._sug_win.geometry(f"+{x}+{y}")

        self._sug_list.delete(0, tk.END)
        self._sug_cache = rows
        for r in rows:
            self._sug_list.insert(tk.END, f"{(r['Nombre'] or '')[:42]} — ${float(r['Precio']):.2f}  (Stock: {r['Stock']})")

        self._sug_win.deiconify()
        self._sug_list.focus_set()
        self._sug_list.selection_clear(0, tk.END)
        self._sug_list.selection_set(0)


    def _hide_suggestions(self):
        if self._sug_win and self._sug_win.winfo_exists():
            self._sug_win.withdraw()

    def _pick_suggestion(self):
        if not self._sug_list:
            return
        sel = self._sug_list.curselection()
        if not sel:
            return
        idx = sel[0]
        p = self._sug_cache[idx]
        self._hide_suggestions()
        self._set_producto_inputs(p)
        self.add_item()
        self.ent_input.delete(0, tk.END)

    def _on_type_cliente(self, event):
        """
        Filtra dinámicamente el combo de clientes por lo tipeado.
        Usa la lista ya cargada por ClienteRepo.listar() en _load_clientes().
        """
        typed = (self.cb_cliente.get() or "").strip().lower()
        try:
            base = self.clientes 
        except Exception:
            return
        if not typed:
            self.cb_cliente['values'] = [f"{c['ClienteID']} - {c['Nombre']}" for c in base]
            return
        fil = [c for c in base if typed in (c['Nombre'] or '').lower() or typed in str(c['ClienteID'])]
        self.cb_cliente['values'] = [f"{c['ClienteID']} - {c['Nombre']}" for c in fil]

    def _total_actual(self) -> float:
        return round(sum(it['cantidad'] * it['precio'] for it in self.items), 2)
    def _load_clientes(self):
        try:
            data = ClienteRepo.listar()
            self.clientes = data
            self.cb_cliente['values'] = [f"{c['ClienteID']} - {c['Nombre']}" for c in data]
            if data: self.cb_cliente.current(0)
        except Exception as e: messagebox.showerror("Error",str(e))

    def _load_productos_initial(self):

        pass

    def _buscar_producto(self, texto:str):

        p = None
        try:
            p = ProductoRepo.buscar_por_codigo(texto)
        except: pass
        if p: return p

        lst = ProductoRepo.buscar_nombre_contiene(texto)
        return lst[0] if lst else None


    def _set_producto_inputs(self, p):
        self._producto_actual = p
        self.ent_precio.delete(0,tk.END); self.ent_precio.insert(0,f"{float(p['Precio']):.2f}")
        self.ent_cantidad.delete(0,tk.END); self.ent_cantidad.insert(0,"1")

    def add_item(self):
        p = self._producto_actual
        if not p:
            messagebox.showerror("Error","Seleccioná/buscá un producto"); return
        try:
            precio = float(self.ent_precio.get()); cantidad = float(self.ent_cantidad.get())
            if cantidad <= 0: raise ValueError
        except:
            messagebox.showerror("Error","Precio o cantidad inválida"); return

        self.items.append({
            'producto_id': p['ProductoID'],
            'nombre': p['Nombre'],
            'precio': precio,
            'cantidad': cantidad
        })

        self.ent_input.delete(0, tk.END)
        self._refresh_items()


    def eliminar_item(self):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0]); del self.items[idx]
        self._refresh_items()

    def _refresh_items(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        total = 0.0
        lines = []
        for it in self.items:
            sub = it['cantidad']*it['precio']; total += sub
            self.tree.insert('',tk.END,values=(it['nombre'],f"{it['precio']:.2f}",f"{it['cantidad']:.3f}",f"{sub:.2f}"))
            lines.append(f"{it['nombre'][:22]:<22}  x${it['precio']:.2f}  = ${sub:.2f}")
        self.lbl_total.config(text=f"${total:,.2f}")
        self._render_ticket(lines,total)

    def _render_ticket(self, lines,total):
        self.txt_ticket.config(state="normal"); self.txt_ticket.delete("1.0",tk.END)
        self.txt_ticket.insert(tk.END,"SISTEMA DE VENTAS\n")
        self.txt_ticket.insert(tk.END,"------------------------------\n")
        for ln in lines: self.txt_ticket.insert(tk.END,ln+"\n")
        self.txt_ticket.insert(tk.END,"------------------------------\n")
        self.txt_ticket.insert(tk.END,f"TOTAL: ${total:,.2f}\n")
        self.txt_ticket.config(state="disabled")

    def pagar(self):
        if not self.items:
            messagebox.showinfo("Info", "No hay ítems en la venta")
            return
        total_val = self._total_actual()  
        PaymentDialog(self, total_val, self._confirmar_pago)



    def _confirmar_pago(self, forma, entregado, descuento):
        cliente_id = None
        if self.cb_cliente.current() >= 0 and self.cb_cliente.get():
            try:
                cliente_id = int(self.cb_cliente.get().split(' - ')[0])
            except:
                pass

        total_ui = self._total_actual()
        total_con_desc = round(total_ui * (1 - max(descuento,0)/100.0), 2)
        vuelto_arg = (entregado or 0) - total_con_desc if forma == "Efectivo" else 0
        try:
            items = [
                {'producto_id': it['producto_id'], 'cantidad': it['cantidad'], 'precio': it['precio']}
                for it in self.items
            ]

            venta_id, total_repo, _ = VentaRepo.crear_venta(
                cliente_id,
                items,
                metodo_pago=forma,
                entregado=entregado,
                descuento_pct=descuento,  
                vuelto=vuelto_arg
            )

            try:
                generar_ticket_pdf(venta_id, abrir=True)
            except Exception as e:
                print("WARN PDF:", e) 

            messagebox.showinfo(
                "Éxito",
                f"Venta {venta_id} registrada.\n"
                f"Total: ${total_repo:.2f}\n"
                f"Forma: {forma}\n"
                f"Entregado: ${entregado:.2f}\n"
                f"Vuelto: ${vuelto_arg:.2f}"
            )
            self.items.clear()
            self._refresh_items()

        except Exception as e:
            messagebox.showerror("Error", str(e))


class PaymentDialog(tk.Toplevel):
    def __init__(self, master, total_val, on_confirm):
        super().__init__(master)
        self.title("Pago")
        self.resizable(False, False)
        self.transient(master)
        center_to_parent(self, master)
        self.bind("<Escape>", lambda e: self.destroy())
        self.on_confirm = on_confirm
        self.total_val = float(total_val)

        ttk.Label(self, text=f"Total: ${self.total_val:,.2f}", font=("Segoe UI", 16, "bold"))\
            .grid(row=0, column=0, columnspan=2, padx=12, pady=(12,6), sticky="e")

        ttk.Label(self, text="Forma de pago:").grid(row=1, column=0, sticky="w", padx=12)
        self.cb_forma = ttk.Combobox(self, state="readonly",
                                     values=["Efectivo", "Tarjeta", "Transferencia"])
        self.cb_forma.grid(row=1, column=1, sticky="ew", padx=(0,12), pady=4)
        self.cb_forma.current(0)

        ttk.Label(self, text="Descuento (%):").grid(row=2, column=0, sticky="w", padx=12)
        self.ent_desc = ttk.Entry(self, width=10); self.ent_desc.grid(row=2, column=1, sticky="w", padx=(0,12), pady=4)
        self.ent_desc.insert(0, "0")

        ttk.Label(self, text="Entregado ($):").grid(row=3, column=0, sticky="w", padx=12)
        self.ent_entregado = ttk.Entry(self, width=12); self.ent_entregado.grid(row=3, column=1, sticky="w", padx=(0,12), pady=4)

        ttk.Label(self, text="Total con desc.:").grid(row=4, column=0, sticky="w", padx=12)
        self.lbl_total_desc = ttk.Label(self, text="$0.00", font=("Segoe UI", 11, "bold"))
        self.lbl_total_desc.grid(row=4, column=1, sticky="w", padx=(0,12), pady=4)

        ttk.Label(self, text="Vuelto ($):").grid(row=5, column=0, sticky="w", padx=12)   
        self.lbl_vuelto = ttk.Label(self, text="$0.00", font=("Segoe UI", 11, "bold"))
        self.lbl_vuelto.grid(row=5, column=1, sticky="w", padx=(0,12), pady=4)

        btns = ttk.Frame(self); btns.grid(row=6, column=0, columnspan=2, sticky="ew", padx=12, pady=(10,12)) 
        ttk.Button(btns, text="Confirmar (F10)", style="Accent.TButton", command=self._ok)\
            .pack(side="left", padx=(0,8))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side="left")
        
        self._done = False 


        self.ent_desc.bind("<KeyRelease>", lambda e: self._recalc())
        center_to_parent(self)
        self.ent_entregado.bind("<KeyRelease>", lambda e: self._recalc())
        self.cb_forma.bind("<<ComboboxSelected>>", lambda e: self._recalc())

        self.bind("<F10>", lambda e: self._ok())
        self.update_idletasks()
        center_to_parent(self, master)
        self.lift(); self.focus_force()

        self._recalc()
        self.after(100, lambda: self.ent_entregado.focus_set())

    def _recalc(self):

        try:
            desc = float(self.ent_desc.get() or 0.0)
        except:
            desc = 0.0


        total_desc = round(self.total_val * (1 - max(desc,0)/100.0), 2)
        self.lbl_total_desc.config(text=f"${total_desc:,.2f}")


        forma = self.cb_forma.get()
        try:
            entregado = float(self.ent_entregado.get() or 0.0)
        except:
            entregado = 0.0

        vuelto = entregado - total_desc if forma == "Efectivo" else 0.0
        self.lbl_vuelto.config(text=f"${vuelto:,.2f}")

        self._done = False
    def _ok(self):
        if self._done: return
        self._done = True
        forma = self.cb_forma.get()
        try:
            entregado = float(self.ent_entregado.get() or 0)
            desc = float(self.ent_desc.get() or 0)
        except:
            messagebox.showerror("Error", "Montos inválidos"); return
        self.destroy()
        self.on_confirm(forma, entregado, desc)

class ProductPickerDialog(tk.Toplevel):
    """
    Selector rápido de productos:
      - Buscar por nombre o código de barras
      - Navegar con ↑/↓, PageUp/PageDown, Home/End
      - Enter / Doble clic: seleccionar
      - ESC: cerrar
    """
    def __init__(self, master):
        super().__init__(master)
        self.title("Seleccionar producto")
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.result = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Buscar:").grid(row=0, column=0, sticky="w")
        self.e_q = ttk.Entry(top, width=38)
        self.e_q.grid(row=0, column=1, sticky="ew", padx=(6, 6))
        self.e_q.bind("<KeyRelease>", lambda e: self._apply_filter())

        self.var_activos = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Sólo activos", variable=self.var_activos,
                        command=self._apply_filter).grid(row=0, column=2, sticky="w")

        cols = ("id", "codigo", "nombre", "precio", "stock")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.tree.heading("id", text="ID")
        self.tree.heading("codigo", text="Código")
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("precio", text="Precio")
        self.tree.heading("stock", text="Stock")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("codigo", width=150, anchor="w")
        self.tree.column("nombre", width=360, anchor="w")
        self.tree.column("precio", width=100, anchor="e")
        self.tree.column("stock", width=90, anchor="e")

        yscroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=yscroll.set)
        yscroll.grid(row=1, column=1, sticky="ns", pady=(0, 10))

        # acciones
        self.tree.bind("<Return>", lambda e: self._choose())
        self.tree.bind("<Double-Button-1>", lambda e: self._choose())
        self.bind("<Escape>", lambda e: self.destroy())

        btns = ttk.Frame(self)
        btns.grid(row=2, column=0, sticky="e", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Seleccionar", command=self._choose,
                   style="Accent.TButton").pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side="left")

        # cargar productos
        try:
            self._all = ProductoRepo.listar()  # debe devolver CodigoBarras si lo agregaste al repo
        except Exception as e:
            self._all = []
            messagebox.showerror("DB", str(e), parent=self)

        self._render(self._all)
        self.update_idletasks()
        self._center(master)
        self.e_q.focus_set()

    def _center(self, parent):
        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            ww, wh = self.winfo_reqwidth(), self.winfo_reqheight()
            x = px + (pw - ww)//2
            y = py + (ph - wh)//2
        except Exception:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            ww, wh = self.winfo_reqwidth(), self.winfo_reqheight()
            x = (sw - ww)//2; y = (sh - wh)//2
        self.geometry(f"+{max(0,x)}+{max(0,y)}")

    def _render(self, rows):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for d in rows:
            self.tree.insert(
                "", tk.END,
                values=(
                    d["ProductoID"],
                    d.get("CodigoBarras") or "",
                    d["Nombre"],
                    f"{float(d['Precio'] or 0):.2f}",
                    f"{float(d['Stock'] or 0):.3f}",
                )
            )
        # seleccionar primera fila
        kids = self.tree.get_children()
        if kids:
            self.tree.selection_set(kids[0])
            self.tree.focus(kids[0])

    def _apply_filter(self):
        q = (self.e_q.get() or "").strip().lower()
        only_active = self.var_activos.get()
        rows = []
        for d in self._all:
            if only_active and not d.get("Activo", True):
                continue
            nombre = (d["Nombre"] or "").lower()
            codigo = (d.get("CodigoBarras") or "").lower()
            if not q or q in nombre or q in codigo or (q.isdigit() and str(d["ProductoID"]) == q):
                rows.append(d)
        self._render(rows)

    def _choose(self):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        pid = int(vals[0])
        try:
            prod = ProductoRepo.buscar_por_id(pid)
        except Exception:
            prod = None
        if prod:
            self.result = prod
            self.destroy()


class UsuariosFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        toolbar = ttk.Frame(self); toolbar.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(toolbar, text="Nuevo usuario", command=self.add_user).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Resetear contraseña", command=self.reset_pass).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Cambiar rol", command=self.change_role).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Activar/Desactivar", command=self.toggle_active).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Actualizar", command=self.load).pack(side=tk.LEFT)

        self.tree = ttk.Treeview(self, columns=("id","numero","nombre","rol","activo","forzar","creado"), show='headings')
        for col, txt, w in [("id","ID",60),("numero","Número",120),("nombre","Nombre",220),("rol","Rol",100),("activo","Activo",80),("forzar","Forzar cambio",120),("creado","Creado",160)]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor=tk.CENTER if col not in ("nombre",) else tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.load()

    def load(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            data = UsuarioRepo.listar()
            for d in data:
                self.tree.insert('', tk.END, values=(d['UsuarioID'], d['Numero'], d['Nombre'] or '', d['Rol'], 'Sí' if d['Activo'] else 'No', 'Sí' if d['ForzarCambio'] else 'No', str(d['CreadoEn'])))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Seleccioná un usuario en la grilla");
            return None
        return int(self.tree.item(sel[0], 'values')[0])

    def add_user(self):
        numero = simpledialog.askstring("Nuevo usuario", "Número (legajo):", parent=self)
        if not numero: return
        nombre = simpledialog.askstring("Nuevo usuario", "Nombre:", parent=self) or ''
        rol = simpledialog.askstring("Nuevo usuario", "Rol (Admin/Vendedor):", parent=self) or 'Vendedor'
        if rol not in ('Admin','Vendedor'):
            messagebox.showerror("Error", "Rol inválido (Admin/Vendedor)"); return
        pw = simpledialog.askstring("Nuevo usuario", "Contraseña inicial:", parent=self, show='*')
        if not pw: return
        try:
            UsuarioRepo.crear(numero, nombre, rol, pw, forzar_cambio=True)
            self.load()
            messagebox.showinfo("Éxito", "Usuario creado. Deberá cambiar su contraseña al iniciar.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def reset_pass(self):
        uid = self._selected_id()
        if not uid: return
        pw = simpledialog.askstring("Resetear contraseña", "Nueva contraseña:", parent=self, show='*')
        if not pw: return
        try:
            UsuarioRepo.cambiar_password(uid, pw, forzar_cambio=True)
            messagebox.showinfo("Éxito", "Contraseña reseteada. Se pedirá cambio al iniciar sesión.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def change_role(self):
        uid = self._selected_id()
        if not uid: return
        rol = simpledialog.askstring("Cambiar rol", "Nuevo rol (Admin/Vendedor):", parent=self)
        if not rol or rol not in ('Admin','Vendedor'):
            messagebox.showerror("Error", "Rol inválido (Admin/Vendedor)"); return
        try:
            UsuarioRepo.set_rol(uid, rol)
            self.load()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def toggle_active(self):
        uid = self._selected_id();
        if not uid: return
        item = self.tree.item(self.tree.selection()[0], 'values')
        activo = True if item[4] == 'Sí' else False
        try:
            UsuarioRepo.set_estado(uid, not activo)
            self.load()
        except Exception as e:
            messagebox.showerror("Error", str(e))




if __name__ == '__main__':
    print("[INIT] Arrancando app…")
    db_ok = True
    try:
        ensure_schema()
        print("[INIT] Schema OK")
    except Exception as e:
        print("[WARN] No se pudo inicializar la DB:", e)
        db_ok = False


    style = tb.Style(theme="flatly")
    root = style.master
    root.title("Sistema de Ventas")


    root.withdraw()


    dlg = LoginDialog(root)
    dlg.update_idletasks()
    try:
        dlg.lift(); dlg.focus_force()
    except Exception:
        pass
    root.wait_window(dlg)

    if getattr(dlg, "result", None):

        app = VentasWindow(root, dlg.result)
        try:
            app.state('zoomed')           
        except Exception:
            pass
        if not db_ok:
            messagebox.showwarning("Aviso", "La base de datos no está disponible. Algunas funciones pueden fallar.")
        root.mainloop()                
    else:
        root.destroy()

