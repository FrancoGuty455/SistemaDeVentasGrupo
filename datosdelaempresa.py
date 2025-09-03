import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from repos import EmpresaRepo

class DatosEmpresaFrame(ttk.Frame):
    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.on_saved = on_saved

        frm = ttk.Frame(self); frm.pack(fill="both", expand=True, padx=12, pady=12)
        frm.columnconfigure(1, weight=1)

        self.vars = {k: tk.StringVar() for k in ("Nombre","CUIT","CondicionIVA","Direccion","Telefono","Email","LogoPath")}

        row = 0
        for label, key in [
            ("Nombre comercial*", "Nombre"),
            ("CUIT", "CUIT"),
            ("Condición IVA", "CondicionIVA"),
            ("Dirección", "Direccion"),
            ("Teléfono", "Telefono"),
            ("Email", "Email"),
            ("Logo (ruta opcional)", "LogoPath"),
        ]:
            ttk.Label(frm, text=label).grid(row=row, column=0, sticky="e", padx=(0,8), pady=6)
            ent = ttk.Entry(frm, textvariable=self.vars[key])
            ent.grid(row=row, column=1, sticky="ew", pady=6)
            if key == "LogoPath":
                ttk.Button(frm, text="Examinar…", command=self._pick_logo).grid(row=row, column=2, padx=6)
            row += 1

        btns = ttk.Frame(frm); btns.grid(row=row, column=0, columnspan=3, pady=(12,0), sticky="w")
        ttk.Button(btns, text="Guardar", style="success.TButton", command=self._save).pack(side="left")
        ttk.Button(btns, text="Recargar", command=self._load).pack(side="left", padx=6)

        self._load()

    def _pick_logo(self):
        path = filedialog.askopenfilename(
            title="Seleccioná el logo (png/jpg)",
            filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"), ("Todos", "*.*")]
        )
        if path:
            self.vars["LogoPath"].set(path)

    def _load(self):
        try:
            info = EmpresaRepo.obtener()
            for k in self.vars:
                self.vars[k].set(info.get(k) or "")
        except Exception as e:
            messagebox.showerror("Empresa", str(e))

    def _save(self):
        nombre = self.vars["Nombre"].get().strip()
        if not nombre:
            messagebox.showerror("Empresa", "El nombre comercial es obligatorio."); return
        try:
            EmpresaRepo.guardar(
                nombre=nombre,
                cuit=self.vars["CUIT"].get().strip() or None,
                condicion=self.vars["CondicionIVA"].get().strip() or None,
                direccion=self.vars["Direccion"].get().strip() or None,
                telefono=self.vars["Telefono"].get().strip() or None,
                email=self.vars["Email"].get().strip() or None,
                logo_path=(self.vars["LogoPath"].get().strip() or None)
            )
            messagebox.showinfo("Empresa", "Datos guardados.")
            if callable(self.on_saved): self.on_saved()
        except Exception as e:
            messagebox.showerror("Empresa", str(e))
