import customtkinter as ctk
from tkinter import ttk
import pandas as pd
import database
from ui.components.modals import DateRangeModal, export_dataframe_dialog

class NormalizedViewerFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="Visor de Datos Normalizados (MDM)", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.current_page = 0
        self.page_size = 200
        self.total_count = 0
        self.fecha_inicio = None
        self.fecha_fin = None

        self.filters_container = ctk.CTkFrame(self, fg_color=("#e2e8f0", "#1f2937"), corner_radius=8)
        self.filters_container.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        row1 = ctk.CTkFrame(self.filters_container, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(row1, text="Comercio:").pack(side="left", padx=2)
        self.fuente_var = ctk.StringVar(value="Todas")
        self.fuente_combo = ctk.CTkComboBox(row1, variable=self.fuente_var, command=self.on_filter_changed, width=110)
        self.fuente_combo.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Tipo:").pack(side="left", padx=(8, 2))
        self.tipo_var = ctk.StringVar(value="Todos")
        self.tipo_combo = ctk.CTkComboBox(row1, variable=self.tipo_var, values=["Todos", "Alcohol", "Tabaco"], command=self.on_filter_changed, width=95)
        self.tipo_combo.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Subcategoría:").pack(side="left", padx=(8, 2))
        self.subcat_var = ctk.StringVar(value="Todas")
        self.subcat_combo = ctk.CTkComboBox(row1, variable=self.subcat_var, command=self.on_filter_changed, width=130)
        self.subcat_combo.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Estado INVIMA:").pack(side="left", padx=(8, 2))
        self.invima_status_var = ctk.StringVar(value="Todos")
        self.invima_status_combo = ctk.CTkComboBox(row1, variable=self.invima_status_var, values=["Todos", "Ligados", "Sin Registro", "Tabaco", "No Aplica"], command=self.on_filter_changed, width=120)
        self.invima_status_combo.pack(side="left", padx=4)

        self.btn_range = ctk.CTkButton(row1, text="Rango Fechas", fg_color=("#cbd5e1", "#374151"), hover_color=("#94a3b8", "#4b5563"), text_color=("#0f172a", "#f9fafb"), width=100, command=self.open_date_modal)
        self.btn_range.pack(side="left", padx=8)

        self.lbl_range_info = ctk.CTkLabel(row1, text="Todas las fechas", text_color=("#64748b", "#9ca3af"), font=ctk.CTkFont(size=11, slant="italic"))
        self.lbl_range_info.pack(side="left", padx=2)

        row2 = ctk.CTkFrame(self.filters_container, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(row2, text="Buscar:").pack(side="left", padx=2)
        self.search_entry = ctk.CTkEntry(row2, placeholder_text="Código, INVIMA, Nombre o Marca...", width=240)
        self.search_entry.pack(side="left", padx=4)
        self.search_entry.bind("<Return>", lambda e: self.on_filter_changed())

        ctk.CTkLabel(row2, text="Precio $ Min:").pack(side="left", padx=(8, 2))
        self.pmin_entry = ctk.CTkEntry(row2, placeholder_text="0", width=75)
        self.pmin_entry.pack(side="left", padx=2)

        ctk.CTkLabel(row2, text="Max:").pack(side="left", padx=(4, 2))
        self.pmax_entry = ctk.CTkEntry(row2, placeholder_text="Max", width=75)
        self.pmax_entry.pack(side="left", padx=2)

        self.descuento_var = ctk.BooleanVar(value=False)
        self.chk_descuento = ctk.CTkCheckBox(row2, text="Solo Ofertas", variable=self.descuento_var, command=self.on_filter_changed)
        self.chk_descuento.pack(side="left", padx=12)

        self.btn_search = ctk.CTkButton(row2, text="Aplicar Filtros", fg_color="#2563eb", hover_color="#1d4ed8", command=self.on_filter_changed)
        self.btn_search.pack(side="left", padx=4)

        self.btn_export = ctk.CTkButton(row2, text="Exportar (Excel/JSON/CSV)", fg_color="#10b981", hover_color="#059669", command=self.export_data)
        self.btn_export.pack(side="right", padx=5)

        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=2, column=0, padx=20, pady=(0, 5), sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        columns = ("Código", "Fuente", "Fecha", "Nombre Estándar", "Marca", "Categoría", "Descuento", "Vol. Cantidad", "Unidad Medida", "Precio Final", "Precio/Unidad", "Registro INVIMA")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")
        
        self.tree.heading("Código", text="Código")
        self.tree.column("Código", width=95, anchor="center")
        self.tree.heading("Fuente", text="Fuente")
        self.tree.column("Fuente", width=80, anchor="center")
        self.tree.heading("Fecha", text="Fecha")
        self.tree.column("Fecha", width=80, anchor="center")
        self.tree.heading("Nombre Estándar", text="Nombre Estándar")
        self.tree.column("Nombre Estándar", width=230)
        self.tree.heading("Marca", text="Marca")
        self.tree.column("Marca", width=100)
        self.tree.heading("Categoría", text="Categoría")
        self.tree.column("Categoría", width=100)
        self.tree.heading("Descuento", text="Desc.")
        self.tree.column("Descuento", width=70, anchor="center")
        self.tree.heading("Vol. Cantidad", text="Vol. Cantidad")
        self.tree.column("Vol. Cantidad", width=90, anchor="e")
        self.tree.heading("Unidad Medida", text="Unidad")
        self.tree.column("Unidad Medida", width=85, anchor="center")
        self.tree.heading("Precio Final", text="Precio Final")
        self.tree.column("Precio Final", width=90, anchor="e")
        self.tree.heading("Precio/Unidad", text="Precio/Unidad")
        self.tree.column("Precio/Unidad", width=105, anchor="center")
        self.tree.heading("Registro INVIMA", text="Registro INVIMA")
        self.tree.column("Registro INVIMA", width=145, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.pagination_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pagination_frame.grid(row=3, column=0, padx=20, pady=(5, 15), sticky="ew")

        self.btn_prev = ctk.CTkButton(self.pagination_frame, text="◀ Anterior", width=90, command=self.prev_page)
        self.btn_prev.pack(side="left", padx=5)

        self.lbl_page_info = ctk.CTkLabel(self.pagination_frame, text="Página 1 de 1", font=ctk.CTkFont(weight="bold"))
        self.lbl_page_info.pack(side="left", padx=15)

        self.btn_next = ctk.CTkButton(self.pagination_frame, text="Siguiente ▶", width=90, command=self.next_page)
        self.btn_next.pack(side="left", padx=5)

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
        self.on_filter_changed()

    def load_filters(self):
        sources = ["Todas"] + database.get_available_sources()
        subcats = database.get_available_subcategories()
        self.fuente_combo.configure(values=sources)
        self.subcat_combo.configure(values=subcats)
        self.on_filter_changed()

    def on_filter_changed(self, *args):
        self.current_page = 0
        self.update_data()

    def update_data(self):
        fuente = self.fuente_var.get()
        tipo = self.tipo_var.get()
        subcat = self.subcat_var.get()
        inv_status = self.invima_status_var.get()
        search_term = self.search_entry.get()
        solo_desc = self.descuento_var.get()

        pmin = float(self.pmin_entry.get()) if self.pmin_entry.get().strip().isdigit() else None
        pmax = float(self.pmax_entry.get()) if self.pmax_entry.get().strip().isdigit() else None
        
        offset = self.current_page * self.page_size
        df, total_count = database.get_normalized_data_paginated(
            fuente=fuente,
            tipo=tipo,
            subcategoria=subcat,
            estado_invima=inv_status,
            fecha_inicio=self.fecha_inicio,
            fecha_fin=self.fecha_fin,
            search_term=search_term,
            solo_descuento=solo_desc,
            precio_min=pmin,
            precio_max=pmax,
            limit=self.page_size,
            offset=offset
        )
        self.total_count = total_count
        
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if not df.empty:
            for _, row in df.iterrows():
                pf = row.get('precio_final')
                pf_str = f"${pf:,.0f}" if pd.notnull(pf) and pf > 0 else "No Disponible"
                invima_val = row.get('registro_sanitario_invima', '') or 'SIN_REGISTRO_ENCONTRADO'
                desc_val = row.get('descuento', '0%') or '0%'
                
                vol_cant = row.get('volumen_cantidad')
                if pd.notnull(vol_cant) and vol_cant is not None:
                    vol_cant_str = f"{vol_cant:,.0f}" if float(vol_cant).is_integer() else f"{vol_cant:,.2f}"
                else:
                    vol_cant_str = "-"
                    
                vol_u_str = str(row.get('volumen_unidad_medida') or '') or "-"
                pum_val = str(row.get('precio_unidad') or '') or "-"

                self.tree.insert("", "end", values=(
                    row.get('id', ''),
                    row.get('fuente', ''),
                    str(row.get('fecha_extraccion', '')),
                    row.get('nombre', ''),
                    row.get('marca_estandar', ''),
                    row.get('subcategoria_estandar', ''),
                    desc_val,
                    vol_cant_str,
                    vol_u_str,
                    pf_str,
                    pum_val,
                    invima_val
                ))

        total_pages = max(1, (total_count + self.page_size - 1) // self.page_size)
        self.lbl_page_info.configure(text=f"Página {self.current_page + 1} de {total_pages} (Total: {total_count:,} registros)")
        self.btn_prev.configure(state="normal" if self.current_page > 0 else "disabled")
        self.btn_next.configure(state="normal" if (self.current_page + 1) < total_pages else "disabled")

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_data()

    def next_page(self):
        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        if (self.current_page + 1) < total_pages:
            self.current_page += 1
            self.update_data()

    def export_data(self):
        fuente = self.fuente_var.get()
        tipo = self.tipo_var.get()
        subcat = self.subcat_var.get()
        inv_status = self.invima_status_var.get()
        search_term = self.search_entry.get()
        solo_desc = self.descuento_var.get()

        pmin = float(self.pmin_entry.get()) if self.pmin_entry.get().strip().isdigit() else None
        pmax = float(self.pmax_entry.get()) if self.pmax_entry.get().strip().isdigit() else None

        df = database.get_normalized_data_as_dataframe(
            fuente=fuente,
            tipo=tipo,
            subcategoria=subcat,
            estado_invima=inv_status,
            fecha_inicio=self.fecha_inicio,
            fecha_fin=self.fecha_fin,
            search_term=search_term,
            solo_descuento=solo_desc,
            precio_min=pmin,
            precio_max=pmax,
            ignore_zero_prices=False
        )
        export_dataframe_dialog(df, default_filename="datos_normalizados_mdm")
