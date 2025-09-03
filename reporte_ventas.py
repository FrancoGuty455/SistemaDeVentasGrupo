import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
from repos import VentaRepo, ClienteRepo

class ReporteVentasFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # Toolbar
        toolbar = ttk.Frame(self); toolbar.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(toolbar, text="Actualizar", command=self.load).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Exportar en Excel", command=self.export_csv).pack(side=tk.LEFT, padx=6)

        # Tabla
        cols = ("id", "fecha", "cliente", "total", "metodo")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        for col, txt, w in [
            ("id", "ID", 60),
            ("fecha", "Fecha", 160),
            ("cliente", "Cliente", 220),
            ("total", "Total", 120),
            ("metodo", "Pago", 120)
        ]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor=tk.CENTER if col!="cliente" else tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.load()

    def load(self):
        """Carga las ventas desde el repositorio"""
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            data = VentaRepo.listar() 
            for d in data:
                cliente = f"{d['ClienteID']} - {d.get('ClienteNombre','')}" if d.get("ClienteID") else "Consumidor Final"
                self.tree.insert("", tk.END, values=(
                    d["VentaID"], d["Fecha"], cliente,
                    f"${float(d['Total']):.2f}", d.get("MetodoPago","-")
                ))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def export_csv(self):
        file = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if not file: return
        try:
            with open(file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Fecha", "Cliente", "Total", "Método de pago"])
                for row in self.tree.get_children():
                    writer.writerow(self.tree.item(row)["values"])
            messagebox.showinfo("Éxito", f"Ventas exportadas a {file}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
