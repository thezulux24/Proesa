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
import matplotlib.dates as mdates
import seaborn as sns
import matplotlib.ticker as ticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
from PIL import Image
from dotenv import load_dotenv

import database

load_dotenv()

# Modo inicial claro
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

def configure_treeview_style(mode="Light"):
    style = ttk.Style()
    style.theme_use("clam")
    
    if mode == "Light":
        bg_color = "#ffffff"
        fg_color = "#0f172a"
        heading_bg = "#e2e8f0"
        heading_fg = "#0f172a"
        select_bg = "#2563eb"
        select_fg = "#ffffff"
        border_color = "#cbd5e1"
    else:
        bg_color = "#1f2937"
        fg_color = "#f9fafb"
        heading_bg = "#374151"
        heading_fg = "#f9fafb"
        select_bg = "#2563eb"
        select_fg = "#ffffff"
        border_color = "#374151"

    style.configure("Treeview",
                    background=bg_color,
                    foreground=fg_color,
                    fieldbackground=bg_color,
                    rowheight=26,
                    font=("Segoe UI", 10),
                    borderwidth=0)
    
    style.configure("Treeview.Heading",
                    background=heading_bg,
                    foreground=heading_fg,
                    font=("Segoe UI", 10, "bold"),
                    borderwidth=1,
                    relief="flat")
    
    style.map("Treeview",
              background=[("selected", select_bg)],
              foreground=[("selected", select_fg)])
    
    style.map("Treeview.Heading",
              background=[("active", select_bg)],
              foreground=[("active", "#ffffff")])


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


class DataSuiteApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        db = database.DataSuiteDB()
        db.init_db()
        
        self.title("PROESA - Suite Data & Mercado (Alcohol y Tabaco)")
        self.geometry("1420x920")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Cargar estilos de Treeview iniciales (modo Claro)
        configure_treeview_style("Light")

        self.sidebar_frame = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=("#e2e8f0", "#111827"))
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)

        # Cargar e insertar Logo oficial
        logo_path = os.path.join(os.path.dirname(__file__), "logo.webp")
        if os.path.exists(logo_path):
            try:
                pil_logo = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(195, 75))
                self.logo_label = ctk.CTkLabel(self.sidebar_frame, image=self.logo_image, text="")
            except Exception:
                self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Suite Data PROESA", font=ctk.CTkFont(size=20, weight="bold"))
        else:
            self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Suite Data PROESA", font=ctk.CTkFont(size=20, weight="bold"))
            
        self.logo_label.grid(row=0, column=0, padx=15, pady=(20, 15))

        btn_kwargs = {
            "font": ctk.CTkFont(size=14),
            "height": 42,
            "anchor": "w",
            "fg_color": "transparent",
            "text_color": ("#1e293b", "#d1d5db"),
            "hover_color": ("#cbd5e1", "#1f2937")
        }

        self.btn_extraccion = ctk.CTkButton(self.sidebar_frame, text=" Módulo Extracción", command=self.show_extraccion, **btn_kwargs)
        self.btn_extraccion.grid(row=1, column=0, padx=15, pady=4, sticky="ew")

        self.btn_viewer = ctk.CTkButton(self.sidebar_frame, text=" Visor Datos Crudos", command=self.show_viewer, **btn_kwargs)
        self.btn_viewer.grid(row=2, column=0, padx=15, pady=4, sticky="ew")

        self.btn_norm_viewer = ctk.CTkButton(self.sidebar_frame, text=" Visor Normalizado", command=self.show_norm_viewer, **btn_kwargs)
        self.btn_norm_viewer.grid(row=3, column=0, padx=15, pady=4, sticky="ew")

        self.btn_analysis = ctk.CTkButton(self.sidebar_frame, text=" Análisis & Mercado", command=self.show_analysis, **btn_kwargs)
        self.btn_analysis.grid(row=4, column=0, padx=15, pady=4, sticky="ew")

        self.btn_standardization = ctk.CTkButton(self.sidebar_frame, text=" Estandarización Data", command=self.show_standardization, **btn_kwargs)
        self.btn_standardization.grid(row=5, column=0, padx=15, pady=4, sticky="ew")

        # Botón de Conmutación de Modo Claro / Oscuro
        self.switch_theme = ctk.CTkSwitch(
            self.sidebar_frame, 
            text="Modo Oscuro", 
            command=self.toggle_theme,
            font=ctk.CTkFont(size=13, weight="bold"),
            progress_color="#2563eb"
        )
        self.switch_theme.grid(row=7, column=0, padx=20, pady=(20, 25), sticky="s")

        # Frame instances
        self.frame_extraccion = ExtraccionFrame(self)
        self.frame_viewer = DataViewerFrame(self)
        self.frame_norm_viewer = NormalizedViewerFrame(self)
        self.frame_analysis = UnifiedAnalysisFrame(self)
        self.frame_standardization = UnifiedStandardizationFrame(self)

        self.show_norm_viewer()

    def toggle_theme(self):
        if self.switch_theme.get() == 1:
            ctk.set_appearance_mode("Dark")
            configure_treeview_style("Dark")
        else:
            ctk.set_appearance_mode("Light")
            configure_treeview_style("Light")
            
        if hasattr(self, 'frame_analysis'):
            self.frame_analysis.update_plot()

    def hide_all_frames(self):
        self.frame_extraccion.grid_forget()
        self.frame_viewer.grid_forget()
        self.frame_norm_viewer.grid_forget()
        self.frame_analysis.grid_forget()
        self.frame_standardization.grid_forget()

        for btn in [self.btn_extraccion, self.btn_viewer, self.btn_norm_viewer, self.btn_analysis,
                    self.btn_standardization]:
            btn.configure(fg_color="transparent", text_color=("#1e293b", "#d1d5db"))

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

    def show_standardization(self):
        self.hide_all_frames()
        self._activate_button(self.btn_standardization)
        self.frame_standardization.load_filters()
        self.frame_standardization.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)


# ==========================================
# 1. Extracción Frame
# ==========================================
class ExtraccionFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="Módulo de Extracción de Datos (Scrapers)", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.controls = ctk.CTkFrame(self, fg_color="transparent")
        self.controls.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self.controls, text="Seleccionar Comercio:").pack(side="left", padx=(0, 10))
        self.comercio_combo = ctk.CTkComboBox(self.controls, values=["Todos", "Éxito", "Carulla", "Jumbo", "Olímpica", "D1", "Makro", "Cañaveral"], width=150)
        self.comercio_combo.pack(side="left", padx=(0, 15))

        self.btn_run = ctk.CTkButton(self.controls, text="Iniciar Extracción", fg_color="#2563eb", hover_color="#1d4ed8", command=self.run_scraper)
        self.btn_run.pack(side="left", padx=(0, 10))

        self.log_text = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_text.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")

    def run_scraper(self):
        comercio = self.comercio_combo.get()
        self.log_text.delete("1.0", tk.END)
        self.log_text.insert(tk.END, f"Iniciando extracción para: {comercio}...\n\n")
        
        self.btn_run.configure(state="disabled")
        threading.Thread(target=self._execute_scraper, args=(comercio,), daemon=True).start()

    def _execute_scraper(self, comercio):
        try:
            cmd = ["python", "main.py"]
            if comercio != "Todos":
                cmd.extend(["--comercio", comercio.lower()])

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in process.stdout:
                self.after(0, self._append_log, line)
            process.wait()
            self.after(0, self._append_log, f"\nExtracción finalizada con código de salida: {process.returncode}\n")
        except Exception as e:
            self.after(0, self._append_log, f"\nError al ejecutar scraper: {e}\n")
        finally:
            self.after(0, lambda: self.btn_run.configure(state="normal"))

    def _append_log(self, text):
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)


# ==========================================
# 2. Visor de Datos Crudos (Histórico)
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


# ==========================================
# 3. Visor de Datos Normalizados (MDM)
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

        columns = ("Código", "Fuente", "Fecha", "Nombre Estándar", "Marca", "Categoría", "Descuento", "Volumen Estándar", "Precio Final", "Precio/Unidad", "Registro INVIMA")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")
        
        self.tree.heading("Código", text="Código Universal")
        self.tree.column("Código", width=105, anchor="center")
        self.tree.heading("Fuente", text="Fuente")
        self.tree.column("Fuente", width=85, anchor="center")
        self.tree.heading("Fecha", text="Fecha")
        self.tree.column("Fecha", width=85, anchor="center")
        self.tree.heading("Nombre Estándar", text="Nombre Estándar")
        self.tree.column("Nombre Estándar", width=250)
        self.tree.heading("Marca", text="Marca")
        self.tree.column("Marca", width=110)
        self.tree.heading("Categoría", text="Categoría")
        self.tree.column("Categoría", width=110)
        self.tree.heading("Descuento", text="Descuento")
        self.tree.column("Descuento", width=80, anchor="center")
        self.tree.heading("Volumen Estándar", text="Vol. Estándar")
        self.tree.column("Volumen Estándar", width=95, anchor="center")
        self.tree.heading("Precio Final", text="Precio Final")
        self.tree.column("Precio Final", width=95, anchor="e")
        self.tree.heading("Precio/Unidad", text="Precio/Unidad")
        self.tree.column("Precio/Unidad", width=110, anchor="center")
        self.tree.heading("Registro INVIMA", text="Registro INVIMA")
        self.tree.column("Registro INVIMA", width=150, anchor="center")

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
                vol_val = row.get('volumen_estandar', 'N/A') or 'N/A'
                pum_val = row.get('precio_unidad', 'N/A') or 'N/A'

                self.tree.insert("", "end", values=(
                    row.get('id', ''),
                    row.get('fuente', ''),
                    str(row.get('fecha_extraccion', '')),
                    row.get('nombre', ''),
                    row.get('marca_estandar', ''),
                    row.get('subcategoria_estandar', ''),
                    desc_val,
                    vol_val,
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


# ==========================================
# 4. Módulo Unificado de Análisis & Comparativas de Mercado
# ==========================================
class UnifiedAnalysisFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="Análisis Estadístico & Comparativas de Mercado", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 0), sticky="w")

        self.fecha_inicio = None
        self.fecha_fin = None
        self.selected_product = None

        self.filters_container = ctk.CTkFrame(self, fg_color=("#e2e8f0", "#1f2937"), corner_radius=8)
        self.filters_container.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        row1 = ctk.CTkFrame(self.filters_container, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(row1, text="Comercio:").pack(side="left", padx=2)
        self.fuente_var = ctk.StringVar(value="Todas")
        self.fuente_combo = ctk.CTkComboBox(row1, variable=self.fuente_var, command=self.update_data, width=110)
        self.fuente_combo.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Tipo:").pack(side="left", padx=(8, 2))
        self.tipo_var = ctk.StringVar(value="Todos")
        self.tipo_combo = ctk.CTkComboBox(row1, variable=self.tipo_var, values=["Todos", "Alcohol", "Tabaco"], command=self.update_data, width=95)
        self.tipo_combo.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Subcategoría:").pack(side="left", padx=(8, 2))
        self.subcat_var = ctk.StringVar(value="Todas")
        self.subcat_combo = ctk.CTkComboBox(row1, variable=self.subcat_var, command=self.update_data, width=130)
        self.subcat_combo.pack(side="left", padx=4)

        self.btn_range = ctk.CTkButton(row1, text="Rango Fechas", fg_color=("#cbd5e1", "#374151"), hover_color=("#94a3b8", "#4b5563"), text_color=("#0f172a", "#f9fafb"), width=100, command=self.open_date_modal)
        self.btn_range.pack(side="left", padx=6)

        self.lbl_range_info = ctk.CTkLabel(row1, text="Todas las fechas", text_color=("#64748b", "#9ca3af"), font=ctk.CTkFont(size=11, slant="italic"))
        self.lbl_range_info.pack(side="left", padx=2)

        self.btn_choose_prod = ctk.CTkButton(row1, text="Elegir Producto", fg_color="#2563eb", hover_color="#1d4ed8", width=120, command=self.open_product_modal)
        self.btn_choose_prod.pack(side="right", padx=4)

        self.plot_type_var = ctk.StringVar(value="Resumen de Métricas")
        self.plot_combo = ctk.CTkComboBox(row1, variable=self.plot_type_var, values=[
            "Resumen de Métricas",
            "Buscador Cruzado (Guerra de Precios)",
            "Evolución Temporal del Mercado",
            "Comparativa de Precio por Unidad ($/L)",
            "Marcas Más Frecuentes",
            "Histograma de Precios",
            "Distribución y Frecuencia de Descuentos (%)",
            "Top 10 Mayores Descuentos",
            "Precios por Marca (Boxplot)",
            "Precio vs % de Alcohol"
        ], command=self.update_plot, width=250)
        self.plot_combo.pack(side="right", padx=6)

        self.content_frame = ctk.CTkScrollableFrame(self)
        self.content_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.df = pd.DataFrame()
        self.unique_products = []

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
        if self.df is not None and not self.df.empty and 'nombre' in self.df.columns:
            self.unique_products = sorted(self.df['nombre'].dropna().unique().tolist())
        else:
            self.unique_products = []
        self.update_plot()

    def open_product_modal(self):
        if not self.unique_products:
            messagebox.showwarning("Vacío", "No hay productos disponibles para los filtros seleccionados.")
            return
            
        modal = ctk.CTkToplevel(self)
        modal.title("Seleccionar Producto Estándar")
        modal.geometry("540x600")
        modal.transient(self.winfo_toplevel())
        modal.grab_set()

        ctk.CTkLabel(modal, text="Buscar Producto para Guerra de Precios", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)
        
        search_entry = ctk.CTkEntry(modal, placeholder_text="Escribe para filtrar...", width=340)
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
        
        search_entry.bind("<KeyRelease>", lambda e: populate_list(search_entry.get()))
        search_entry.focus()
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                selected_item = listbox.get(selection[0])
                self.selected_product = selected_item
                self.plot_type_var.set("Buscador Cruzado (Guerra de Precios)")
                self.update_plot()
                modal.destroy()
                
        listbox.bind("<Double-Button-1>", lambda e: on_select())
        ctk.CTkButton(modal, text="Confirmar Selección", fg_color="#2563eb", hover_color="#1d4ed8", command=on_select).pack(pady=15)

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
        
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Light":
            plt.style.use('default')
            fig_bg = '#ffffff'
            ax_bg = '#f8fafc'
            text_color = '#0f172a'
            strip_color = '#0284c7'
        else:
            plt.style.use('dark_background')
            fig_bg = '#111827'
            ax_bg = '#1f2937'
            text_color = 'white'
            strip_color = '#38bdf8'

        fig, ax = plt.subplots(figsize=(10.5, 5.5))
        fig.patch.set_facecolor(fig_bg)
        ax.set_facecolor(ax_bg)

        if plot_type == "Buscador Cruzado (Guerra de Precios)":
            if not self.selected_product:
                if self.unique_products:
                    self.selected_product = self.unique_products[0]
            
            if self.selected_product:
                df_filtered = self.df[self.df['nombre'] == self.selected_product]
                if df_filtered.empty:
                    ax.text(0.5, 0.5, f"No se encontraron lecturas para:\n'{self.selected_product}'", ha='center', va='center', color=text_color, fontsize=12)
                else:
                    sns.boxplot(data=df_filtered, x='fuente', y='precio_final', hue='fuente', legend=False, ax=ax, palette="Blues", showfliers=False, width=0.4)
                    sns.stripplot(data=df_filtered, x='fuente', y='precio_final', ax=ax, color=strip_color, size=8, jitter=0.2, alpha=0.9)
                    ax.set_title(f"Guerra de Precios entre Comercios:\n'{self.selected_product}'", fontsize=14, fontweight='bold', color=text_color, pad=12)
                    ax.set_xlabel("Comercio", color=text_color, fontsize=11)
                    ax.set_ylabel("Precio (COP)", color=text_color, fontsize=11)
                    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))
                    ax.tick_params(colors=text_color)
            else:
                ax.text(0.5, 0.5, "Haz clic en 'Elegir Producto' para seleccionar un artículo.", ha='center', va='center', color=text_color, fontsize=12)

        elif plot_type == "Evolución Temporal del Mercado":
            if 'fecha_extraccion' in self.df.columns:
                df_time = self.df.copy()
                df_time['fecha_dt'] = pd.to_datetime(df_time['fecha_extraccion'], errors='coerce')
                df_time = df_time.dropna(subset=['fecha_dt'])
                df_time = df_time.groupby(['fecha_dt', 'fuente'])['precio_final'].mean().reset_index().sort_values(by='fecha_dt')
                
                if not df_time.empty:
                    sns.lineplot(data=df_time, x='fecha_dt', y='precio_final', hue='fuente', marker='o', linewidth=2.5, ax=ax, markersize=7)
                    ax.set_title("Evolución Temporal del Precio Promedio por Comercio", fontsize=14, fontweight='bold', color=text_color, pad=12)
                    ax.set_xlabel("Fecha de Extracción", color=text_color, fontsize=11)
                    ax.set_ylabel("Precio Promedio (COP)", color=text_color, fontsize=11)
                    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                    plt.xticks(rotation=35, ha='right')
                    ax.tick_params(colors=text_color)

        elif plot_type == "Comparativa de Precio por Unidad ($/L)":
            df_pum = self.df.dropna(subset=['precio_unidad']).copy()
            if not df_pum.empty:
                counts = df_pum['precio_unidad'].value_counts().head(10)
                counts.plot(kind='barh', ax=ax, color='#10b981')
                ax.set_title("Top Rango de Precios por Unidad / Medida (PUM)", fontsize=14, fontweight='bold', color=text_color, pad=12)
                ax.set_xlabel("Frecuencia de Lecturas", color=text_color, fontsize=11)
                ax.set_ylabel("Precio por Unidad ($ / PUM)", color=text_color, fontsize=11)
                ax.invert_yaxis()
                ax.tick_params(colors=text_color)
            else:
                ax.text(0.5, 0.5, "No hay datos de Precio por Unidad disponibles para los filtros seleccionados.", ha='center', va='center', color=text_color, fontsize=12)

        elif plot_type == "Marcas Más Frecuentes":
            counts = self.df['marca_estandar'].value_counts().head(10)
            counts.plot(kind='bar', ax=ax, color='#2563eb')
            ax.set_title("Top 10 Marcas Estándar con Mayor Presencia", fontsize=14, fontweight='bold', color=text_color, pad=12)
            ax.set_xlabel("Marca Estándar", color=text_color, fontsize=11)
            ax.set_ylabel("Cantidad de Registros", color=text_color, fontsize=11)
            plt.xticks(rotation=35, ha='right')
            ax.tick_params(colors=text_color)

        elif plot_type == "Histograma de Precios":
            prices = self.df['precio_final'].dropna()
            prices = prices[prices > 0]
            ax.hist(prices, bins=35, color='#059669', edgecolor='black', alpha=0.85)
            ax.set_title("Distribución General de Precios Finales (Precios > $0)", fontsize=14, fontweight='bold', color=text_color, pad=12)
            ax.set_xlabel("Precio Final (COP)", color=text_color, fontsize=11)
            ax.set_ylabel("Frecuencia (Cantidad de Productos)", color=text_color, fontsize=11)
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))
            ax.tick_params(colors=text_color)

        elif plot_type == "Precio vs % de Alcohol":
            df_clean = self.df.dropna(subset=['precio_final', 'grados_alcohol_estandar']).copy()
            df_clean['grados_num'] = pd.to_numeric(df_clean['grados_alcohol_estandar'].astype(str).str.replace('%', '').str.strip(), errors='coerce')
            df_clean = df_clean.dropna(subset=['grados_num'])
            df_clean = df_clean[df_clean['precio_final'] > 0]
            
            if not df_clean.empty:
                ax.scatter(df_clean['grados_num'], df_clean['precio_final'], alpha=0.6, c='#d97706', edgecolors='black', s=45)
                ax.set_title("Relación entre Graduación Alcohólica (%) y Precio", fontsize=14, fontweight='bold', color=text_color, pad=12)
                ax.set_xlabel("Grados de Alcohol (%)", color=text_color, fontsize=11)
                ax.set_ylabel("Precio Final (COP)", color=text_color, fontsize=11)
                ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))
                ax.tick_params(colors=text_color)
            else:
                ax.text(0.5, 0.5, "Sin datos válidos de Grados de Alcohol.", ha='center', va='center', color=text_color, fontsize=12)

        elif plot_type == "Precios por Marca (Boxplot)":
            top_marcas = self.df['marca_estandar'].value_counts().head(5).index
            df_top = self.df[self.df['marca_estandar'].isin(top_marcas)]
            if not df_top.empty:
                sns.boxplot(data=df_top, x='marca_estandar', y='precio_final', hue='marca_estandar', legend=False, ax=ax, palette="Blues", showfliers=False, width=0.4)
                sns.stripplot(data=df_top, x='marca_estandar', y='precio_final', ax=ax, color=strip_color, size=6, jitter=0.2, alpha=0.8)
                ax.set_title("Distribución de Precios por Marca (Top 5 Marcas)", fontsize=14, fontweight='bold', color=text_color, pad=12)
                ax.set_xlabel("Marca Estándar", color=text_color, fontsize=11)
                ax.set_ylabel("Precio (COP)", color=text_color, fontsize=11)
                ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))
                ax.tick_params(colors=text_color)

        elif plot_type == "Distribución y Frecuencia de Descuentos (%)":
            df_desc = self.df.dropna(subset=['descuento']).copy()
            df_desc['desc_num'] = pd.to_numeric(df_desc['descuento'].astype(str).str.replace('%', '').str.strip(), errors='coerce')
            df_desc = df_desc[df_desc['desc_num'] > 0]
            
            if not df_desc.empty:
                ax.hist(df_desc['desc_num'], bins=20, color='#7c3aed', edgecolor='black', alpha=0.85)
                ax.set_title("Distribución de Porcentajes de Oferta / Descuento", fontsize=14, fontweight='bold', color=text_color, pad=12)
                ax.set_xlabel("Porcentaje de Descuento (%)", color=text_color, fontsize=11)
                ax.set_ylabel("Cantidad de Ofertas", color=text_color, fontsize=11)
                ax.tick_params(colors=text_color)
            else:
                ax.text(0.5, 0.5, "No se registraron ofertas activas para los filtros seleccionados.", ha='center', va='center', color=text_color, fontsize=12)

        elif plot_type == "Top 10 Mayores Descuentos":
            df_desc = self.df.copy()
            df_desc['desc_num'] = pd.to_numeric(df_desc['descuento'].astype(str).str.replace('%', '').str.strip(), errors='coerce')
            df_desc = df_desc.dropna(subset=['desc_num']).sort_values(by='desc_num', ascending=False).head(10)
            
            if not df_desc.empty:
                names = df_desc['nombre'].str[:28] + "..."
                ax.barh(names, df_desc['desc_num'], color='#dc2626')
                ax.set_title("Top 10 Productos con Mayor Porcentaje de Descuento", fontsize=14, fontweight='bold', color=text_color, pad=12)
                ax.set_xlabel("Descuento (%)", color=text_color, fontsize=11)
                ax.invert_yaxis()
                ax.tick_params(colors=text_color)
            else:
                ax.text(0.5, 0.5, "Sin datos de ofertas.", ha='center', va='center', color=text_color, fontsize=12)

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.content_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, pady=15)

    def render_metrics(self):
        df = self.df
        total = len(df)
        prices = df['precio_final'].dropna()
        prices = prices[prices > 0]
        
        precio_prom = prices.mean() if not prices.empty else 0
        precio_med = prices.median() if not prices.empty else 0

        df_desc = df.dropna(subset=['descuento']).copy()
        df_desc['desc_num'] = pd.to_numeric(df_desc['descuento'].astype(str).str.replace('%', '').str.strip(), errors='coerce')
        total_ofertas = len(df_desc[df_desc['desc_num'] > 0])

        def create_card(parent, title, value, subtitle=""):
            frame = ctk.CTkFrame(parent, fg_color=("#e2e8f0", "#1f2937"), corner_radius=10)
            ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=13, weight="bold"), text_color=("#475569", "#9ca3af")).pack(pady=(15,5), padx=10)
            ctk.CTkLabel(frame, text=value, font=ctk.CTkFont(size=22, weight="bold"), text_color=("#0f172a", "#f9fafb")).pack(pady=5, padx=10)
            if subtitle:
                ctk.CTkLabel(frame, text=subtitle, font=ctk.CTkFont(size=11), text_color=("#64748b", "#6b7280"), wraplength=280).pack(pady=(0,15), padx=10)
            return frame

        grid = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        grid.pack(fill="x", pady=20, padx=20)
        grid.grid_columnconfigure((0,1,2,3), weight=1)

        create_card(grid, "Lecturas Normalizadas", f"{total:,}").grid(row=0, column=0, padx=8, pady=10, sticky="nsew")
        create_card(grid, "Precio Promedio", f"${precio_prom/1000:,.1f}K COP" if precio_prom > 0 else "N/A").grid(row=0, column=1, padx=8, pady=10, sticky="nsew")
        create_card(grid, "Mediana de Precio", f"${precio_med/1000:,.1f}K COP" if precio_med > 0 else "N/A").grid(row=0, column=2, padx=8, pady=10, sticky="nsew")
        create_card(grid, "Ofertas Activas", f"{total_ofertas:,}").grid(row=0, column=3, padx=8, pady=10, sticky="nsew")


# ==========================================
# 5. Módulo Unificado de Estandarización de Datos (MDM & INVIMA)
# ==========================================
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


if __name__ == "__main__":
    app = DataSuiteApp()
    app.mainloop()
