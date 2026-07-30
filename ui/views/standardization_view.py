import os
import json
import time
import threading
import customtkinter as ctk
from tkinter import ttk, messagebox
import pandas as pd
import database
from ui.components.modals import AssignInvimaModal, export_dataframe_dialog

class UnifiedStandardizationFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="Flujo Único de Estandarización de Datos (MDM & INVIMA)", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Tabview con los 4 pasos de estandarización e INVIMA
        self.tabview = ctk.CTkTabview(self, fg_color=("#e2e8f0", "#1f2937"))
        self.tabview.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")

        self.tab_mapeo = self.tabview.add("1. Mapeo y Vinculación MDM")
        self.tab_ia = self.tabview.add("2. Depuración IA (Falsos Positivos)")
        self.tab_invima = self.tabview.add("3. Homologación INVIMA")
        self.tab_catalogo = self.tabview.add("4. Catálogo Nacional INVIMA")

        self.cat_current_page = 0
        self.cat_page_size = 200
        self.cat_total_count = 0

        self._setup_mapeo_tab()
        self._setup_ia_tab()
        self._setup_invima_tab()
        self._setup_catalogo_tab()

    def load_filters(self):
        sources = ["Todas"] + database.get_available_sources()
        subcats = database.get_available_subcategories()
        
        self.map_fuente_combo.configure(values=sources)
        self.inv_subcat_combo.configure(values=subcats)
        
        self.load_mapeo_data()
        self.load_invima_data()
        self.load_catalogo_data()

    # -------------------------------------------------------------
    # PASO 1: Mapeo y Vinculación MDM
    # -------------------------------------------------------------
    def _setup_mapeo_tab(self):
        self.tab_mapeo.grid_rowconfigure(0, weight=0)
        self.tab_mapeo.grid_rowconfigure(1, weight=1)
        self.tab_mapeo.grid_rowconfigure(2, weight=0)
        self.tab_mapeo.grid_columnconfigure((0, 1), weight=1)

        controls = ctk.CTkFrame(self.tab_mapeo, fg_color="transparent")
        controls.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(controls, text="Comercio:").pack(side="left", padx=2)
        self.map_fuente_var = ctk.StringVar(value="Todas")
        self.map_fuente_combo = ctk.CTkComboBox(controls, variable=self.map_fuente_var, command=self.load_mapeo_data, width=110)
        self.map_fuente_combo.pack(side="left", padx=4)

        ctk.CTkLabel(controls, text="Tipo:").pack(side="left", padx=(8, 2))
        self.map_tipo_var = ctk.StringVar(value="Todos")
        self.map_tipo_combo = ctk.CTkComboBox(controls, variable=self.map_tipo_var, values=["Todos", "Alcohol", "Tabaco"], command=self.load_mapeo_data, width=100)
        self.map_tipo_combo.pack(side="left", padx=4)

        ctk.CTkLabel(controls, text="Buscar Crudos:").pack(side="left", padx=(8, 2))
        self.map_search_entry = ctk.CTkEntry(controls, placeholder_text="Nombre o marca...", width=200)
        self.map_search_entry.pack(side="left", padx=4)
        self.map_search_entry.bind("<Return>", lambda e: self.load_mapeo_data())

        ctk.CTkButton(controls, text="Buscar / Refrescar", command=self.load_mapeo_data).pack(side="left", padx=4)
        ctk.CTkButton(controls, text="Exportar Sin Mapear", fg_color="#10b981", hover_color="#059669", command=self.export_mapeo_data).pack(side="right", padx=4)
        ctk.CTkButton(controls, text="Ejecutar ETL", fg_color="#2563eb", hover_color="#1d4ed8", font=ctk.CTkFont(weight="bold"), command=self.run_etl).pack(side="right", padx=4)

        left_frame = ctk.CTkFrame(self.tab_mapeo)
        left_frame.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="nsew")
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left_frame, text="Productos Sin Mapear (Crudos)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=5)
        self.tree_raw = ttk.Treeview(left_frame, columns=("Comercio", "ID", "Nombre", "Marca"), show="headings")
        self.tree_raw.heading("Comercio", text="Comercio")
        self.tree_raw.heading("ID", text="ID")
        self.tree_raw.heading("Nombre", text="Nombre")
        self.tree_raw.heading("Marca", text="Marca")
        self.tree_raw.column("Comercio", width=80)
        self.tree_raw.column("ID", width=80)
        self.tree_raw.column("Nombre", width=220)
        self.tree_raw.column("Marca", width=100)
        self.tree_raw.grid(row=1, column=0, sticky="nsew")

        scrollbar_raw = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree_raw.yview)
        self.tree_raw.configure(yscroll=scrollbar_raw.set)
        scrollbar_raw.grid(row=1, column=1, sticky="ns")

        right_frame = ctk.CTkFrame(self.tab_mapeo)
        right_frame.grid(row=1, column=1, padx=(5, 10), pady=5, sticky="nsew")
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right_frame, text="Maestro de Productos (Diccionario)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=5)
        self.tree_master = ttk.Treeview(right_frame, columns=("Código", "Nombre", "Marca"), show="headings")
        self.tree_master.heading("Código", text="Código")
        self.tree_master.heading("Nombre", text="Nombre Estándar")
        self.tree_master.heading("Marca", text="Marca")
        self.tree_master.column("Código", width=100)
        self.tree_master.column("Nombre", width=240)
        self.tree_master.column("Marca", width=120)
        self.tree_master.grid(row=1, column=0, sticky="nsew")

        scrollbar_master = ttk.Scrollbar(right_frame, orient="vertical", command=self.tree_master.yview)
        self.tree_master.configure(yscroll=scrollbar_master.set)
        scrollbar_master.grid(row=1, column=1, sticky="ns")

        bottom_controls = ctk.CTkFrame(self.tab_mapeo, fg_color="transparent")
        bottom_controls.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        ctk.CTkButton(bottom_controls, text="Vincular Seleccionados al Maestro", font=ctk.CTkFont(weight="bold"), command=self.link_products).pack(side="left", padx=5)

    def load_mapeo_data(self, *args):
        for i in self.tree_raw.get_children(): self.tree_raw.delete(i)
        for i in self.tree_master.get_children(): self.tree_master.delete(i)

        fuente = self.map_fuente_var.get()
        tipo = self.map_tipo_var.get()
        search_term = self.map_search_entry.get()

        self.df_raw = database.get_unmapped_products(fuente=fuente, tipo=tipo, search_term=search_term)
        for _, r in self.df_raw.head(500).iterrows():
            self.tree_raw.insert("", "end", values=(r['comercio'], r['producto_id'], r['nombre'], r['marca']))

        self.df_master = database.get_maestro_products(tipo=tipo, search_term=search_term)
        for _, r in self.df_master.head(500).iterrows():
            self.tree_master.insert("", "end", values=(r['codigo_universal'], r['nombre_estandar'], r['marca_estandar']))

    def link_products(self):
        sel_raw = self.tree_raw.selection()
        sel_master = self.tree_master.selection()
        if not sel_raw or not sel_master:
            messagebox.showwarning("Atención", "Selecciona al menos un producto crudo y un producto maestro.")
            return

        master_id = self.tree_master.item(sel_master[0])['values'][0]
        for s in sel_raw:
            vals = self.tree_raw.item(s)['values']
            database.add_mapping(vals[0], str(vals[1]), master_id)
        
        messagebox.showinfo("Éxito", f"Vinculados {len(sel_raw)} productos al maestro {master_id}.")
        self.load_mapeo_data()

    def run_etl(self):
        try:
            database.run_normalization_etl()
            messagebox.showinfo("Éxito", "Proceso ETL de normalización completado con éxito.")
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al ejecutar ETL: {e}")

    def export_mapeo_data(self):
        if hasattr(self, 'df_raw'):
            export_dataframe_dialog(self.df_raw, default_filename="productos_sin_mapear")

    # -------------------------------------------------------------
    # PASO 2: Depuración IA (Falsos Positivos)
    # -------------------------------------------------------------
    def _setup_ia_tab(self):
        self.tab_ia.grid_rowconfigure(0, weight=0)
        self.tab_ia.grid_rowconfigure(1, weight=1)
        self.tab_ia.grid_columnconfigure(0, weight=1)

        controls = ctk.CTkFrame(self.tab_ia, fg_color="transparent")
        controls.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(controls, text="API Key DeepSeek:").pack(side="left", padx=(0, 5))
        self.ia_api_entry = ctk.CTkEntry(controls, placeholder_text="Tu API Key de DeepSeek", width=220, show="*")
        env_key = os.getenv("DEEPSEEK_API_KEY")
        if env_key:
            self.ia_api_entry.insert(0, env_key)
        self.ia_api_entry.pack(side="left", padx=(0, 10))

        self.btn_ia_detect = ctk.CTkButton(controls, text="Buscar Atípicos con IA", fg_color="#2563eb", hover_color="#1d4ed8", font=ctk.CTkFont(weight="bold"), command=self.detect_fp)
        self.btn_ia_detect.pack(side="left", padx=(0, 10))

        self.btn_ia_remove = ctk.CTkButton(controls, text="Eliminar Seleccionados", fg_color="#ef4444", hover_color="#dc2626", font=ctk.CTkFont(weight="bold"), command=self.remove_fp_selected)
        self.btn_ia_remove.pack(side="right")

        self.ia_status_label = ctk.CTkLabel(controls, text="", text_color="#d97706", font=ctk.CTkFont(weight="bold"))
        self.ia_status_label.pack(side="right", padx=15)

        tree_frame = ctk.CTkFrame(self.tab_ia)
        tree_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.tree_fp = ttk.Treeview(tree_frame, columns=("DB_ID", "Nombre", "Marca", "Tipo"), show="headings")
        self.tree_fp.heading("DB_ID", text="ID Maestro")
        self.tree_fp.heading("Nombre", text="Nombre Estándar")
        self.tree_fp.heading("Marca", text="Marca Estándar")
        self.tree_fp.heading("Tipo", text="Tipo")
        
        self.tree_fp.column("DB_ID", width=140, anchor="center")
        self.tree_fp.column("Nombre", width=460)
        self.tree_fp.column("Marca", width=140, anchor="center")
        self.tree_fp.column("Tipo", width=110, anchor="center")
        self.tree_fp.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_fp.yview)
        self.tree_fp.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.false_positives = []

    def detect_fp(self):
        api_key = self.ia_api_entry.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Ingresa tu API Key de DeepSeek.")
            return

        self.btn_ia_detect.configure(state="disabled")
        threading.Thread(target=self._run_deepseek, args=(api_key,), daemon=True).start()

    def _run_deepseek(self, api_key):
        def set_status(text):
            self.after(0, lambda: self.ia_status_label.configure(text=text))
            
        try:
            set_status("Consultando Maestro de Productos...")
            df = database.get_maestro_products()
            if 'deleted' in df.columns:
                df = df[df['deleted'] == 0]
                
            if df.empty:
                self.after(0, lambda: messagebox.showinfo("Info", "El Maestro de Productos está vacío."))
                set_status("")
                return

            # Intentar usar el SDK de OpenAI o fallback transparente vía requests HTTP
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                use_sdk = True
            except ImportError:
                use_sdk = False

            df.rename(columns={'codigo_universal': 'id', 'nombre_estandar': 'nombre', 'marca_estandar': 'marca', 'tipo_producto_estandar': 'tipo'}, inplace=True)
            df = df.drop_duplicates(subset=['id'])

            prompt = """Eres un auditor de datos experto con amplio conocimiento en marcas y productos de consumo en Colombia.
Tu tarea es determinar si los siguientes productos son un "falso positivo" para la categoría de Alcohol o Tabaco basándote en el NOMBRE.

Criterio:
1. Evalúa el NOMBRE del producto. Si reconoces que el producto contiene alcohol, tabaco o es un vapeador, NO ES falso positivo (falso positivo = false).
2. Las bebidas que simulan ser alcohólicas pero no contienen alcohol (ej. 'Vino Sin Alcohol', 'Cerveza Zero') NO son falsos positivos.
3. Si el producto es un Combo o Pack que INCLUYE una bebida alcohólica/tabaco/vape, NO es falso positivo.
4. Un producto ES un FALSO POSITIVO (true) ÚNICAMENTE si se trata de un elemento no alcohólico/no tabaco por sí solo (ej. copas, vasos, baterías, hieleras, sodas, agua tónica, exprimidores, estuches vacíos, útiles, etc.).

Recibirás un array JSON. Devuelve ÚNICAMENTE un array plano de cadenas de texto (IDs) con los 'db_id' de aquellos que sí son falsos positivos (true).
Ejemplo de salida estricta: ["id1", "id2", "id3"]"""
            
            chunk_size = 50
            fp_db_ids = []
            total_chunks = len(df) // chunk_size + (1 if len(df) % chunk_size != 0 else 0)
            
            for i in range(0, len(df), chunk_size):
                chunk_index = i // chunk_size + 1
                set_status(f"Analizando bloque {chunk_index} de {total_chunks} con IA...")
                chunk_df = df.iloc[i:i+chunk_size]
                chunk_data = [{"db_id": str(r['id']), "nombre": str(r['nombre'])} for _, r in chunk_df.iterrows()]
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        if use_sdk:
                            response = client.chat.completions.create(
                                model='deepseek-chat',
                                messages=[
                                    {"role": "system", "content": "Return pure JSON array."},
                                    {"role": "user", "content": prompt + "\n\n" + json.dumps(chunk_data, ensure_ascii=False)}
                                ],
                                temperature=0.0
                            )
                            text = response.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
                        else:
                            import requests
                            res = requests.post(
                                "https://api.deepseek.com/chat/completions",
                                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                                json={
                                    "model": "deepseek-chat",
                                    "messages": [
                                        {"role": "system", "content": "Return pure JSON array."},
                                        {"role": "user", "content": prompt + "\n\n" + json.dumps(chunk_data, ensure_ascii=False)}
                                    ],
                                    "temperature": 0.0
                                },
                                timeout=60
                            )
                            res_data = res.json()
                            text = res_data["choices"][0]["message"]["content"].strip().replace("```json", "").replace("```", "").strip()

                        ids = json.loads(text)
                        if isinstance(ids, list):
                            fp_db_ids.extend([str(x) for x in ids])
                        break
                    except Exception:
                        if attempt < max_retries - 1:
                            time.sleep(5)
                time.sleep(0.3)

            self.false_positives = df[df['id'].isin(fp_db_ids)].to_dict('records')
            set_status("Análisis completado")
            self.after(0, self._update_fp_tree)

        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Error IA general", str(e)))
            set_status("")
        finally:
            self.after(0, lambda: self.btn_ia_detect.configure(state="normal"))

    def _update_fp_tree(self):
        for item in self.tree_fp.get_children():
            self.tree_fp.delete(item)
        
        all_items = []
        for p in self.false_positives:
            marca = p['marca'] if pd.notnull(p['marca']) else "N/A"
            tipo = p['tipo'] if pd.notnull(p['tipo']) else "N/A"
            item = self.tree_fp.insert("", "end", values=(p['id'], p['nombre'], marca, tipo))
            all_items.append(item)
            
        if all_items:
            self.tree_fp.selection_set(all_items)
            messagebox.showinfo("Búsqueda Lista", f"Se encontraron {len(all_items)} posibles falsos positivos.")

    def remove_fp_selected(self):
        selected = self.tree_fp.selection()
        if not selected:
            messagebox.showwarning("Atención", "No hay elementos seleccionados.")
            return
            
        count = 0
        for s in selected:
            item = self.tree_fp.item(s)
            db_id = item["values"][0]
            database.delete_false_positive(db_id)
            self.tree_fp.delete(s)
            count += 1
            
        messagebox.showinfo("Éxito", f"Se eliminaron {count} registros de la base de datos.")

    # -------------------------------------------------------------
    # PASO 3: Homologación INVIMA
    # -------------------------------------------------------------
    def _setup_invima_tab(self):
        self.tab_invima.grid_rowconfigure(0, weight=0)
        self.tab_invima.grid_rowconfigure(1, weight=1)
        self.tab_invima.grid_columnconfigure(0, weight=1)

        controls = ctk.CTkFrame(self.tab_invima, fg_color="transparent")
        controls.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(controls, text="Estado:").pack(side="left", padx=2)
        self.inv_estado_var = ctk.StringVar(value="Todos")
        self.inv_estado_combo = ctk.CTkComboBox(controls, variable=self.inv_estado_var, values=["Todos", "Ligados", "Sin Registro", "Tabaco", "No Aplica"], command=self.load_invima_data, width=130)
        self.inv_estado_combo.pack(side="left", padx=4)

        ctk.CTkLabel(controls, text="Tipo:").pack(side="left", padx=(8, 2))
        self.inv_tipo_var = ctk.StringVar(value="Todos")
        self.inv_tipo_combo = ctk.CTkComboBox(controls, variable=self.inv_tipo_var, values=["Todos", "Alcohol", "Tabaco"], command=self.load_invima_data, width=100)
        self.inv_tipo_combo.pack(side="left", padx=4)

        ctk.CTkLabel(controls, text="Subcategoría:").pack(side="left", padx=(8, 2))
        self.inv_subcat_var = ctk.StringVar(value="Todas")
        self.inv_subcat_combo = ctk.CTkComboBox(controls, variable=self.inv_subcat_var, command=self.load_invima_data, width=140)
        self.inv_subcat_combo.pack(side="left", padx=4)

        ctk.CTkLabel(controls, text="Buscar:").pack(side="left", padx=(8, 2))
        self.inv_search_entry = ctk.CTkEntry(controls, placeholder_text="Código, Nombre, Marca o INVIMA...", width=200)
        self.inv_search_entry.pack(side="left", padx=4)
        self.inv_search_entry.bind("<Return>", lambda e: self.load_invima_data())

        ctk.CTkButton(controls, text="Buscar", width=70, command=self.load_invima_data).pack(side="left", padx=2)
        ctk.CTkButton(controls, text="Exportar", fg_color="#10b981", hover_color="#059669", width=90, command=self.export_invima_data).pack(side="right", padx=5)
        ctk.CTkButton(controls, text="Asignar / Editar INVIMA", fg_color="#2563eb", hover_color="#1d4ed8", font=ctk.CTkFont(weight="bold"), command=self.open_assign_modal).pack(side="right", padx=5)

        tree_frame = ctk.CTkFrame(self.tab_invima)
        tree_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columns = ("Código Maestro", "Nombre Estándar", "Marca", "Tipo", "Registro INVIMA", "Nombre Certificado INVIMA")
        self.tree_inv = ttk.Treeview(tree_frame, columns=columns, show="headings")

        self.tree_inv.heading("Código Maestro", text="Código Maestro")
        self.tree_inv.column("Código Maestro", width=120, anchor="center")
        self.tree_inv.heading("Nombre Estándar", text="Nombre Estándar")
        self.tree_inv.column("Nombre Estándar", width=320)
        self.tree_inv.heading("Marca", text="Marca")
        self.tree_inv.column("Marca", width=120)
        self.tree_inv.heading("Tipo", text="Tipo")
        self.tree_inv.column("Tipo", width=90, anchor="center")
        self.tree_inv.heading("Registro INVIMA", text="Registro INVIMA")
        self.tree_inv.column("Registro INVIMA", width=180, anchor="center")
        self.tree_inv.heading("Nombre Certificado INVIMA", text="Nombre Certificado INVIMA")
        self.tree_inv.column("Nombre Certificado INVIMA", width=300)

        self.tree_inv.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_inv.yview)
        self.tree_inv.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree_inv.bind("<Double-Button-1>", lambda e: self.open_assign_modal())

    def load_invima_data(self, *args):
        estado = self.inv_estado_var.get()
        tipo = self.inv_tipo_var.get()
        subcat = self.inv_subcat_var.get()
        search_term = self.inv_search_entry.get()

        df = database.get_maestro_products_invima(
            filter_type=estado, 
            tipo=tipo, 
            subcategoria=subcat, 
            search_term=search_term
        )
        self.df_invima_current = df
        
        for item in self.tree_inv.get_children():
            self.tree_inv.delete(item)

        if df.empty:
            return

        for _, r in df.iterrows():
            inv_reg = r.get('registro_sanitario_invima') or 'SIN_REGISTRO_ENCONTRADO'
            inv_nom = r.get('nombre_invima') or ''
            self.tree_inv.insert("", "end", values=(
                r['codigo_universal'], r['nombre_estandar'], r['marca_estandar'], r['tipo_producto_estandar'], inv_reg, inv_nom
            ))

    def open_assign_modal(self):
        selected = self.tree_inv.selection()
        if not selected:
            messagebox.showwarning("Atención", "Selecciona un producto de la tabla para asignar/editar su Registro INVIMA.")
            return

        selected_items = [self.tree_inv.item(s)['values'] for s in selected]
        AssignInvimaModal(self, selected_items, self.on_invima_assigned)

    def on_invima_assigned(self, items, new_code):
        count = 0
        for item in items:
            cod_uni = item[0]
            database.update_master_invima_code(cod_uni, new_code)
            count += 1

        messagebox.showinfo("Éxito", f"Se asignó el registro '{new_code}' a {count} productos correctamente.")
        self.load_invima_data()

    def export_invima_data(self):
        if hasattr(self, 'df_invima_current'):
            export_dataframe_dialog(self.df_invima_current, default_filename="maestro_invima_mdm")

    # -------------------------------------------------------------
    # PASO 4: Catálogo Nacional INVIMA
    # -------------------------------------------------------------
    def _setup_catalogo_tab(self):
        self.tab_catalogo.grid_rowconfigure(0, weight=0)
        self.tab_catalogo.grid_rowconfigure(1, weight=1)
        self.tab_catalogo.grid_rowconfigure(2, weight=0)
        self.tab_catalogo.grid_columnconfigure(0, weight=1)

        controls = ctk.CTkFrame(self.tab_catalogo, fg_color="transparent")
        controls.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(controls, text="Buscar:").pack(side="left", padx=2)
        self.cat_search_entry = ctk.CTkEntry(controls, placeholder_text="Registro Sanitario, Producto, Marca...", width=320)
        self.cat_search_entry.pack(side="left", padx=5)
        self.cat_search_entry.bind("<Return>", lambda e: self.on_catalogo_search())

        self.btn_cat_search = ctk.CTkButton(controls, text="Buscar", width=80, command=self.on_catalogo_search)
        self.btn_cat_search.pack(side="left", padx=5)

        self.btn_cat_add = ctk.CTkButton(controls, text="+ Registrar Nuevo INVIMA", fg_color="#2563eb", hover_color="#1d4ed8", font=ctk.CTkFont(weight="bold"), command=self.open_add_catalogo_modal)
        self.btn_cat_add.pack(side="right", padx=5)

        self.btn_cat_export = ctk.CTkButton(controls, text="Exportar Catálogo", fg_color="#10b981", hover_color="#059669", command=self.export_catalogo_data)
        self.btn_cat_export.pack(side="right", padx=5)

        tree_frame = ctk.CTkFrame(self.tab_catalogo)
        tree_frame.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columns = ("ID", "Registro Sanitario", "Producto Certificado", "Marca", "Clasificación", "Grados Alcohol")
        self.tree_cat = ttk.Treeview(tree_frame, columns=columns, show="headings")

        self.tree_cat.heading("ID", text="ID")
        self.tree_cat.column("ID", width=60, anchor="center")
        self.tree_cat.heading("Registro Sanitario", text="Registro Sanitario")
        self.tree_cat.column("Registro Sanitario", width=180, anchor="center")
        self.tree_cat.heading("Producto Certificado", text="Nombre Bebida Alcohólica (INVIMA)")
        self.tree_cat.column("Producto Certificado", width=380)
        self.tree_cat.heading("Marca", text="Marca")
        self.tree_cat.column("Marca", width=140)
        self.tree_cat.heading("Clasificación", text="Clasificación")
        self.tree_cat.column("Clasificación", width=160)
        self.tree_cat.heading("Grados Alcohol", text="Grados Alcohol")
        self.tree_cat.column("Grados Alcohol", width=110, anchor="center")

        self.tree_cat.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_cat.yview)
        self.tree_cat.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        pagination_frame = ctk.CTkFrame(self.tab_catalogo, fg_color="transparent")
        pagination_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")

        self.btn_cat_prev = ctk.CTkButton(pagination_frame, text="◀ Anterior", width=90, command=self.prev_catalogo_page)
        self.btn_cat_prev.pack(side="left", padx=5)

        self.lbl_cat_page_info = ctk.CTkLabel(pagination_frame, text="Página 1 de 1", font=ctk.CTkFont(weight="bold"))
        self.lbl_cat_page_info.pack(side="left", padx=15)

        self.btn_cat_next = ctk.CTkButton(pagination_frame, text="Siguiente ▶", width=90, command=self.next_catalogo_page)
        self.btn_cat_next.pack(side="left", padx=5)

    def on_catalogo_search(self):
        self.cat_current_page = 0
        self.load_catalogo_data()

    def load_catalogo_data(self):
        search_term = self.cat_search_entry.get()
        offset = self.cat_current_page * self.cat_page_size
        
        df, total_count = database.get_invima_certificados(search_term=search_term, limit=self.cat_page_size, offset=offset)
        self.cat_total_count = total_count
        self.df_catalogo_current = df
        
        for item in self.tree_cat.get_children():
            self.tree_cat.delete(item)

        if not df.empty:
            for _, r in df.iterrows():
                self.tree_cat.insert("", "end", values=(
                    r.get('id', ''), r.get('registro_sanitario', ''), r.get('nombre_bebida_alcoholica', ''),
                    r.get('marca', ''), r.get('clasificacion', ''), r.get('grados_alcohol', '')
                ))

        total_pages = max(1, (total_count + self.cat_page_size - 1) // self.cat_page_size)
        self.lbl_cat_page_info.configure(text=f"Página {self.cat_current_page + 1} de {total_pages} (Total: {total_count:,} registros)")
        self.btn_cat_prev.configure(state="normal" if self.cat_current_page > 0 else "disabled")
        self.btn_cat_next.configure(state="normal" if (self.cat_current_page + 1) < total_pages else "disabled")

    def prev_catalogo_page(self):
        if self.cat_current_page > 0:
            self.cat_current_page -= 1
            self.load_catalogo_data()

    def next_catalogo_page(self):
        total_pages = max(1, (self.cat_total_count + self.cat_page_size - 1) // self.cat_page_size)
        if (self.cat_current_page + 1) < total_pages:
            self.cat_current_page += 1
            self.load_catalogo_data()

    def export_catalogo_data(self):
        if hasattr(self, 'df_catalogo_current'):
            export_dataframe_dialog(self.df_catalogo_current, default_filename="catalogo_invima_certificados")

    def open_add_catalogo_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Registrar Nuevo Certificado INVIMA")
        modal.geometry("500x520")
        modal.resizable(False, False)
        modal.transient(self.winfo_toplevel())
        modal.grab_set()

        ctk.CTkLabel(modal, text="Agregar Nuevo Registro Sanitario INVIMA", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15)

        form = ctk.CTkFrame(modal, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=25, pady=5)

        fields = [
            ("Registro Sanitario:", "entry_reg", "Ej: INVIMA 2023L-0012345"),
            ("Código Único:", "entry_cod", "Ej: 2023L-0012345"),
            ("Nombre Producto:", "entry_nom", "Ej: RON MEDELLIN AÑEJO 750ML"),
            ("Marca:", "entry_mar", "Ej: RON MEDELLIN"),
            ("Clasificación:", "entry_clas", "Ej: Ron"),
            ("Grados de Alcohol (%):", "entry_grad", "Ej: 35.0%")
        ]

        entries = {}
        for label_text, var_name, placeholder in fields:
            f = ctk.CTkFrame(form, fg_color="transparent")
            f.pack(fill="x", pady=4)
            ctk.CTkLabel(f, text=label_text, width=150, anchor="w").pack(side="left")
            e = ctk.CTkEntry(f, placeholder_text=placeholder, width=280)
            e.pack(side="left", fill="x", expand=True)
            entries[var_name] = e

        def save_new():
            reg = entries['entry_reg'].get().strip()
            cod = entries['entry_cod'].get().strip()
            nom = entries['entry_nom'].get().strip()
            mar = entries['entry_mar'].get().strip()
            clas = entries['entry_clas'].get().strip()
            grad = entries['entry_grad'].get().strip()

            if not reg or not nom:
                messagebox.showwarning("Atención", "El Registro Sanitario y el Nombre del Producto son obligatorios.")
                return

            database.add_invima_certificado(reg, cod, nom, mar, clas, grad)
            messagebox.showinfo("Éxito", "Nuevo certificado INVIMA registrado correctamente.")
            modal.destroy()
            self.load_catalogo_data()

        ctk.CTkButton(modal, text="Guardar Certificado", fg_color="#2563eb", hover_color="#1d4ed8", font=ctk.CTkFont(weight="bold"), command=save_new).pack(pady=20)
