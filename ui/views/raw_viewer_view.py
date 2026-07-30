import customtkinter as ctk
from tkinter import ttk, messagebox
import pandas as pd
import database
from ui.components.modals import DateRangeModal, export_dataframe_dialog

class DataViewerFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="Visor de Datos Crudos (Histórico)", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.fecha_inicio = None
        self.fecha_fin = None

        self.filters_container = ctk.CTkFrame(self, fg_color=("#e2e8f0", "#1f2937"), corner_radius=8)
        self.filters_container.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        row1 = ctk.CTkFrame(self.filters_container, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(row1, text="Comercio:").pack(side="left", padx=2)
        self.fuente_var = ctk.StringVar(value="Todas")
        self.fuente_combo = ctk.CTkComboBox(row1, variable=self.fuente_var, command=self.update_data, width=110)
        self.fuente_combo.pack(side="left", padx=5)

        ctk.CTkLabel(row1, text="Tipo:").pack(side="left", padx=(10, 2))
        self.tipo_var = ctk.StringVar(value="Todos")
        self.tipo_combo = ctk.CTkComboBox(row1, variable=self.tipo_var, values=["Todos", "Alcohol", "Tabaco"], command=self.update_data, width=100)
        self.tipo_combo.pack(side="left", padx=5)

        ctk.CTkLabel(row1, text="Categoría:").pack(side="left", padx=(10, 2))
        self.cat_var = ctk.StringVar(value="Todas")
        self.cat_combo = ctk.CTkComboBox(row1, variable=self.cat_var, command=self.update_data, width=140)
        self.cat_combo.pack(side="left", padx=5)

        self.btn_range = ctk.CTkButton(row1, text="Rango Fechas", fg_color=("#cbd5e1", "#374151"), hover_color=("#94a3b8", "#4b5563"), text_color=("#0f172a", "#f9fafb"), width=110, command=self.open_date_modal)
        self.btn_range.pack(side="left", padx=10)

        self.lbl_range_info = ctk.CTkLabel(row1, text="Todas las fechas", text_color=("#64748b", "#9ca3af"), font=ctk.CTkFont(size=11, slant="italic"))
        self.lbl_range_info.pack(side="left", padx=2)

        row2 = ctk.CTkFrame(self.filters_container, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(row2, text="Buscar:").pack(side="left", padx=2)
        self.search_entry = ctk.CTkEntry(row2, placeholder_text="Nombre, marca o ID...", width=200)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<Return>", lambda e: self.update_data())

        ctk.CTkLabel(row2, text="Precio $ Min:").pack(side="left", padx=(10, 2))
        self.pmin_entry = ctk.CTkEntry(row2, placeholder_text="0", width=80)
        self.pmin_entry.pack(side="left", padx=2)

        ctk.CTkLabel(row2, text="Max:").pack(side="left", padx=(5, 2))
        self.pmax_entry = ctk.CTkEntry(row2, placeholder_text="Max", width=80)
        self.pmax_entry.pack(side="left", padx=2)

        self.descuento_var = ctk.BooleanVar(value=False)
        self.chk_descuento = ctk.CTkCheckBox(row2, text="Solo Ofertas", variable=self.descuento_var, command=self.update_data)
        self.chk_descuento.pack(side="left", padx=15)

        self.btn_search = ctk.CTkButton(row2, text="Aplicar Filtros", fg_color="#2563eb", hover_color="#1d4ed8", command=self.update_data)
        self.btn_search.pack(side="left", padx=5)

        self.btn_export = ctk.CTkButton(row2, text="Exportar (Excel/JSON/CSV)", fg_color="#10b981", hover_color="#059669", command=self.export_data)
        self.btn_export.pack(side="right", padx=5)

        self.btn_remove = ctk.CTkButton(row2, text="Eliminar (Soft)", fg_color="#ef4444", hover_color="#dc2626", command=self.soft_delete_selected)
        self.btn_remove.pack(side="right", padx=5)

        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        columns = ("ID", "Fuente", "Fecha", "Nombre", "Marca", "Categoría", "Tipo", "Descuento", "Volumen", "Precio Final", "Precio/Unidad", "Alcohol")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")
        
        self.tree.heading("ID", text="ID BD")
        self.tree.column("ID", width=55, anchor="center")
        self.tree.heading("Fuente", text="Fuente")
        self.tree.column("Fuente", width=85, anchor="center")
        self.tree.heading("Fecha", text="Fecha")
        self.tree.column("Fecha", width=85, anchor="center")
        self.tree.heading("Nombre", text="Nombre")
        self.tree.column("Nombre", width=280)
        self.tree.heading("Marca", text="Marca")
        self.tree.column("Marca", width=110)
        self.tree.heading("Categoría", text="Categoría")
        self.tree.column("Categoría", width=110)
        self.tree.heading("Tipo", text="Tipo")
        self.tree.column("Tipo", width=80, anchor="center")
        self.tree.heading("Descuento", text="Descuento")
        self.tree.column("Descuento", width=85, anchor="center")
        self.tree.heading("Volumen", text="Volumen")
        self.tree.column("Volumen", width=95, anchor="center")
        self.tree.heading("Precio Final", text="Precio Final")
        self.tree.column("Precio Final", width=95, anchor="e")
        self.tree.heading("Precio/Unidad", text="Precio/Unidad")
        self.tree.column("Precio/Unidad", width=110, anchor="center")
        self.tree.heading("Alcohol", text="Alcohol")
        self.tree.column("Alcohol", width=65, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

    def open_date_modal(self):
        dates = database.get_available_dates()
        DateRangeModal(self, dates, self.on_date_range_applied, self.fecha_inicio, self.fecha_fin)

    def on_date_range_applied(self, start, end):
        self.fecha_inicio = start
        self.fecha_fin = end
        if start and end:
            self.lbl_range_info.configure(text=f"{start} a {end}")
        else:
            self.lbl_range_info.configure(text="Todas las fechas")
        self.update_data()

    def load_filters(self):
        sources = ["Todas"] + database.get_available_sources()
        categories = database.get_available_categories()
        self.fuente_combo.configure(values=sources)
        self.cat_combo.configure(values=categories)
        self.update_data()

    def update_data(self, *args):
        fuente = self.fuente_var.get()
        tipo = self.tipo_var.get()
        cat = self.cat_var.get()
        search_term = self.search_entry.get()
        solo_desc = self.descuento_var.get()

        pmin = float(self.pmin_entry.get()) if self.pmin_entry.get().strip().isdigit() else None
        pmax = float(self.pmax_entry.get()) if self.pmax_entry.get().strip().isdigit() else None
        
        df = database.get_data_as_dataframe(
            fuente=fuente, 
            tipo=tipo, 
            categoria=cat,
            fecha_inicio=self.fecha_inicio, 
            fecha_fin=self.fecha_fin, 
            search_term=search_term,
            solo_descuento=solo_desc,
            precio_min=pmin,
            precio_max=pmax
        )
        self.df_current = df
        
        for item in self.tree.get_children():
            self.tree.delete(item)

        if df.empty:
            return

        for _, r in df.head(1000).iterrows():
            precio_val = r['precio_final']
            precio_str = f"${precio_val:,.0f}" if pd.notnull(precio_val) and precio_val > 0 else "No Disponible"
            desc_val = r.get('descuento', '0%') or '0%'
            medida_val = r.get('medida', 'N/A') or 'N/A'
            pum_val = r.get('precio_unidad', 'N/A') or 'N/A'
            
            self.tree.insert("", "end", values=(
                r['id'], r['fuente'], str(r.get('fecha_extraccion', '')), r['nombre'], r['marca'], r['categoria'], 
                r['tipo_producto'], desc_val, medida_val, precio_str, pum_val, r['grados_alcohol']
            ))

    def export_data(self):
        if hasattr(self, 'df_current'):
            export_dataframe_dialog(self.df_current, default_filename="datos_crudos")

    def soft_delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Selecciona al menos un registro.")
            return

        count = 0
        for s in selected:
            item = self.tree.item(s)
            db_id = item["values"][0]
            database.delete_false_positive(db_id)
            self.tree.delete(s)
            count += 1
            
        messagebox.showinfo("Éxito", f"Se eliminaron {count} registros.")
