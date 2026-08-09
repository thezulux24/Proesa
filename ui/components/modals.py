import datetime
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import database

def export_dataframe_dialog(df, default_filename="export_data"):
    if df is None or df.empty:
        messagebox.showwarning("Vacío", "No hay datos para exportar con los filtros actuales.")
        return
        
    filepath = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[
            ("Archivos de Excel (*.xlsx)", "*.xlsx"),
            ("Archivos JSON (*.json)", "*.json"),
            ("Archivos CSV (*.csv)", "*.csv")
        ],
        initialfile=f"{default_filename}_{datetime.date.today()}"
    )
    
    if not filepath:
        return
        
    try:
        if filepath.lower().endswith('.json'):
            df.to_json(filepath, orient='records', force_ascii=False, indent=2)
        elif filepath.lower().endswith('.csv'):
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
        else:
            df.to_excel(filepath, index=False)
            
        messagebox.showinfo("Éxito", f"Datos exportados correctamente a:\n{filepath}")
    except Exception as e:
        messagebox.showerror("Error de Exportación", f"Fallo al exportar los datos: {e}")


class DateRangeModal(ctk.CTkToplevel):
    def __init__(self, master, available_dates, on_apply_callback, current_start=None, current_end=None):
        super().__init__(master)
        self.title("Seleccionar Rango de Fechas")
        self.geometry("450x300")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.grab_set()
        
        self.on_apply = on_apply_callback
        self.dates = available_dates if available_dates else [str(datetime.date.today())]
        
        ctk.CTkLabel(self, text="Filtro de Rango de Fechas", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 15))
        
        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(form_frame, text="Fecha Inicial:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.combo_start = ctk.CTkComboBox(form_frame, values=self.dates, width=200)
        if current_start and current_start in self.dates:
            self.combo_start.set(current_start)
        else:
            self.combo_start.set(self.dates[-1] if self.dates else "")
        self.combo_start.grid(row=0, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(form_frame, text="Fecha Final:", font=ctk.CTkFont(size=14)).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.combo_end = ctk.CTkComboBox(form_frame, values=self.dates, width=200)
        if current_end and current_end in self.dates:
            self.combo_end.set(current_end)
        else:
            self.combo_end.set(self.dates[0] if self.dates else "")
        self.combo_end.grid(row=1, column=1, padx=10, pady=10)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=20)
        
        ctk.CTkButton(btn_frame, text="Aplicar Rango", fg_color="#2563eb", hover_color="#1d4ed8", font=ctk.CTkFont(weight="bold"), command=self.apply).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Limpiar Rango", fg_color="#4b5563", hover_color="#374151", command=self.clear_range).pack(side="right", padx=5)

    def apply(self):
        start = self.combo_start.get().strip()
        end = self.combo_end.get().strip()
        if start > end:
            start, end = end, start
        self.on_apply(start, end)
        self.destroy()

    def clear_range(self):
        self.on_apply(None, None)
        self.destroy()


class AssignInvimaModal(ctk.CTkToplevel):
    def __init__(self, master, selected_items, on_save_callback):
        super().__init__(master)
        self.title("Asignar / Editar Registro Sanitario INVIMA")
        self.geometry("580x560")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.grab_set()

        self.selected_items = selected_items
        self.on_save = on_save_callback

        ctk.CTkLabel(self, text="Gestión de Registro Sanitario INVIMA", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))

        if len(self.selected_items) == 1:
            cod, nombre, marca, _, inv_curr, _ = self.selected_items[0]
            info_text = f"Código Maestro: {cod}\nProducto: {nombre}\nMarca: {marca}\nINVIMA Actual: {inv_curr}"
        else:
            info_text = f"Se actualizarán {len(self.selected_items)} productos maestros seleccionados simultáneamente."

        card_info = ctk.CTkFrame(self, fg_color=("#e2e8f0", "#1f2937"), corner_radius=8)
        card_info.pack(fill="x", padx=25, pady=10)
        ctk.CTkLabel(card_info, text=info_text, font=ctk.CTkFont(size=12), justify="left", wraplength=500).pack(padx=15, pady=12, anchor="w")

        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=25, pady=5)

        ctk.CTkLabel(input_frame, text="Nuevo Registro Sanitario INVIMA:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 3))
        self.entry_invima = ctk.CTkEntry(input_frame, placeholder_text="Ej: INVIMA 2018L-0009667 o RSA-0025928-2023", width=500)
        if len(self.selected_items) == 1 and self.selected_items[0][4] not in ['SIN_REGISTRO_ENCONTRADO', 'N/A - TABACO', 'NO_APLICA']:
            self.entry_invima.insert(0, str(self.selected_items[0][4]))
        self.entry_invima.pack(fill="x")
        self.entry_invima.bind("<KeyRelease>", self.on_invima_key_release)

        self.preview_frame = ctk.CTkFrame(self, fg_color=("#f1f5f9", "#111827"), corner_radius=8)
        self.preview_frame.pack(fill="both", expand=True, padx=25, pady=10)

        ctk.CTkLabel(self.preview_frame, text="Coincidencia en Catálogo Oficial Certificado:", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#475569", "#9ca3af")).pack(anchor="w", padx=12, pady=(10, 4))
        self.lbl_preview = ctk.CTkLabel(self.preview_frame, text="Escribe un código arriba para validar en el catálogo oficial...", font=ctk.CTkFont(size=11, slant="italic"), text_color="#6b7280", justify="left", wraplength=500)
        self.lbl_preview.pack(anchor="w", padx=12, pady=(0, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25, pady=15)

        ctk.CTkButton(btn_frame, text="Guardar Cambios", fg_color="#2563eb", hover_color="#1d4ed8", font=ctk.CTkFont(weight="bold"), command=self.save).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Marcar No Aplica (-1)", fg_color="#d97706", hover_color="#b45309", command=self.set_no_applies).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="#4b5563", hover_color="#374151", command=self.destroy).pack(side="left", padx=5)

    def on_invima_key_release(self, event):
        val = self.entry_invima.get().strip()
        if not val:
            self.lbl_preview.configure(text="Escribe un código arriba para validar en el catálogo oficial...", text_color="#6b7280")
            return
            
        db = database.DataSuiteDB()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT registro_sanitario, nombre_bebida_alcoholica, marca, clasificacion 
                FROM invima_certificados 
                WHERE UPPER(registro_sanitario) LIKE ? OR UPPER(registro_sanitario) LIKE ?
                LIMIT 1
            """, (f"%{val.upper()}%", f"%{val.upper().replace('INVIMA', '').strip()}%"))
            found = cur.fetchone()

        if found:
            txt = f"✓ ENCONTRADO EN CATÁLOGO:\nRegistro: {found[0]}\nProducto: {found[1]}\nMarca: {found[2]}\nClasificación: {found[3]}"
            self.lbl_preview.configure(text=txt, text_color="#10b981")
        else:
            txt = f"⚠ No se encontró coincidencia exacta en el catálogo oficial certificado.\nSe guardará como asignación personalizada o pendiente."
            self.lbl_preview.configure(text=txt, text_color="#d97706")

    def save(self):
        new_val = self.entry_invima.get().strip()
        if not new_val:
            messagebox.showwarning("Atención", "Ingresa un registro INVIMA o haz clic en 'Marcar No Aplica (-1)'.")
            return
        self.on_save(self.selected_items, new_val)
        self.destroy()

    def set_no_applies(self):
        self.on_save(self.selected_items, "NO_APLICA")
        self.destroy()


class CandidateMatchingModal(ctk.CTkToplevel):
    def __init__(self, master, target_raw, df_master, on_link_callback):
        """
        target_raw: dict or tuple (comercio, producto_id, nombre, marca, ultimo_precio)
        df_master: DataFrame of maestro_productos with ultimo_precio column
        on_link_callback: callback function(comercio, producto_id, codigo_universal)
        """
        super().__init__(master)
        self.title("Asistente de Vinculación y Matching MDM (Top Candidatos)")
        self.geometry("1020x680")
        self.resizable(True, True)
        self.transient(master.winfo_toplevel())
        self.grab_set()

        if isinstance(target_raw, dict):
            self.comercio = target_raw.get('comercio', '')
            self.prod_id = str(target_raw.get('producto_id', ''))
            self.nombre_crudo = target_raw.get('nombre', '')
            self.marca_cruda = target_raw.get('marca', '')
            self.precio_crudo = target_raw.get('ultimo_precio', 0)
            self.url_producto = target_raw.get('url_producto', '')
        else:
            self.comercio = target_raw[0]
            self.prod_id = str(target_raw[1])
            self.nombre_crudo = target_raw[2]
            self.marca_cruda = target_raw[3] if len(target_raw) > 3 else ''
            self.precio_crudo = target_raw[4] if len(target_raw) > 4 else 0
            self.url_producto = target_raw[5] if len(target_raw) > 5 else ''

        self.df_master = df_master.copy() if df_master is not None else pd.DataFrame()
        self.on_link = on_link_callback

        self._setup_ui()
        self.calculate_and_load_candidates()

    def _setup_ui(self):
        # Header / Target info card
        card_info = ctk.CTkFrame(self, fg_color=("#1e293b", "#0f172a"), corner_radius=10)
        card_info.pack(fill="x", padx=20, pady=(15, 10))

        lbl_header = ctk.CTkLabel(
            card_info, 
            text="PRODUCTO CRUDO A VINCULAR", 
            font=ctk.CTkFont(size=11, weight="bold"), 
            text_color="#94a3b8"
        )
        lbl_header.pack(anchor="w", padx=16, pady=(10, 2))

        lbl_nombre = ctk.CTkLabel(
            card_info, 
            text=f"{self.nombre_crudo}", 
            font=ctk.CTkFont(size=16, weight="bold"), 
            text_color="#f8fafc",
            anchor="w",
            justify="left",
            wraplength=950
        )
        lbl_nombre.pack(anchor="w", padx=16, pady=(0, 6))

        info_meta_frame = ctk.CTkFrame(card_info, fg_color="transparent")
        info_meta_frame.pack(fill="x", padx=16, pady=(0, 10))

        meta_txt = f"Comercio: {self.comercio}   |   ID: {self.prod_id}   |   Marca: {self.marca_cruda or 'N/A'}"
        ctk.CTkLabel(info_meta_frame, text=meta_txt, font=ctk.CTkFont(size=12), text_color="#cbd5e1").pack(side="left")

        # Botón para abrir URL en navegador
        ctk.CTkButton(
            info_meta_frame,
            text="🔗 Ver Enlace en Tienda",
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(weight="bold", size=12),
            width=160,
            command=self.open_product_url
        ).pack(side="right", padx=(10, 0))

        precio_fmt = self._format_currency(self.precio_crudo)
        lbl_price_badge = ctk.CTkLabel(
            info_meta_frame,
            text=f" Último Precio Crudo: {precio_fmt} ",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#10b981",
            fg_color="#064e3b",
            corner_radius=6
        )
        lbl_price_badge.pack(side="right")

        # Search Bar & Instructions
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            search_frame, 
            text="🔍 Buscar candidato manualmente si no está en el Top 15:", 
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=(0, 10))

        self.search_entry = ctk.CTkEntry(
            search_frame, 
            placeholder_text="Escribe nombre, marca o código maestro para filtrar en vivo...",
            width=400
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.search_entry.bind("<KeyRelease>", self.on_search_key_release)

        ctk.CTkButton(
            search_frame, 
            text="Limpiar Búsqueda", 
            width=120,
            fg_color="#4b5563", 
            hover_color="#374151", 
            command=self.clear_search
        ).pack(side="right", padx=(5, 0))

        # Candidates Table Frame
        tree_frame = ctk.CTkFrame(self, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=20, pady=5)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columns = ("Similitud", "Código", "Nombre Estándar MDM", "Marca", "Último Precio MDM")
        self.tree_candidates = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        
        self.tree_candidates.heading("Similitud", text="Coincidencia")
        self.tree_candidates.heading("Código", text="Código Master")
        self.tree_candidates.heading("Nombre Estándar MDM", text="Nombre Estándar MDM")
        self.tree_candidates.heading("Marca", text="Marca Estándar")
        self.tree_candidates.heading("Último Precio MDM", text="Último Precio MDM")

        self.tree_candidates.column("Similitud", width=100, anchor="center")
        self.tree_candidates.column("Código", width=120, anchor="center")
        self.tree_candidates.column("Nombre Estándar MDM", width=460, anchor="w")
        self.tree_candidates.column("Marca", width=140, anchor="w")
        self.tree_candidates.column("Último Precio MDM", width=140, anchor="e")

        self.tree_candidates.grid(row=0, column=0, sticky="nsew")
        self.tree_candidates.bind("<Double-1>", lambda e: self.confirm_link())

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_candidates.yview)
        self.tree_candidates.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Bottom Action Bar
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(5, 15))

        self.lbl_status = ctk.CTkLabel(
            btn_frame, 
            text="Selecciona un candidato maestro y presiona Vincular o haz doble clic.", 
            font=ctk.CTkFont(size=12, slant="italic"), 
            text_color="#64748b"
        )
        self.lbl_status.pack(side="left")

        ctk.CTkButton(
            btn_frame, 
            text="🚫 Descartar (Falso Positivo)", 
            fg_color="#dc2626", 
            hover_color="#b91c1c", 
            font=ctk.CTkFont(weight="bold", size=13), 
            command=self.mark_as_false_positive
        ).pack(side="left", padx=(10, 5))

        ctk.CTkButton(
            btn_frame, 
            text="Vincular Candidato Seleccionado", 
            fg_color="#2563eb", 
            hover_color="#1d4ed8", 
            font=ctk.CTkFont(weight="bold", size=13), 
            command=self.confirm_link
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame, 
            text="✨ Crear Nuevo Maestro", 
            fg_color="#059669", 
            hover_color="#047857", 
            font=ctk.CTkFont(weight="bold", size=13), 
            command=self.open_create_master_dialog
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame, 
            text="🔗 Ver Enlace Candidato", 
            fg_color="#0284c7", 
            hover_color="#0369a1", 
            font=ctk.CTkFont(weight="bold", size=13), 
            command=self.open_selected_candidate_url
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame, 
            text="Cancelar", 
            fg_color="#4b5563", 
            hover_color="#374151", 
            command=self.destroy
        ).pack(side="right", padx=5)

    def open_product_url(self):
        import webbrowser
        url = str(self.url_producto).strip() if self.url_producto else ""
        if url and url.startswith("http"):
            webbrowser.open(url)
        else:
            messagebox.showwarning("Sin URL", "Este producto no tiene un enlace web válido grabado de la tienda.")

    def open_selected_candidate_url(self):
        import webbrowser
        selected = self.tree_candidates.selection()
        if not selected:
            messagebox.showwarning("Atención", "Por favor selecciona un candidato maestro de la lista.")
            return

        values = self.tree_candidates.item(selected[0])['values']
        code = str(values[1])
        url = self.candidate_urls.get(code, '')
        if url and url.startswith("http"):
            webbrowser.open(url)
        else:
            messagebox.showwarning("Sin URL", f"El candidato maestro {code} no tiene un enlace web registrado.")

    def _format_currency(self, val):
        try:
            if val is None or pd.isna(val) or float(val) <= 0:
                return "$ 0 / Sin precio"
            return f"$ {float(val):,.0f}".replace(",", ".")
        except Exception:
            return "$ 0 / Sin precio"

    def _clean_text(self, text):
        import re
        if not text: return ''
        text = str(text).upper()
        text = re.sub(r'[^A-Z0-9\s]', ' ', text)
        return ' '.join(text.split())

    def _compute_similarity(self, raw_name, raw_brand, master_name, master_brand):
        from difflib import SequenceMatcher
        n1 = self._clean_text(raw_name)
        n2 = self._clean_text(master_name)
        if not n1 or not n2: return 0.0

        seq_ratio = SequenceMatcher(None, n1, n2).ratio()
        tokens1 = set(n1.split())
        tokens2 = set(n2.split())
        jaccard = len(tokens1 & tokens2) / len(tokens1 | tokens2) if (tokens1 and tokens2) else 0.0

        score = 0.5 * seq_ratio + 0.5 * jaccard

        b1 = self._clean_text(raw_brand)
        b2 = self._clean_text(master_brand)
        if b1 and b2 and (b1 in b2 or b2 in b1 or b1 in n2):
            score += 0.10

        return min(score, 1.0)

    def calculate_and_load_candidates(self, filter_text=""):
        for item in self.tree_candidates.get_children():
            self.tree_candidates.delete(item)

        self.candidate_urls = {}

        if self.df_master.empty:
            self.lbl_status.configure(text="No hay productos en el maestro de productos.", text_color="#ef4444")
            return

        filter_clean = self._clean_text(filter_text)
        scored_items = []

        for _, r in self.df_master.iterrows():
            code = str(r.get('codigo_universal', ''))
            name = str(r.get('nombre_estandar', ''))
            brand = str(r.get('marca_estandar', ''))
            price = r.get('ultimo_precio', 0)
            url_candidate = str(r.get('url_producto', '')).strip()

            # Calculate match score
            score = self._compute_similarity(self.nombre_crudo, self.marca_cruda, name, brand)

            if filter_clean:
                code_clean = self._clean_text(code)
                name_clean = self._clean_text(name)
                brand_clean = self._clean_text(brand)
                if filter_clean in code_clean or filter_clean in name_clean or filter_clean in brand_clean:
                    scored_items.append((score, code, name, brand, price, url_candidate))
            else:
                scored_items.append((score, code, name, brand, price, url_candidate))

        # Sort by score descending
        scored_items.sort(key=lambda x: x[0], reverse=True)

        limit = 30 if filter_clean else 15
        top_candidates = scored_items[:limit]

        for score, code, name, brand, price, url_candidate in top_candidates:
            pct_str = f"{score * 100:.1f}%"
            price_str = self._format_currency(price)
            self.candidate_urls[code] = url_candidate
            self.tree_candidates.insert("", "end", values=(pct_str, code, name, brand, price_str))

        if top_candidates:
            first_item = self.tree_candidates.get_children()[0]
            self.tree_candidates.selection_set(first_item)
            self.tree_candidates.focus(first_item)
            if filter_text:
                self.lbl_status.configure(
                    text=f"Mostrando {len(top_candidates)} resultados para '{filter_text}'.", 
                    text_color="#10b981"
                )
            else:
                top_score = top_candidates[0][0] * 100
                self.lbl_status.configure(
                    text=f"Top 15 candidatos cargados (Mejor coincidencia: {top_score:.1f}%).", 
                    text_color="#10b981"
                )
        else:
            self.lbl_status.configure(
                text=f"No se encontraron candidatos que coincidan con '{filter_text}'.", 
                text_color="#d97706"
            )

    def on_search_key_release(self, event):
        txt = self.search_entry.get().strip()
        self.calculate_and_load_candidates(filter_text=txt)

    def clear_search(self):
        self.search_entry.delete(0, 'end')
        self.calculate_and_load_candidates(filter_text="")

    def confirm_link(self):
        selected = self.tree_candidates.selection()
        if not selected:
            messagebox.showwarning("Atención", "Por favor selecciona un candidato maestro de la lista.")
            return

        values = self.tree_candidates.item(selected[0])['values']
        codigo_universal = values[1]
        nombre_master = values[2]

        if messagebox.askyesno("Confirmar Vinculación", f"¿Vincular el producto crudo '{self.nombre_crudo}'\nal maestro '{codigo_universal}' - {nombre_master}?"):
            self.on_link(self.comercio, self.prod_id, codigo_universal)
            self.destroy()

    def open_create_master_dialog(self):
        target_raw = {
            'comercio': self.comercio,
            'producto_id': self.prod_id,
            'nombre': self.nombre_crudo,
            'marca': self.marca_cruda,
            'ultimo_precio': self.precio_crudo,
            'url_producto': self.url_producto
        }
        
        def on_master_created(created_code, raw_data):
            self.on_link(self.comercio, self.prod_id, created_code)
            self.destroy()

        CreateMasterModal(self, target_raw=target_raw, on_create_callback=on_master_created)

    def mark_as_false_positive(self):
        if messagebox.askyesno("Confirmar Falso Positivo", f"¿Marcar el producto '{self.nombre_crudo}' [{self.comercio} - ID {self.prod_id}] como Falso Positivo?\nSe ocultará de la lista y no se incluirá en los análisis."):
            database.mark_raw_false_positive(self.comercio, self.prod_id)
            messagebox.showinfo("Descartado", f"El producto {self.comercio} [{self.prod_id}] fue marcado como falso positivo.")
            self.destroy()
            if self.on_link:
                self.on_link(self.comercio, self.prod_id, None)


class CreateMasterModal(ctk.CTkToplevel):
    def __init__(self, master, target_raw=None, on_create_callback=None):
        """
        target_raw: dict with keys ('comercio', 'producto_id', 'nombre', 'marca', 'tipo_producto', etc.) or None
        on_create_callback: callback function(codigo_universal, target_raw)
        """
        super().__init__(master)
        self.title("Crear Nuevo Producto Maestro (MDM)")
        self.geometry("560x650")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.grab_set()

        self.target_raw = target_raw
        self.on_create = on_create_callback

        self._setup_ui()

    def _setup_ui(self):
        # Header
        ctk.CTkLabel(
            self, 
            text="✨ Crear Nuevo Producto Maestro MDM", 
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(18, 5))

        if self.target_raw:
            nombre_raw = self.target_raw.get('nombre', '')
            comercio = self.target_raw.get('comercio', '')
            prod_id = self.target_raw.get('producto_id', '')
            info_txt = f"Se creará el maestro y se vinculará a: [{comercio} - ID {prod_id}] {nombre_raw}"
            card_info = ctk.CTkFrame(self, fg_color=("#e2e8f0", "#1f2937"), corner_radius=8)
            card_info.pack(fill="x", padx=25, pady=(5, 10))
            ctk.CTkLabel(
                card_info, 
                text=info_txt, 
                font=ctk.CTkFont(size=11, weight="bold"), 
                text_color="#3b82f6", 
                wraplength=490, 
                justify="left"
            ).pack(padx=12, pady=8, anchor="w")

        # Form Frame
        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=25, pady=5)
        form_frame.grid_columnconfigure(1, weight=1)

        # 1. Código Universal
        row = 0
        ctk.CTkLabel(form_frame, text="Código Universal:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 10))
        self.entry_code = ctk.CTkEntry(form_frame, placeholder_text="Ej: MST_102030")
        auto_code = database.generate_new_master_code()
        self.entry_code.insert(0, auto_code)
        self.entry_code.grid(row=row, column=1, sticky="ew", pady=6)

        # 2. Nombre Estándar MDM
        row += 1
        ctk.CTkLabel(form_frame, text="Nombre Estándar MDM *:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 10))
        self.entry_nombre = ctk.CTkEntry(form_frame, placeholder_text="Ej: Aguardiente BENDITO sin azúcar (750 ml)")
        if self.target_raw and self.target_raw.get('nombre'):
            self.entry_nombre.insert(0, str(self.target_raw.get('nombre')))
        self.entry_nombre.grid(row=row, column=1, sticky="ew", pady=6)

        # 3. Marca Estándar
        row += 1
        ctk.CTkLabel(form_frame, text="Marca Estándar *:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 10))
        self.entry_marca = ctk.CTkEntry(form_frame, placeholder_text="Ej: BENDITO")
        if self.target_raw and self.target_raw.get('marca'):
            self.entry_marca.insert(0, str(self.target_raw.get('marca')))
        self.entry_marca.grid(row=row, column=1, sticky="ew", pady=6)

        # 4. Tipo de Producto
        row += 1
        ctk.CTkLabel(form_frame, text="Tipo de Producto *:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 10))
        self.combo_tipo = ctk.CTkComboBox(form_frame, values=["Alcohol", "Tabaco"])
        default_tipo = "Alcohol"
        if self.target_raw and self.target_raw.get('tipo_producto'):
            raw_tipo = str(self.target_raw.get('tipo_producto')).capitalize()
            if raw_tipo in ["Alcohol", "Tabaco"]:
                default_tipo = raw_tipo
        self.combo_tipo.set(default_tipo)
        self.combo_tipo.grid(row=row, column=1, sticky="ew", pady=6)

        # 5. Subcategoría Estándar
        row += 1
        ctk.CTkLabel(form_frame, text="Subcategoría Estándar:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 10))
        subcats = database.get_available_subcategories()
        if not subcats:
            subcats = ["Aguardiente", "Cerveza", "Ron", "Whisky", "Vino", "Vodka", "Tequila", "Cigarrillos"]
        self.combo_subcat = ctk.CTkComboBox(form_frame, values=subcats)
        self.combo_subcat.set(subcats[0] if subcats else "")
        self.combo_subcat.grid(row=row, column=1, sticky="ew", pady=6)

        # 6. Volumen Estándar
        row += 1
        ctk.CTkLabel(form_frame, text="Volumen Estándar:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 10))
        self.entry_volumen = ctk.CTkEntry(form_frame, placeholder_text="Ej: 750 ml")
        if self.target_raw and self.target_raw.get('medida'):
            self.entry_volumen.insert(0, str(self.target_raw.get('medida')))
        self.entry_volumen.grid(row=row, column=1, sticky="ew", pady=6)

        # 7. Grados de Alcohol
        row += 1
        ctk.CTkLabel(form_frame, text="Grados de Alcohol:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 10))
        self.entry_grados = ctk.CTkEntry(form_frame, placeholder_text="Ej: 29%")
        if self.target_raw and self.target_raw.get('grados_alcohol'):
            self.entry_grados.insert(0, str(self.target_raw.get('grados_alcohol')))
        self.entry_grados.grid(row=row, column=1, sticky="ew", pady=6)

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25, pady=(15, 20))

        if self.target_raw:
            ctk.CTkButton(
                btn_frame, 
                text="🚫 Descartar (Falso Positivo)", 
                fg_color="#dc2626", 
                hover_color="#b91c1c", 
                font=ctk.CTkFont(weight="bold", size=13), 
                command=self.discard_as_false_positive
            ).pack(side="left", padx=5)

        btn_save_text = "✨ Guardar y Vincular Maestro" if self.target_raw else "✨ Guardar Nuevo Maestro"
        ctk.CTkButton(
            btn_frame, 
            text=btn_save_text, 
            fg_color="#059669", 
            hover_color="#047857", 
            font=ctk.CTkFont(weight="bold", size=13), 
            command=self.save
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame, 
            text="Cancelar", 
            fg_color="#4b5563", 
            hover_color="#374151", 
            command=self.destroy
        ).pack(side="right", padx=5)

    def save(self):
        codigo = self.entry_code.get().strip()
        nombre = self.entry_nombre.get().strip()
        marca = self.entry_marca.get().strip()
        tipo = self.combo_tipo.get().strip()
        subcat = self.combo_subcat.get().strip()
        volumen = self.entry_volumen.get().strip()
        grados = self.entry_grados.get().strip()

        if not nombre:
            messagebox.showwarning("Campo Requerido", "El campo 'Nombre Estándar MDM' es obligatorio.")
            return

        if not marca:
            messagebox.showwarning("Campo Requerido", "El campo 'Marca Estándar' es obligatorio.")
            return

        try:
            created_code = database.add_to_maestro(
                nombre=nombre,
                marca=marca,
                tipo=tipo,
                subcategoria=subcat,
                volumen=volumen,
                grados=grados,
                codigo_universal=codigo
            )

            if self.target_raw:
                comercio = self.target_raw.get('comercio')
                prod_id = str(self.target_raw.get('producto_id'))
                if comercio and prod_id:
                    database.add_mapping(comercio, prod_id, created_code)

            if self.on_create:
                self.on_create(created_code, self.target_raw)

            messagebox.showinfo("Éxito", f"Producto Maestro '{created_code}' creado correctamente.")
            self.destroy()
        except ValueError as ve:
            messagebox.showerror("Código Duplicado", str(ve))
        except Exception as e:
            messagebox.showerror("Error al Crear Maestro", f"Ocurrió un error al guardar el producto maestro:\n{e}")

    def discard_as_false_positive(self):
        if not self.target_raw:
            return
        comercio = self.target_raw.get('comercio')
        prod_id = str(self.target_raw.get('producto_id'))
        nombre = self.target_raw.get('nombre', '')
        if messagebox.askyesno("Confirmar Falso Positivo", f"¿Descartar '{nombre}' [{comercio} - ID {prod_id}] como falso positivo?\nSe ocultará permanentemente de las listas no mapeadas."):
            database.mark_raw_false_positive(comercio, prod_id)
            messagebox.showinfo("Descartado", "El producto crudo ha sido marcado como Falso Positivo.")
            self.destroy()
            if self.on_create:
                self.on_create(None, self.target_raw)


