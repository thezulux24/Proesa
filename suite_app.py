import os
import json
import datetime
import subprocess
import threading
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as ticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
from dotenv import load_dotenv

import database

load_dotenv()

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

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

        card_info = ctk.CTkFrame(self, fg_color="#1f2937", corner_radius=8)
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

        self.preview_frame = ctk.CTkFrame(self, fg_color="#111827", corner_radius=8)
        self.preview_frame.pack(fill="both", expand=True, padx=25, pady=10)

        ctk.CTkLabel(self.preview_frame, text="Coincidencia en Catálogo Oficial Certificado:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#9ca3af").pack(anchor="w", padx=12, pady=(10, 4))
        self.lbl_preview = ctk.CTkLabel(self.preview_frame, text="Escribe un código arriba para validar en el catálogo oficial...", font=ctk.CTkFont(size=11, slant="italic"), text_color="#6b7280", justify="left", wraplength=500)
        self.lbl_preview.pack(anchor="w", padx=12, pady=(0, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25, pady=15)

        ctk.CTkButton(btn_frame, text="Guardar y Vincular", fg_color="#2563eb", hover_color="#1d4ed8", font=ctk.CTkFont(weight="bold"), command=self.save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Marcar NO APLICA (-1)", fg_color="#d97706", hover_color="#b45309", command=self.set_no_aplica).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="#4b5563", hover_color="#374151", command=self.destroy).pack(side="right", padx=5)

        self.on_invima_key_release(None)

    def on_invima_key_release(self, event):
        code = self.entry_invima.get().strip()
        if not code:
            self.lbl_preview.configure(text="Escribe un código arriba para validar en el catálogo oficial...", text_color="#6b7280")
            return

        db = database.DataSuiteDB()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT registro_sanitario, codigo_unico, nombre_bebida_alcoholica, marca, grados_alcohol 
                FROM invima_certificados 
                WHERE UPPER(registro_sanitario) LIKE ? OR UPPER(registro_sanitario) LIKE ?
                LIMIT 1
            """, (f"%{code.upper()}%", f"%{code.upper().replace('INVIMA', '').strip()}%"))
            row = cur.fetchone()

        if row:
            reg, c_unique, name_cert, brand_cert, alc = row
            text = f"REGISTRO ENCONTRADO EN BASE OFICIAL:\n• Registro: {reg}\n• Código Único: {c_unique or 'N/A'}\n• Bebida: {name_cert}\n• Marca: {brand_cert or 'N/A'} | Alcohol: {alc or 'N/A'}°"
            self.lbl_preview.configure(text=text, text_color="#10b981")
        else:
            text = f"CÓDIGO NUEVO / NO ENCONTRADO EN CATÁLOGO CERTIFICADO:\nSe asignará '{code}' como ASIGNACIÓN MANUAL."
            self.lbl_preview.configure(text=text, text_color="#f59e0b")

    def save(self):
        new_code = self.entry_invima.get().strip()
        if not new_code:
            messagebox.showwarning("Atención", "Ingresa un Registro Sanitario INVIMA válido.")
            return

        self.on_save(self.selected_items, new_code)
        self.destroy()

    def set_no_aplica(self):
        self.on_save(self.selected_items, "NO_APLICA")
        self.destroy()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        db = database.DataSuiteDB()
        db.init_db()
        
        self.title("PROESA - Suite Data & Mercado (Alcohol y Tabaco)")
        self.geometry("1420x920")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#111827")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Suite Data PROESA", font=ctk.CTkFont(size=20, weight="bold"), text_color="#f9fafb")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(25, 20))

        btn_kwargs = {
            "font": ctk.CTkFont(size=14),
            "height": 38,
            "anchor": "w",
            "fg_color": "transparent",
            "text_color": "#d1d5db",
            "hover_color": "#1f2937"
        }

        self.btn_extraccion = ctk.CTkButton(self.sidebar_frame, text=" Módulo Extracción", command=self.show_extraccion, **btn_kwargs)
        self.btn_extraccion.grid(row=1, column=0, padx=15, pady=4, sticky="ew")

        self.btn_viewer = ctk.CTkButton(self.sidebar_frame, text=" Visor Datos Crudos", command=self.show_viewer, **btn_kwargs)
        self.btn_viewer.grid(row=2, column=0, padx=15, pady=4, sticky="ew")

        self.btn_norm_viewer = ctk.CTkButton(self.sidebar_frame, text=" Visor Normalizado", command=self.show_norm_viewer, **btn_kwargs)
        self.btn_norm_viewer.grid(row=3, column=0, padx=15, pady=4, sticky="ew")

        self.btn_analysis = ctk.CTkButton(self.sidebar_frame, text=" Análisis de Precios", command=self.show_analysis, **btn_kwargs)
        self.btn_analysis.grid(row=4, column=0, padx=15, pady=4, sticky="ew")

        self.btn_gestion_invima = ctk.CTkButton(self.sidebar_frame, text=" Gestión INVIMA MDM", command=self.show_gestion_invima, **btn_kwargs)
        self.btn_gestion_invima.grid(row=5, column=0, padx=15, pady=4, sticky="ew")

        self.btn_catalogo_invima = ctk.CTkButton(self.sidebar_frame, text=" Catálogo Nacional INVIMA", command=self.show_catalogo_invima, **btn_kwargs)
        self.btn_catalogo_invima.grid(row=6, column=0, padx=15, pady=4, sticky="ew")

        self.btn_deepseek = ctk.CTkButton(self.sidebar_frame, text=" Depuración IA", command=self.show_deepseek, **btn_kwargs)
        self.btn_deepseek.grid(row=7, column=0, padx=15, pady=4, sticky="ew")

        self.btn_compare = ctk.CTkButton(self.sidebar_frame, text=" Comparativas Mercado", command=self.show_compare, **btn_kwargs)
        self.btn_compare.grid(row=8, column=0, padx=15, pady=4, sticky="ew")

        self.btn_normalization = ctk.CTkButton(self.sidebar_frame, text=" Asignación Mapeo MDM", command=self.show_normalization, **btn_kwargs)
        self.btn_normalization.grid(row=9, column=0, padx=15, pady=4, sticky="ew")

        self.frame_extraccion = ExtraccionFrame(self)
        self.frame_viewer = DataViewerFrame(self)
        self.frame_norm_viewer = NormalizedViewerFrame(self)
        self.frame_analysis = AnalysisFrame(self)
        self.frame_gestion_invima = GestionINVIMAFrame(self)
        self.frame_catalogo_invima = CatalogoINVIMAFrame(self)
        self.frame_deepseek = DeepSeekFilterFrame(self)
        self.frame_compare = CompareFrame(self)
        self.frame_normalization = NormalizationFrame(self)

        self.show_norm_viewer()

    def hide_all_frames(self):
        self.frame_extraccion.grid_forget()
        self.frame_viewer.grid_forget()
        self.frame_norm_viewer.grid_forget()
        self.frame_analysis.grid_forget()
        self.frame_gestion_invima.grid_forget()
        self.frame_catalogo_invima.grid_forget()
        self.frame_deepseek.grid_forget()
        self.frame_compare.grid_forget()
        self.frame_normalization.grid_forget()

        for btn in [self.btn_extraccion, self.btn_viewer, self.btn_norm_viewer, self.btn_analysis,
                    self.btn_gestion_invima, self.btn_catalogo_invima, self.btn_deepseek, self.btn_compare, self.btn_normalization]:
            btn.configure(fg_color="transparent", text_color="#d1d5db")

    def _activate_button(self, button):
        button.configure(fg_color="#2563eb", text_color="#ffffff")

    def show_extraccion(self):
        self.hide_all_frames()
        self._activate_button(self.btn_extraccion)
        self.frame_extraccion.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_viewer(self):
        self.hide_all_frames()
        self._activate_button(self.btn_viewer)
        self.frame_viewer.load_filters()
        self.frame_viewer.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_norm_viewer(self):
        self.hide_all_frames()
        self._activate_button(self.btn_norm_viewer)
        self.frame_norm_viewer.load_filters()
        self.frame_norm_viewer.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_analysis(self):
        self.hide_all_frames()
        self._activate_button(self.btn_analysis)
        self.frame_analysis.load_filters()
        self.frame_analysis.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_gestion_invima(self):
        self.hide_all_frames()
        self._activate_button(self.btn_gestion_invima)
        self.frame_gestion_invima.load_filters()
        self.frame_gestion_invima.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_catalogo_invima(self):
        self.hide_all_frames()
        self._activate_button(self.btn_catalogo_invima)
        self.frame_catalogo_invima.load_data()
        self.frame_catalogo_invima.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_deepseek(self):
        self.hide_all_frames()
        self._activate_button(self.btn_deepseek)
        self.frame_deepseek.load_filters()
        self.frame_deepseek.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_compare(self):
        self.hide_all_frames()
        self._activate_button(self.btn_compare)
        self.frame_compare.load_filters()
        self.frame_compare.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_normalization(self):
        self.hide_all_frames()
        self._activate_button(self.btn_normalization)
        self.frame_normalization.load_filters()
        self.frame_normalization.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)


# ==========================================
# 1. Extracción Frame
# ==========================================
class ExtraccionFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="Módulo de Extracción de Datos", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        self.controls = ctk.CTkFrame(self, fg_color="transparent")
        self.controls.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self.controls, text="Seleccionar Comercio / Scraper:", font=ctk.CTkFont(size=14)).pack(side="left", padx=(0,10))
        self.scraper_var = ctk.StringVar(value="Todos los Comercios")
        self.scrapers_list = ["Todos los Comercios", "Éxito", "Carulla", "Jumbo", "Olímpica", "D1", "Makro", "Cañaveral"]
        self.scraper_combo = ctk.CTkComboBox(self.controls, variable=self.scraper_var, values=self.scrapers_list, width=220)
        self.scraper_combo.pack(side="left", padx=(0,20))

        self.btn_run = ctk.CTkButton(self.controls, text="Ejecutar Extracción", fg_color="#2563eb", hover_color="#1d4ed8", font=ctk.CTkFont(weight="bold"), command=self.run_scraper)
        self.btn_run.pack(side="left")

        self.textbox = ctk.CTkTextbox(self, state="disabled", wrap="word", font=ctk.CTkFont(family="Consolas", size=12))
        self.textbox.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="nsew")

    def log(self, msg):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", msg + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def run_scraper(self):
        target = self.scraper_var.get()
        self.btn_run.configure(state="disabled")
        self.log(f"Iniciando proceso de extracción: {target}...")
        threading.Thread(target=self._run_process, args=(target,), daemon=True).start()

    def _run_process(self, target):
        script_map = {
            "Éxito": ["python", "scraper_exito/scraper.py"],
            "Carulla": ["python", "scraper_carulla/scraper.py"],
            "Jumbo": ["python", "scraper_jumbo/scraper.py"],
            "Olímpica": ["python", "scraper_olimpica/scraper.py"],
            "D1": ["python", "scraper_d1/scraper.py"],
            "Makro": ["python", "scraper_makro/scraper.py"],
            "Cañaveral": ["python", "scraper_canaveral/scraper.py"],
            "Todos los Comercios": ["python", "main.py"]
        }
        cmd = script_map.get(target, ["python", "main.py"])
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in process.stdout:
                self.log(line.strip())
            process.wait()
            
            self.log("Refrescando base de datos SQLite y ejecutando ETL...")
            database.run_normalization_etl()
            self.log("Proceso de extracción y normalización finalizado correctamente.")
        except Exception as e:
            self.log(f"Error durante la extracción: {e}")
        finally:
            self.btn_run.configure(state="normal")


# ==========================================
# 2. Visor de Datos Crudos
# ==========================================
class DataViewerFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="Visor de Datos Crudos (Histórico)", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.fecha_inicio = None
        self.fecha_fin = None

        self.filters_container = ctk.CTkFrame(self, fg_color="#1f2937", corner_radius=8)
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

        self.btn_range = ctk.CTkButton(row1, text="Rango Fechas", fg_color="#374151", hover_color="#4b5563", width=110, command=self.open_date_modal)
        self.btn_range.pack(side="left", padx=10)

        self.lbl_range_info = ctk.CTkLabel(row1, text="Todas las fechas", text_color="#9ca3af", font=ctk.CTkFont(size=11, slant="italic"))
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

        self.btn_export = ctk.CTkButton(row2, text="Exportar (Excel / JSON / CSV)", fg_color="#10b981", hover_color="#059669", command=self.export_data)
        self.btn_export.pack(side="right", padx=5)

        self.btn_remove = ctk.CTkButton(row2, text="Eliminar (Soft)", fg_color="#ef4444", hover_color="#dc2626", command=self.soft_delete_selected)
        self.btn_remove.pack(side="right", padx=5)

        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        columns = ("ID", "Fuente", "Fecha", "Nombre", "Marca", "Categoría", "Tipo", "Precio Final", "Alcohol")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")
        
        self.tree.heading("ID", text="ID BD")
        self.tree.column("ID", width=60, anchor="center")
        self.tree.heading("Fuente", text="Fuente")
        self.tree.column("Fuente", width=90, anchor="center")
        self.tree.heading("Fecha", text="Fecha")
        self.tree.column("Fecha", width=90, anchor="center")
        self.tree.heading("Nombre", text="Nombre")
        self.tree.column("Nombre", width=340)
        self.tree.heading("Marca", text="Marca")
        self.tree.column("Marca", width=120)
        self.tree.heading("Categoría", text="Categoría")
        self.tree.column("Categoría", width=130)
        self.tree.heading("Tipo", text="Tipo")
        self.tree.column("Tipo", width=90, anchor="center")
        self.tree.heading("Precio Final", text="Precio Final")
        self.tree.column("Precio Final", width=90, anchor="e")
        self.tree.heading("Alcohol", text="Alcohol")
        self.tree.column("Alcohol", width=70, anchor="center")

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
            
            self.tree.insert("", "end", values=(
                r['id'], r['fuente'], str(r.get('fecha_extraccion', '')), r['nombre'], r['marca'], r['categoria'], 
                r['tipo_producto'], precio_str, r['grados_alcohol']
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


# ==========================================
# 3. Visor Normalizado
# ==========================================
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

        self.filters_container = ctk.CTkFrame(self, fg_color="#1f2937", corner_radius=8)
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

        self.btn_range = ctk.CTkButton(row1, text="Rango Fechas", fg_color="#374151", hover_color="#4b5563", width=100, command=self.open_date_modal)
        self.btn_range.pack(side="left", padx=8)

        self.lbl_range_info = ctk.CTkLabel(row1, text="Todas las fechas", text_color="#9ca3af", font=ctk.CTkFont(size=11, slant="italic"))
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

        self.btn_export = ctk.CTkButton(row2, text="Exportar (Excel / JSON / CSV)", fg_color="#10b981", hover_color="#059669", command=self.export_data)
        self.btn_export.pack(side="right", padx=5)

        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=2, column=0, padx=20, pady=(0, 5), sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        columns = ("Código", "Fuente", "Fecha", "Nombre Estándar", "Marca", "Categoría", "Registro INVIMA", "Precio Final")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")
        
        self.tree.heading("Código", text="Código Universal")
        self.tree.column("Código", width=110, anchor="center")
        self.tree.heading("Fuente", text="Fuente")
        self.tree.column("Fuente", width=90, anchor="center")
        self.tree.heading("Fecha", text="Fecha")
        self.tree.column("Fecha", width=90, anchor="center")
        self.tree.heading("Nombre Estándar", text="Nombre Estándar")
        self.tree.column("Nombre Estándar", width=300)
        self.tree.heading("Marca", text="Marca")
        self.tree.column("Marca", width=120)
        self.tree.heading("Categoría", text="Categoría")
        self.tree.column("Categoría", width=120)
        self.tree.heading("Registro INVIMA", text="Registro INVIMA")
        self.tree.column("Registro INVIMA", width=160, anchor="center")
        self.tree.heading("Precio Final", text="Precio Final")
        self.tree.column("Precio Final", width=100, anchor="e")

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

                self.tree.insert("", "end", values=(
                    row.get('id', ''),
                    row.get('fuente', ''),
                    str(row.get('fecha_extraccion', '')),
                    row.get('nombre', ''),
                    row.get('marca_estandar', ''),
                    row.get('subcategoria_estandar', ''),
                    invima_val,
                    pf_str
                ))

        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        self.lbl_page_info.configure(text=f"Página {self.current_page + 1} de {total_pages} ({self.total_count:,} registros)")
        
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


# ==========================================
# 4. Sección Gestión INVIMA MDM
# ==========================================
class GestionINVIMAFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="Gestión de Registro Sanitario INVIMA (Productos Maestros)", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.controls = ctk.CTkFrame(self, fg_color="#1f2937", corner_radius=8)
        self.controls.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        row1 = ctk.CTkFrame(self.controls, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(row1, text="Estado:").pack(side="left", padx=2)
        self.estado_var = ctk.StringVar(value="Todos")
        self.estado_combo = ctk.CTkComboBox(row1, variable=self.estado_var, values=["Todos", "Ligados", "Sin Registro", "Tabaco", "No Aplica"], command=self.load_data, width=130)
        self.estado_combo.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Tipo:").pack(side="left", padx=(10, 2))
        self.tipo_var = ctk.StringVar(value="Todos")
        self.tipo_combo = ctk.CTkComboBox(row1, variable=self.tipo_var, values=["Todos", "Alcohol", "Tabaco"], command=self.load_data, width=100)
        self.tipo_combo.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Subcategoría:").pack(side="left", padx=(10, 2))
        self.subcat_var = ctk.StringVar(value="Todas")
        self.subcat_combo = ctk.CTkComboBox(row1, variable=self.subcat_var, command=self.load_data, width=140)
        self.subcat_combo.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Buscar:").pack(side="left", padx=(10, 2))
        self.search_entry = ctk.CTkEntry(row1, placeholder_text="Código, Nombre, Marca o INVIMA...", width=200)
        self.search_entry.pack(side="left", padx=4)
        self.search_entry.bind("<Return>", lambda e: self.load_data())

        self.btn_search = ctk.CTkButton(row1, text="Buscar", width=70, command=self.load_data)
        self.btn_search.pack(side="left", padx=2)

        self.btn_export = ctk.CTkButton(row1, text="Exportar", fg_color="#10b981", hover_color="#059669", width=90, command=self.export_data)
        self.btn_export.pack(side="right", padx=5)

        self.btn_open_modal = ctk.CTkButton(
            row1, 
            text="Asignar / Editar INVIMA", 
            fg_color="#2563eb", 
            hover_color="#1d4ed8", 
            font=ctk.CTkFont(weight="bold"), 
            command=self.open_assign_modal
        )
        self.btn_open_modal.pack(side="right", padx=5)

        # Treeview
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        columns = ("Código Maestro", "Nombre Estándar", "Marca", "Tipo", "Registro INVIMA", "Nombre Certificado INVIMA")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")

        self.tree.heading("Código Maestro", text="Código Maestro")
        self.tree.column("Código Maestro", width=120, anchor="center")
        self.tree.heading("Nombre Estándar", text="Nombre Estándar")
        self.tree.column("Nombre Estándar", width=320)
        self.tree.heading("Marca", text="Marca")
        self.tree.column("Marca", width=120)
        self.tree.heading("Tipo", text="Tipo")
        self.tree.column("Tipo", width=90, anchor="center")
        self.tree.heading("Registro INVIMA", text="Registro INVIMA")
        self.tree.column("Registro INVIMA", width=180, anchor="center")
        self.tree.heading("Nombre Certificado INVIMA", text="Nombre Certificado INVIMA")
        self.tree.column("Nombre Certificado INVIMA", width=300)

        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-Button-1>", lambda e: self.open_assign_modal())

    def load_filters(self):
        subcats = database.get_available_subcategories()
        self.subcat_combo.configure(values=subcats)
        self.load_data()

    def load_data(self, *args):
        estado = self.estado_var.get()
        tipo = self.tipo_var.get()
        subcat = self.subcat_var.get()
        search_term = self.search_entry.get()

        df = database.get_maestro_products_invima(
            filter_type=estado, 
            tipo=tipo, 
            subcategoria=subcat, 
            search_term=search_term
        )
        self.df_current = df
        
        for item in self.tree.get_children():
            self.tree.delete(item)

        if df.empty:
            return

        for _, r in df.iterrows():
            inv_reg = r.get('registro_sanitario_invima') or 'SIN_REGISTRO_ENCONTRADO'
            inv_nom = r.get('nombre_invima') or ''
            self.tree.insert("", "end", values=(
                r['codigo_universal'], r['nombre_estandar'], r['marca_estandar'], r['tipo_producto_estandar'], inv_reg, inv_nom
            ))

    def open_assign_modal(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Selecciona un producto de la tabla para asignar/editar su Registro INVIMA.")
            return

        selected_items = [self.tree.item(s)['values'] for s in selected]
        AssignInvimaModal(self, selected_items, self.on_invima_assigned)

    def on_invima_assigned(self, items, new_code):
        count = 0
        for item in items:
            cod_uni = item[0]
            database.update_master_invima_code(cod_uni, new_code)
            count += 1

        messagebox.showinfo("Éxito", f"Se asignó el registro '{new_code}' a {count} productos correctamente.")
        self.load_data()

    def export_data(self):
        if hasattr(self, 'df_current'):
            export_dataframe_dialog(self.df_current, default_filename="maestro_invima_mdm")


# ==========================================
# 5. Sección Catálogo Nacional INVIMA
# ==========================================
class CatalogoINVIMAFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="Catálogo Nacional de Certificados INVIMA", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.current_page = 0
        self.page_size = 200
        self.total_count = 0

        self.controls = ctk.CTkFrame(self, fg_color="transparent")
        self.controls.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(self.controls, text="Buscar:").pack(side="left", padx=2)
        self.search_entry = ctk.CTkEntry(self.controls, placeholder_text="Registro, Marca o Nombre Bebida...", width=280)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<Return>", lambda e: self.on_search())

        self.btn_search = ctk.CTkButton(self.controls, text="Buscar", width=70, command=self.on_search)
        self.btn_search.pack(side="left", padx=2)

        self.btn_export = ctk.CTkButton(self.controls, text="Exportar (Excel / JSON / CSV)", fg_color="#10b981", hover_color="#059669", command=self.export_data)
        self.btn_export.pack(side="right", padx=5)

        self.btn_new_cert = ctk.CTkButton(self.controls, text="Nuevo Registro INVIMA", fg_color="#2563eb", hover_color="#1d4ed8", font=ctk.CTkFont(weight="bold"), command=self.open_add_modal)
        self.btn_new_cert.pack(side="right", padx=5)

        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=2, column=0, padx=20, pady=(0, 5), sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        columns = ("Registro Sanitario", "Código Único", "Nombre Bebida Alcohólica", "Marca", "Clasificación", "Grados Alcohol")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")

        self.tree.heading("Registro Sanitario", text="Registro Sanitario")
        self.tree.column("Registro Sanitario", width=160, anchor="center")
        self.tree.heading("Código Único", text="Código Único")
        self.tree.column("Código Único", width=110, anchor="center")
        self.tree.heading("Nombre Bebida Alcohólica", text="Nombre Bebida Alcohólica Certificada")
        self.tree.column("Nombre Bebida Alcohólica", width=380)
        self.tree.heading("Marca", text="Marca")
        self.tree.column("Marca", width=140)
        self.tree.heading("Clasificación", text="Clasificación")
        self.tree.column("Clasificación", width=140)
        self.tree.heading("Grados Alcohol", text="Grados Alcohol (°)")
        self.tree.column("Grados Alcohol", width=110, anchor="center")

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

    def on_search(self):
        self.current_page = 0
        self.load_data()

    def load_data(self):
        search_term = self.search_entry.get()
        offset = self.current_page * self.page_size
        df, total_count = database.get_invima_certificados(search_term=search_term, limit=self.page_size, offset=offset)
        self.total_count = total_count

        for item in self.tree.get_children():
            self.tree.delete(item)

        if not df.empty:
            for _, r in df.iterrows():
                c_unique = r.get('codigo_unico') or 'N/A'
                marca_val = r.get('marca') or 'N/A'
                clas_val = r.get('clasificacion') or 'N/A'
                grados_val = r.get('grados_alcohol') or 'N/A'
                
                self.tree.insert("", "end", values=(
                    r.get('registro_sanitario', ''),
                    c_unique,
                    r.get('nombre_bebida_alcoholica', ''),
                    marca_val,
                    clas_val,
                    grados_val
                ))

        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        self.lbl_page_info.configure(text=f"Página {self.current_page + 1} de {total_pages} ({self.total_count:,} registros)")
        
        self.btn_prev.configure(state="normal" if self.current_page > 0 else "disabled")
        self.btn_next.configure(state="normal" if (self.current_page + 1) < total_pages else "disabled")

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_data()

    def next_page(self):
        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        if (self.current_page + 1) < total_pages:
            self.current_page += 1
            self.load_data()

    def open_add_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Agregar Registro Sanitario INVIMA")
        modal.geometry("500x520")
        modal.resizable(False, False)
        modal.transient(self.winfo_toplevel())
        modal.grab_set()

        ctk.CTkLabel(modal, text="Nuevo Registro Certificado INVIMA", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)

        form = ctk.CTkFrame(modal, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=30, pady=10)

        fields = [
            ("Registro Sanitario *", "reg_entry", "Ej: INVIMA 2024L-0013890"),
            ("Código Único INVIMA", "cod_entry", "Ej: 202401928"),
            ("Nombre Bebida Certificada *", "nom_entry", "Ej: Aguardiente Antioqueño"),
            ("Marca", "mar_entry", "Ej: Antioqueño"),
            ("Clasificación", "clas_entry", "Ej: Aguardiente"),
            ("Grados de Alcohol (°)", "grad_entry", "Ej: 29.0")
        ]
        entries = {}

        for idx, (label_text, var_name, placeholder) in enumerate(fields):
            ctk.CTkLabel(form, text=label_text, font=ctk.CTkFont(size=12)).grid(row=idx, column=0, padx=10, pady=6, sticky="w")
            e = ctk.CTkEntry(form, placeholder_text=placeholder, width=260)
            e.grid(row=idx, column=1, padx=10, pady=6)
            entries[var_name] = e

        def save():
            reg = entries["reg_entry"].get().strip()
            nom = entries["nom_entry"].get().strip()
            if not reg or not nom:
                messagebox.showerror("Error", "El Registro Sanitario y el Nombre de la Bebida son obligatorios.")
                return
            
            database.add_invima_certificado(
                registro_sanitario=reg,
                codigo_unico=entries["cod_entry"].get().strip(),
                nombre=nom,
                marca=entries["mar_entry"].get().strip(),
                clasificacion=entries["clas_entry"].get().strip(),
                grados_alcohol=entries["grad_entry"].get().strip()
            )
            messagebox.showinfo("Éxito", f"Registro '{reg}' agregado exitosamente al catálogo.")
            modal.destroy()
            self.load_data()

        ctk.CTkButton(modal, text="Guardar Registro", fg_color="#2563eb", hover_color="#1d4ed8", font=ctk.CTkFont(weight="bold"), command=save).pack(pady=20)

    def export_data(self):
        search_term = self.search_entry.get()
        df, _ = database.get_invima_certificados(search_term=search_term, limit=50000, offset=0)
        export_dataframe_dialog(df, default_filename="catalogo_nacional_invima")


# ==========================================
# 6. Análisis Estadístico
# ==========================================
class AnalysisFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="Análisis Estadístico de Precios Normalizados", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 0), sticky="w")

        self.fecha_inicio = None
        self.fecha_fin = None

        self.filters_container = ctk.CTkFrame(self, fg_color="#1f2937", corner_radius=8)
        self.filters_container.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        row1 = ctk.CTkFrame(self.filters_container, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(row1, text="Comercio:").pack(side="left", padx=2)
        self.fuente_var = ctk.StringVar(value="Todas")
        self.fuente_combo = ctk.CTkComboBox(row1, variable=self.fuente_var, command=self.update_data, width=110)
        self.fuente_combo.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Tipo:").pack(side="left", padx=(8, 2))
        self.tipo_var = ctk.StringVar(value="Todos")
        self.tipo_combo = ctk.CTkComboBox(row1, variable=self.tipo_var, values=["Todos", "Alcohol", "Tabaco"], command=self.update_data, width=100)
        self.tipo_combo.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Subcategoría:").pack(side="left", padx=(8, 2))
        self.subcat_var = ctk.StringVar(value="Todas")
        self.subcat_combo = ctk.CTkComboBox(row1, variable=self.subcat_var, command=self.update_data, width=130)
        self.subcat_combo.pack(side="left", padx=4)

        self.btn_range = ctk.CTkButton(row1, text="Rango Fechas", fg_color="#374151", hover_color="#4b5563", width=100, command=self.open_date_modal)
        self.btn_range.pack(side="left", padx=8)

        self.lbl_range_info = ctk.CTkLabel(row1, text="Todas las fechas", text_color="#9ca3af", font=ctk.CTkFont(size=11, slant="italic"))
        self.lbl_range_info.pack(side="left", padx=2)

        self.plot_type_var = ctk.StringVar(value="Resumen de Métricas")
        self.plot_combo = ctk.CTkComboBox(row1, variable=self.plot_type_var, values=[], command=self.update_plot, width=230)
        self.plot_combo.pack(side="right", padx=5)

        self.content_frame = ctk.CTkScrollableFrame(self)
        self.content_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.df = pd.DataFrame()
        self.update_plot_options()

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

    def update_plot_options(self):
        options = [
            "Resumen de Métricas",
            "Marcas Más Vendidas",
            "Histograma de Precios",
            "Precio vs Grados de Alcohol",
            "Boxplot de Atípicos",
            "Distribución de Descuentos",
            "Top 10 Mayores Descuentos",
            "Comparativa de Precios por Marca"
        ]
        self.plot_combo.configure(values=options)

    def load_filters(self):
        sources = ["Todas"] + database.get_available_sources()
        subcats = database.get_available_subcategories()
        self.fuente_combo.configure(values=sources)
        self.subcat_combo.configure(values=subcats)
        self.update_data()

    def update_data(self, *args):
        fuente = self.fuente_var.get()
        tipo = self.tipo_var.get()
        subcat = self.subcat_var.get()

        self.df = database.get_normalized_data_as_dataframe(
            fuente=fuente,
            tipo=tipo,
            subcategoria=subcat,
            fecha_inicio=self.fecha_inicio,
            fecha_fin=self.fecha_fin,
            ignore_zero_prices=True
        )
        self.update_plot()

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def update_plot(self, *args):
        self.clear_content()
        if self.df is None or self.df.empty:
            ctk.CTkLabel(self.content_frame, text="No hay datos disponibles para mostrar con los filtros actuales.", font=ctk.CTkFont(size=16)).pack(pady=50)
            return

        plot_type = self.plot_type_var.get()
        if plot_type == "Resumen de Métricas":
            self.render_metrics()
            return

        plt.close('all')
        fig, ax = plt.subplots(figsize=(10, 5))

        if plot_type == "Marcas Más Vendidas":
            counts = self.df['marca_estandar'].value_counts().head(10)
            counts.plot(kind='bar', ax=ax, color='#2563eb')
            ax.set_title("Top 10 Marcas Estándar")
            ax.set_ylabel("Cantidad de Registros")
            plt.xticks(rotation=45, ha='right')

        elif plot_type == "Histograma de Precios":
            prices = self.df['precio_final'].dropna()
            ax.hist(prices, bins=40, color='#10b981', edgecolor='black')
            ax.set_title("Distribución de Precios (Precios > 0)")
            ax.set_xlabel("Precio (COP)")
            ax.set_ylabel("Frecuencia")
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))

        elif plot_type == "Precio vs Grados de Alcohol":
            df_clean = self.df.dropna(subset=['precio_final', 'grados_alcohol_estandar'])
            df_clean['grados_num'] = pd.to_numeric(df_clean['grados_alcohol_estandar'].astype(str).str.replace('%', '').str.strip(), errors='coerce')
            df_clean = df_clean.dropna(subset=['grados_num'])
            ax.scatter(df_clean['grados_num'], df_clean['precio_final'], alpha=0.5, c='#f59e0b')
            ax.set_title("Precio vs % de Alcohol")
            ax.set_xlabel("% de Alcohol")
            ax.set_ylabel("Precio (COP)")
            ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))

        elif plot_type == "Boxplot de Atípicos":
            prices = self.df['precio_final'].dropna()
            ax.boxplot(prices, vert=False, patch_artist=True, flierprops=dict(marker='o', markerfacecolor='red', markersize=4, alpha=0.5))
            ax.set_title("Detección de Valores Atípicos en Precios")
            ax.set_xlabel("Precio (COP)")
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))

        elif plot_type == "Distribución de Descuentos":
            df_desc = self.df.dropna(subset=['descuento'])
            df_desc['desc_num'] = pd.to_numeric(df_desc['descuento'].astype(str).str.replace('%', '').str.strip(), errors='coerce')
            df_desc = df_desc[df_desc['desc_num'] > 0]
            ax.hist(df_desc['desc_num'], bins=20, color='#8b5cf6', edgecolor='black')
            ax.set_title("Frecuencia de Descuentos (%)")
            ax.set_xlabel("Descuento (%)")

        elif plot_type == "Top 10 Mayores Descuentos":
            df_desc = self.df.copy()
            df_desc['desc_num'] = pd.to_numeric(df_desc['descuento'].astype(str).str.replace('%', '').str.strip(), errors='coerce')
            df_desc = df_desc.dropna(subset=['desc_num']).sort_values(by='desc_num', ascending=False).head(10)
            names = df_desc['nombre'].str[:25] + "..."
            ax.barh(names, df_desc['desc_num'], color='#ef4444')
            ax.set_title("Top 10 Productos con Mayor Descuento")
            ax.invert_yaxis()

        elif plot_type == "Comparativa de Precios por Marca":
            top_marcas = self.df['marca_estandar'].value_counts().head(5).index
            df_top = self.df[self.df['marca_estandar'].isin(top_marcas)]
            sns.boxplot(data=df_top, x='marca_estandar', y='precio_final', ax=ax, palette="Blues", showfliers=False)
            ax.set_title("Precios por Marca (Top 5)")
            ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.content_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, pady=20)

    def render_metrics(self):
        df = self.df
        total = len(df)
        precio_prom = df['precio_final'].mean()
        precio_med = df['precio_final'].median()

        try:
            prod_caro = df.loc[df['precio_final'].idxmax()]
            txt_caro = f"{prod_caro['nombre']} (${prod_caro['precio_final']/1000:,.0f}K)"
        except:
            txt_caro = "N/A"

        try:
            prod_barato = df.loc[df['precio_final'].idxmin()]
            txt_barato = f"{prod_barato['nombre']} (${prod_barato['precio_final']/1000:,.0f}K)"
        except:
            txt_barato = "N/A"

        def create_card(parent, title, value, subtitle=""):
            frame = ctk.CTkFrame(parent, fg_color="#1f2937", corner_radius=10)
            ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=13, weight="bold"), text_color="#9ca3af").pack(pady=(15,5), padx=10)
            ctk.CTkLabel(frame, text=value, font=ctk.CTkFont(size=22, weight="bold"), text_color="#f9fafb").pack(pady=5, padx=10)
            if subtitle:
                ctk.CTkLabel(frame, text=subtitle, font=ctk.CTkFont(size=11), text_color="#6b7280", wraplength=280).pack(pady=(0,15), padx=10)
            return frame

        grid = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        grid.pack(fill="x", pady=20, padx=20)
        grid.grid_columnconfigure((0,1,2), weight=1)

        create_card(grid, "Total Lecturas Normalizadas", f"{total:,}").grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        create_card(grid, "Precio Promedio", f"${precio_prom/1000:,.1f}K COP").grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        create_card(grid, "Mediana de Precio", f"${precio_med/1000:,.1f}K COP").grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        
        create_card(grid, "Producto de Mayor Precio", txt_caro.split(" ($")[0][:30]+"...", txt_caro).grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        create_card(grid, "Producto de Menor Precio", txt_barato.split(" ($")[0][:30]+"...", txt_barato).grid(row=1, column=2, padx=10, pady=10, sticky="nsew")


# ==========================================
# 7. Depuración IA (DeepSeek)
# ==========================================
class DeepSeekFilterFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="Depuración con Inteligencia Artificial (DeepSeek)", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.controls = ctk.CTkFrame(self, fg_color="transparent")
        self.controls.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self.controls, text="API Key DeepSeek:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0,5))
        self.api_entry = ctk.CTkEntry(self.controls, placeholder_text="Tu DeepSeek API Key", width=220, show="*")
        env_key = os.getenv("DEEPSEEK_API_KEY")
        if env_key:
            self.api_entry.insert(0, env_key)
        self.api_entry.pack(side="left", padx=(0, 10))

        self.btn_detect = ctk.CTkButton(self.controls, text="Buscar Atípicos", fg_color="#2563eb", hover_color="#1d4ed8", font=ctk.CTkFont(weight="bold"), command=self.detect)
        self.btn_detect.pack(side="left", padx=(0, 10))

        self.btn_remove = ctk.CTkButton(self.controls, text="Eliminar Seleccionados", fg_color="#ef4444", hover_color="#dc2626", font=ctk.CTkFont(weight="bold"), command=self.remove_selected)
        self.btn_remove.pack(side="right")
        
        self.status_label = ctk.CTkLabel(self.controls, text="", text_color="#f59e0b", font=ctk.CTkFont(weight="bold"))
        self.status_label.pack(side="right", padx=20)

        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(self.tree_frame, columns=("DB_ID", "Nombre", "Marca", "Tipo"), show="headings")
        self.tree.heading("DB_ID", text="ID Maestro")
        self.tree.heading("Nombre", text="Nombre Estándar")
        self.tree.heading("Marca", text="Marca Estándar")
        self.tree.heading("Tipo", text="Tipo")
        
        self.tree.column("DB_ID", width=140, anchor="center")
        self.tree.column("Nombre", width=460)
        self.tree.column("Marca", width=140, anchor="center")
        self.tree.column("Tipo", width=110, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.false_positives = [] 

    def load_filters(self):
        pass

    def detect(self):
        api_key = self.api_entry.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Ingresa tu API Key de DeepSeek.")
            return

        self.btn_detect.configure(state="disabled")
        threading.Thread(target=self._run_deepseek, args=(api_key,), daemon=True).start()

    def _run_deepseek(self, api_key):
        def set_status(text):
            self.after(0, lambda: self.status_label.configure(text=text))
            
        try:
            set_status("Consultando Maestro de Productos...")
            df = database.get_maestro_products()
            if 'deleted' in df.columns:
                df = df[df['deleted'] == 0]
                
            if df.empty:
                self.after(0, lambda: messagebox.showinfo("Info", "El Maestro de Productos está vacío."))
                set_status("")
                return

            df.rename(columns={'codigo_universal': 'id', 'nombre_estandar': 'nombre', 'marca_estandar': 'marca', 'tipo_producto_estandar': 'tipo'}, inplace=True)
            df = df.drop_duplicates(subset=['id'])

            try:
                from openai import OpenAI
            except ImportError:
                self.after(0, lambda: messagebox.showerror("Error", "Falta librería 'openai'"))
                set_status("")
                return
                
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
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
                        response = client.chat.completions.create(
                            model='deepseek-v4-flash',
                            messages=[
                                {"role": "system", "content": "Return pure JSON array."},
                                {"role": "user", "content": prompt + "\n\n" + json.dumps(chunk_data, ensure_ascii=False)}
                            ],
                            temperature=0.0
                        )
                        text = response.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
                        ids = json.loads(text)
                        if isinstance(ids, list):
                            fp_db_ids.extend([str(x) for x in ids])
                        break
                    except Exception as loop_e:
                        if attempt < max_retries - 1:
                            time.sleep(5)
                            
                time.sleep(0.3)

            self.false_positives = df[df['id'].isin(fp_db_ids)].to_dict('records')
            set_status("Análisis completado")
            self.after(0, self._update_tree)

        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Error IA general", str(e)))
            set_status("")
        finally:
            self.after(0, lambda: self.btn_detect.configure(state="normal"))

    def _update_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        all_items = []
        for p in self.false_positives:
            marca = p['marca'] if pd.notnull(p['marca']) else "N/A"
            tipo = p['tipo'] if pd.notnull(p['tipo']) else "N/A"
            item = self.tree.insert("", "end", values=(p['id'], p['nombre'], marca, tipo))
            all_items.append(item)
            
        if all_items:
            self.tree.selection_set(all_items)
            messagebox.showinfo("Búsqueda Lista", f"Se encontraron {len(all_items)} posibles falsos positivos.")

    def remove_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "No hay elementos seleccionados.")
            return
            
        count = 0
        for s in selected:
            item = self.tree.item(s)
            db_id = item["values"][0]
            database.delete_false_positive(db_id)
            self.tree.delete(s)
            count += 1
            
        messagebox.showinfo("Éxito", f"Se eliminaron {count} registros de la base de datos.")


# ==========================================
# 8. Comparativas de Mercado
# ==========================================
class CompareFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="Comparativas de Mercado entre Comercios", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.filters_container = ctk.CTkFrame(self, fg_color="#1f2937", corner_radius=8)
        self.filters_container.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        row1 = ctk.CTkFrame(self.filters_container, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(row1, text="Tipo:").pack(side="left", padx=2)
        self.tipo_var = ctk.StringVar(value="Todos")
        self.tipo_combo = ctk.CTkComboBox(row1, variable=self.tipo_var, values=["Todos", "Alcohol", "Tabaco"], command=self.update_plot, width=100)
        self.tipo_combo.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Subcategoría:").pack(side="left", padx=(10, 2))
        self.subcat_var = ctk.StringVar(value="Todas")
        self.subcat_combo = ctk.CTkComboBox(row1, variable=self.subcat_var, command=self.update_plot, width=140)
        self.subcat_combo.pack(side="left", padx=4)

        self.plot_type_var = ctk.StringVar(value="Buscador Cruzado (Producto)")
        self.plot_combo = ctk.CTkComboBox(row1, variable=self.plot_type_var, values=[
            "Buscador Cruzado (Producto)",
            "Evolución Temporal del Mercado"
        ], command=self.update_plot, width=220)
        self.plot_combo.pack(side="left", padx=10)

        self.search_var = ctk.StringVar(value="Haz clic en Elegir Producto")
        self.lbl_selected = ctk.CTkLabel(row1, textvariable=self.search_var, font=ctk.CTkFont(size=12, slant="italic"))
        self.lbl_selected.pack(side="left", padx=5)

        self.btn_export = ctk.CTkButton(row1, text="Exportar", fg_color="#10b981", hover_color="#059669", width=90, command=self.export_data)
        self.btn_export.pack(side="right", padx=5)

        self.btn_search = ctk.CTkButton(row1, text="Elegir Producto", command=self.open_product_modal, width=130, fg_color="#2563eb", hover_color="#1d4ed8")
        self.btn_search.pack(side="right", padx=5)

        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.raw_df = pd.DataFrame()
        self.unique_products = []

    def load_filters(self):
        subcats = database.get_available_subcategories()
        self.subcat_combo.configure(values=subcats)
        self.load_data()

    def load_data(self):
        tipo = self.tipo_var.get()
        subcat = self.subcat_var.get()
        self.raw_df = database.get_normalized_data_as_dataframe(
            tipo=tipo, 
            subcategoria=subcat, 
            ignore_zero_prices=True
        )
        if not self.raw_df.empty:
            self.unique_products = sorted(self.raw_df['nombre'].dropna().unique().tolist())
        else:
            self.unique_products = []
        self.update_plot()

    def open_product_modal(self):
        if not self.unique_products:
            messagebox.showwarning("Vacío", "No hay productos disponibles para los filtros seleccionados.")
            return
            
        modal = ctk.CTkToplevel(self)
        modal.title("Seleccionar Producto Estándar")
        modal.geometry("520x600")
        modal.transient(self.winfo_toplevel())
        modal.grab_set()

        ctk.CTkLabel(modal, text="Buscar Producto Estándar", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)
        
        search_entry = ctk.CTkEntry(modal, placeholder_text="Escribe para filtrar...", width=320)
        search_entry.pack(pady=5)
        
        listbox_frame = ctk.CTkFrame(modal)
        listbox_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, font=("Arial", 11), bg="#1f2937", fg="white", selectbackground="#2563eb")
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def populate_list(filter_text=""):
            listbox.delete(0, tk.END)
            for p in self.unique_products:
                if filter_text.lower() in p.lower():
                    listbox.insert(tk.END, p)
                    
        populate_list()
        
        def on_key_release(event):
            populate_list(search_entry.get())
            
        search_entry.bind("<KeyRelease>", on_key_release)
        search_entry.focus()
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                selected_item = listbox.get(selection[0])
                self.search_var.set(selected_item)
                self.plot_type_var.set("Buscador Cruzado (Producto)")
                self.update_plot()
                modal.destroy()
                
        listbox.bind("<Double-Button-1>", lambda e: on_select())
        ctk.CTkButton(modal, text="Confirmar Selección", fg_color="#2563eb", command=on_select).pack(pady=15)

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def update_plot(self, *args):
        self.clear_content()
        if self.raw_df.empty:
            ctk.CTkLabel(self.content_frame, text="No hay datos en la base de datos para los filtros seleccionados.", font=ctk.CTkFont(size=16)).pack(pady=50)
            return

        plot_type = self.plot_type_var.get()
        plt.close('all')
        fig, ax = plt.subplots(figsize=(10, 5))

        if plot_type == "Buscador Cruzado (Producto)":
            query = self.search_var.get().strip()
            if query == "Haz clic en Elegir Producto" or not query:
                ax.text(0.5, 0.5, "Selecciona un producto usando el botón de arriba.", ha='center', va='center')
            else:
                df_filtered = self.raw_df[self.raw_df['nombre'] == query]
                if df_filtered.empty:
                    ax.text(0.5, 0.5, f"No se encontró '{query}' con los filtros actuales.", ha='center', va='center')
                else:
                    sns.boxplot(data=df_filtered, x='fuente', y='precio_final', ax=ax, palette="Blues", showfliers=False)
                    ax.set_title(f"Comparativa de Precios entre Comercios: '{query}'")
                    ax.set_xlabel("Comercio")
                    ax.set_ylabel("Precio (COP)")
                    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))
                    
        elif plot_type == "Evolución Temporal del Mercado":
            if 'fecha_extraccion' in self.raw_df.columns:
                df_time = self.raw_df.groupby(['fecha_extraccion', 'fuente'])['precio_final'].mean().reset_index()
                if not df_time.empty:
                    sns.lineplot(data=df_time, x='fecha_extraccion', y='precio_final', hue='fuente', marker='o', linewidth=2, ax=ax)
                    ax.set_title("Evolución Temporal del Precio Promedio por Comercio")
                    ax.set_xlabel("Fecha de Extracción")
                    ax.set_ylabel("Precio Promedio (COP)")
                    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))
                    plt.xticks(rotation=45)

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.content_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def export_data(self):
        if hasattr(self, 'raw_df'):
            export_dataframe_dialog(self.raw_df, default_filename="comparativa_mercado")


# ==========================================
# 9. Asignación Mapeo MDM
# ==========================================
class NormalizationFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure((0, 1), weight=1)

        self.label = ctk.CTkLabel(self, text="Asignación y Mapeo MDM (Productos Maestros)", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="w")

        self.controls = ctk.CTkFrame(self, fg_color="#1f2937", corner_radius=8)
        self.controls.grid(row=1, column=0, columnspan=2, padx=20, pady=5, sticky="ew")

        row1 = ctk.CTkFrame(self.controls, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(row1, text="Comercio:").pack(side="left", padx=2)
        self.fuente_var = ctk.StringVar(value="Todas")
        self.fuente_combo = ctk.CTkComboBox(row1, variable=self.fuente_var, command=self.load_data, width=110)
        self.fuente_combo.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Tipo:").pack(side="left", padx=(8, 2))
        self.tipo_var = ctk.StringVar(value="Todos")
        self.tipo_combo = ctk.CTkComboBox(row1, variable=self.tipo_var, values=["Todos", "Alcohol", "Tabaco"], command=self.load_data, width=100)
        self.tipo_combo.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Buscar Crudos:").pack(side="left", padx=(8, 2))
        self.search_entry = ctk.CTkEntry(row1, placeholder_text="Nombre o marca de crudo...", width=200)
        self.search_entry.pack(side="left", padx=4)
        self.search_entry.bind("<Return>", lambda e: self.load_data())

        self.btn_refresh = ctk.CTkButton(row1, text="Buscar / Refrescar", command=self.load_data)
        self.btn_refresh.pack(side="left", padx=4)

        self.btn_export = ctk.CTkButton(row1, text="Exportar Sin Mapear", fg_color="#10b981", hover_color="#059669", command=self.export_data)
        self.btn_export.pack(side="right", padx=4)

        self.btn_etl = ctk.CTkButton(row1, text="Ejecutar ETL", fg_color="#2563eb", hover_color="#1d4ed8", command=self.run_etl)
        self.btn_etl.pack(side="right", padx=4)

        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=2, column=0, padx=(20, 10), pady=(0, 20), sticky="nsew")
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.left_frame, text="Productos Sin Mapear (Crudos)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=5)
        self.tree_raw = ttk.Treeview(self.left_frame, columns=("Comercio", "ID", "Nombre", "Marca"), show="headings")
        self.tree_raw.heading("Comercio", text="Comercio")
        self.tree_raw.heading("ID", text="ID")
        self.tree_raw.heading("Nombre", text="Nombre")
        self.tree_raw.heading("Marca", text="Marca")
        self.tree_raw.column("Comercio", width=80)
        self.tree_raw.column("ID", width=80)
        self.tree_raw.column("Nombre", width=220)
        self.tree_raw.column("Marca", width=100)
        self.tree_raw.grid(row=1, column=0, sticky="nsew")
        
        scrollbar_raw = ttk.Scrollbar(self.left_frame, orient="vertical", command=self.tree_raw.yview)
        self.tree_raw.configure(yscroll=scrollbar_raw.set)
        scrollbar_raw.grid(row=1, column=1, sticky="ns")

        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=2, column=1, padx=(10, 20), pady=(0, 20), sticky="nsew")
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.right_frame, text="Maestro de Productos (Diccionario)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=5)
        self.tree_master = ttk.Treeview(self.right_frame, columns=("Código", "Nombre", "Marca"), show="headings")
        self.tree_master.heading("Código", text="Código")
        self.tree_master.heading("Nombre", text="Nombre Estándar")
        self.tree_master.heading("Marca", text="Marca")
        self.tree_master.column("Código", width=100)
        self.tree_master.column("Nombre", width=240)
        self.tree_master.column("Marca", width=120)
        self.tree_master.grid(row=1, column=0, sticky="nsew")
        
        scrollbar_master = ttk.Scrollbar(self.right_frame, orient="vertical", command=self.tree_master.yview)
        self.tree_master.configure(yscroll=scrollbar_master.set)
        scrollbar_master.grid(row=1, column=1, sticky="ns")

        self.bottom_controls = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_controls.grid(row=3, column=0, columnspan=2, padx=20, pady=(0,20), sticky="ew")

        self.btn_link = ctk.CTkButton(self.bottom_controls, text="Vincular Seleccionados al Maestro", font=ctk.CTkFont(weight="bold"), command=self.link_products)
        self.btn_link.pack(side="left", padx=5)

        self.df_raw = pd.DataFrame()
        self.df_master = pd.DataFrame()

    def load_filters(self):
        sources = ["Todas"] + database.get_available_sources()
        self.fuente_combo.configure(values=sources)
        self.load_data()

    def load_data(self):
        for i in self.tree_raw.get_children(): self.tree_raw.delete(i)
        for i in self.tree_master.get_children(): self.tree_master.delete(i)

        fuente = self.fuente_var.get()
        tipo = self.tipo_var.get()
        search_term = self.search_entry.get()

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
        self.load_data()

    def run_etl(self):
        try:
            database.run_normalization_etl()
            messagebox.showinfo("Éxito", "Proceso ETL de normalización completado con éxito.")
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al ejecutar ETL: {e}")

    def export_data(self):
        if hasattr(self, 'df_raw'):
            export_dataframe_dialog(self.df_raw, default_filename="productos_sin_mapear")

if __name__ == "__main__":
    app = App()
    app.mainloop()
