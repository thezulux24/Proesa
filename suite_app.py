import os
import json
import subprocess
import threading
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.ticker as ticker
import database
import time
from dotenv import load_dotenv

load_dotenv()

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Ensure database tables exist
        db = database.DataSuiteDB()
        db.init_db()
        
        self.title("Suite Universal de Scraping & Analítica")
        self.geometry("1300x850")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="🚀 Suite Data", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        self.btn_extraccion = ctk.CTkButton(self.sidebar_frame, text="📥 Extracción", font=ctk.CTkFont(size=15), command=self.show_extraccion)
        self.btn_extraccion.grid(row=1, column=0, padx=20, pady=10)

        self.btn_viewer = ctk.CTkButton(self.sidebar_frame, text="📄 Visor RAW", font=ctk.CTkFont(size=15), command=self.show_viewer)
        self.btn_viewer.grid(row=2, column=0, padx=20, pady=10)

        self.btn_norm_viewer = ctk.CTkButton(self.sidebar_frame, text="🎯 Visor Normalizado", font=ctk.CTkFont(size=15), fg_color="#2980b9", hover_color="#1c5980", command=self.show_norm_viewer)
        self.btn_norm_viewer.grid(row=3, column=0, padx=20, pady=10)

        self.btn_analysis = ctk.CTkButton(self.sidebar_frame, text="📊 Análisis", font=ctk.CTkFont(size=15), command=self.show_analysis)
        self.btn_analysis.grid(row=4, column=0, padx=20, pady=10)

        self.btn_deepseek = ctk.CTkButton(self.sidebar_frame, text="🤖 Limpieza IA", font=ctk.CTkFont(size=15), command=self.show_deepseek)
        self.btn_deepseek.grid(row=5, column=0, padx=20, pady=10)

        self.btn_compare = ctk.CTkButton(self.sidebar_frame, text="🌐 Comparativas", font=ctk.CTkFont(size=15), fg_color="#8e44ad", hover_color="#732d91", command=self.show_compare)
        self.btn_compare.grid(row=6, column=0, padx=20, pady=10)

        self.btn_normalization = ctk.CTkButton(self.sidebar_frame, text="🔗 Normalización", font=ctk.CTkFont(size=15), fg_color="#f39c12", hover_color="#d68910", command=self.show_normalization)
        self.btn_normalization.grid(row=7, column=0, padx=20, pady=10)

        # Main Frames
        self.frame_extraccion = ExtraccionFrame(self)
        self.frame_viewer = DataViewerFrame(self)
        self.frame_norm_viewer = NormalizedViewerFrame(self)
        self.frame_analysis = AnalysisFrame(self)
        self.frame_deepseek = DeepSeekFilterFrame(self)
        self.frame_compare = CompareFrame(self)
        self.frame_normalization = NormalizationFrame(self)

        self.show_analysis() # Default tab

    def hide_all_frames(self):
        self.frame_extraccion.grid_forget()
        self.frame_viewer.grid_forget()
        self.frame_norm_viewer.grid_forget()
        self.frame_analysis.grid_forget()
        self.frame_deepseek.grid_forget()
        self.frame_compare.grid_forget()
        self.frame_normalization.grid_forget()

    def show_extraccion(self):
        self.hide_all_frames()
        self.frame_extraccion.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_viewer(self):
        self.hide_all_frames()
        self.frame_viewer.load_filters()
        self.frame_viewer.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
    def show_norm_viewer(self):
        self.hide_all_frames()
        self.frame_norm_viewer.load_filters()
        self.frame_norm_viewer.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_analysis(self):
        self.hide_all_frames()
        self.frame_analysis.load_filters()
        self.frame_analysis.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_deepseek(self):
        self.hide_all_frames()
        self.frame_deepseek.load_filters()
        self.frame_deepseek.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_compare(self):
        self.hide_all_frames()
        self.frame_compare.load_data()
        self.frame_compare.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_normalization(self):
        self.hide_all_frames()
        self.frame_normalization.load_data()
        self.frame_normalization.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)


class ExtraccionFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="📥 Módulo de Extracción", font=ctk.CTkFont(size=24, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        self.controls = ctk.CTkFrame(self, fg_color="transparent")
        self.controls.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self.controls, text="Seleccionar Scraper:", font=ctk.CTkFont(size=14)).pack(side="left", padx=(0,10))
        self.scraper_var = ctk.StringVar(value="Éxito")
        self.scraper_combo = ctk.CTkComboBox(self.controls, variable=self.scraper_var, values=["Éxito", "Ejecutar Todos (Próximamente)"])
        self.scraper_combo.pack(side="left", padx=(0,20))

        self.btn_run = ctk.CTkButton(self.controls, text="▶ Iniciar Extracción", font=ctk.CTkFont(weight="bold"), command=self.run_scraper)
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
        if target != "Éxito":
            messagebox.showinfo("Info", "Ese scraper aún no está implementado.")
            return

        self.btn_run.configure(state="disabled")
        self.log(f"Iniciando scraper: {target}...")
        threading.Thread(target=self._run_process, daemon=True).start()

    def _run_process(self):
        try:
            process = subprocess.Popen(
                ["python", "scraper_exito/scraper.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in process.stdout:
                self.log(line.strip())
            process.wait()
            
            self.log("Guardando en la Base de Datos SQLite...")
            if os.path.exists("data/productos_exito.json"):
                with open("data/productos_exito.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                database.insert_products("Éxito", data)
                self.log(f"Se insertaron {len(data)} registros en la BD exitosamente.")
                
            self.log("✅ ¡Proceso finalizado!")
        except Exception as e:
            self.log(f"❌ Error: {e}")
        finally:
            self.btn_run.configure(state="normal")


class DataViewerFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="📄 Visor RAW (Crudos)", font=ctk.CTkFont(size=24, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Filters
        self.filters_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.filters_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.fuente_var = ctk.StringVar(value="Todas")
        self.fuente_combo = ctk.CTkComboBox(self.filters_frame, variable=self.fuente_var, command=self.update_data, width=120)
        self.fuente_combo.pack(side="left", padx=5)

        self.fecha_var = ctk.StringVar(value="Todas")
        self.fecha_combo = ctk.CTkComboBox(self.filters_frame, variable=self.fecha_var, command=self.update_data, width=120)
        self.fecha_combo.pack(side="left", padx=5)

        self.btn_refresh = ctk.CTkButton(self.filters_frame, text="🔄 Refrescar", width=100, command=self.load_filters)
        self.btn_refresh.pack(side="left", padx=10)
        
        self.btn_export = ctk.CTkButton(self.filters_frame, text="💾 Exportar a Excel", fg_color="#27ae60", hover_color="#219150", width=150, command=self.export_data)
        self.btn_export.pack(side="left", padx=10)

        self.btn_remove = ctk.CTkButton(self.filters_frame, text="🗑️ Eliminar Seleccionado", fg_color="#d32f2f", hover_color="#9a0007", width=150, command=self.soft_delete_selected)
        self.btn_remove.pack(side="right", padx=10)

        # Treeview
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        columns = ("ID", "Fuente", "Nombre", "Marca", "Categoría", "Tipo", "Precio", "Alcohol", "Descuento")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")
        
        # Configure columns
        self.tree.heading("ID", text="ID BD")
        self.tree.column("ID", width=50, anchor="center")
        self.tree.heading("Fuente", text="Fuente")
        self.tree.column("Fuente", width=80, anchor="center")
        self.tree.heading("Nombre", text="Nombre")
        self.tree.column("Nombre", width=350)
        self.tree.heading("Marca", text="Marca")
        self.tree.column("Marca", width=100)
        self.tree.heading("Categoría", text="Categoría")
        self.tree.column("Categoría", width=150)
        self.tree.heading("Tipo", text="Tipo")
        self.tree.column("Tipo", width=80, anchor="center")
        self.tree.heading("Precio", text="Precio")
        self.tree.column("Precio", width=80, anchor="e")
        self.tree.heading("Alcohol", text="Alcohol")
        self.tree.column("Alcohol", width=60, anchor="center")
        self.tree.heading("Descuento", text="Dcto (%)")
        self.tree.column("Descuento", width=60, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

    def load_filters(self):
        sources = ["Todas"] + database.get_available_sources()
        dates = ["Todas"] + database.get_available_dates()
        self.fuente_combo.configure(values=sources)
        self.fecha_combo.configure(values=dates)
        self.update_data()

    def update_data(self, *args):
        fuente = self.fuente_var.get()
        fecha = self.fecha_var.get()
        df = database.get_data_as_dataframe(fuente, fecha, "Todos")
        
        for item in self.tree.get_children():
            self.tree.delete(item)

        if df.empty:
            return

        for _, r in df.iterrows():
            precio_str = f"${r['precio_final']/1000:,.0f}K" if pd.notnull(r['precio_final']) else "N/A"
            descuento = str(r['descuento']) if pd.notnull(r['descuento']) and r['descuento'] else "0%"
            if not descuento.endswith('%'): descuento += '%'
            
            self.tree.insert("", "end", values=(
                r['id'], r['fuente'], r['nombre'], r['marca'], r['categoria'], 
                r['tipo_producto'], precio_str, r['grados_alcohol'], descuento
            ))

    def export_data(self):
        if len(self.tree.get_children()) == 0:
            messagebox.showwarning("Vacío", "No hay datos para exportar.")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")],
            title="Exportar Datos"
        )
        
        if not file_path:
            return
            
        fuente = self.fuente_var.get()
        fecha = self.fecha_var.get()
        df = database.get_data_as_dataframe(fuente, fecha, "Todos")
        
        try:
            if file_path.endswith('.csv'):
                df.to_csv(file_path, index=False, encoding='utf-8')
            else:
                df.to_excel(file_path, index=False)
            messagebox.showinfo("Éxito", f"Datos exportados correctamente a:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error de Exportación", str(e))

    def soft_delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "No has seleccionado ningún producto.")
            return

        count = 0
        for s in selected:
            item = self.tree.item(s)
            db_id = item["values"][0]
            database.delete_false_positive(db_id)
            self.tree.delete(s)
            count += 1
            
        messagebox.showinfo("Éxito", f"Se eliminaron (soft delete) {count} registros.")


class NormalizedViewerFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="🎯 Visor Normalizado (MDM)", font=ctk.CTkFont(size=24, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Filters
        self.filters_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.filters_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.fuente_var = ctk.StringVar(value="Todas")
        self.fuente_combo = ctk.CTkComboBox(self.filters_frame, variable=self.fuente_var, command=self.update_data, width=120)
        self.fuente_combo.pack(side="left", padx=5)

        self.fecha_var = ctk.StringVar(value="Todas")
        self.fecha_combo = ctk.CTkComboBox(self.filters_frame, variable=self.fecha_var, command=self.update_data, width=120)
        self.fecha_combo.pack(side="left", padx=5)

        self.btn_refresh = ctk.CTkButton(self.filters_frame, text="🔄 Refrescar", width=100, command=self.load_filters)
        self.btn_refresh.pack(side="left", padx=10)
        
        self.btn_export = ctk.CTkButton(self.filters_frame, text="💾 Exportar a Excel", fg_color="#27ae60", hover_color="#219150", width=150, command=self.export_data)
        self.btn_export.pack(side="left", padx=10)

        # Treeview
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        import tkinter.ttk as ttk
        columns = ("Código", "Fuente", "Nombre Estándar", "Marca", "Categoría", "Tipo", "Precio Original", "Precio Final", "Descuento")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")
        
        self.tree.heading("Código", text="Código Universal")
        self.tree.column("Código", width=100, anchor="center")
        self.tree.heading("Fuente", text="Fuente")
        self.tree.column("Fuente", width=80, anchor="center")
        self.tree.heading("Nombre Estándar", text="Nombre Estándar")
        self.tree.column("Nombre Estándar", width=300)
        self.tree.heading("Marca", text="Marca")
        self.tree.column("Marca", width=100)
        self.tree.heading("Categoría", text="Categoría")
        self.tree.column("Categoría", width=120)
        self.tree.heading("Tipo", text="Tipo")
        self.tree.column("Tipo", width=80, anchor="center")
        self.tree.heading("Precio Original", text="Precio Original")
        self.tree.column("Precio Original", width=90, anchor="e")
        self.tree.heading("Precio Final", text="Precio Final")
        self.tree.column("Precio Final", width=90, anchor="e")
        self.tree.heading("Descuento", text="Dcto")
        self.tree.column("Descuento", width=60, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

    def load_filters(self):
        import database
        sources = ["Todas"] + database.get_available_sources()
        dates = ["Todas"] + database.get_available_dates()
        self.fuente_combo.configure(values=sources)
        self.fecha_combo.configure(values=dates)
        self.update_data()

    def update_data(self, *args):
        import database
        import pandas as pd
        fuente = self.fuente_var.get()
        fecha = self.fecha_var.get()
        
        df = database.get_normalized_data_as_dataframe(fuente=fuente, fecha=fecha)
        self.df_current = df
        
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if not df.empty:
            for _, row in df.iterrows():
                self.tree.insert("", "end", values=(
                    row.get('id', ''),
                    row.get('fuente', ''),
                    row.get('nombre', ''),
                    row.get('marca_estandar', ''),
                    row.get('subcategoria_estandar', ''),
                    row.get('tipo_producto_estandar', ''),
                    f"${row.get('precio_original', 0):,.0f}" if pd.notnull(row.get('precio_original')) else "N/A",
                    f"${row.get('precio_final', 0):,.0f}" if pd.notnull(row.get('precio_final')) else "N/A",
                    row.get('descuento', '0%')
                ))

    def export_data(self):
        import tkinter.messagebox as messagebox
        import tkinter.filedialog as filedialog
        if hasattr(self, 'df_current') and not self.df_current.empty:
            filepath = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
            if not filepath:
                return
            self.df_current.to_excel(filepath, index=False)
            messagebox.showinfo("Exportar", f"Datos normalizados exportados a {filepath}")

class AnalysisFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="📊 Análisis de Datos", font=ctk.CTkFont(size=24, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 0), sticky="w")

        # Top Filters
        self.filters_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.filters_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        # Source
        self.fuente_var = ctk.StringVar(value="Todas")
        self.fuente_combo = ctk.CTkComboBox(self.filters_frame, variable=self.fuente_var, command=self.update_data, width=120)
        self.fuente_combo.pack(side="left", padx=5)

        # Date
        self.fecha_var = ctk.StringVar(value="Todas")
        self.fecha_combo = ctk.CTkComboBox(self.filters_frame, variable=self.fecha_var, command=self.update_data, width=120)
        self.fecha_combo.pack(side="left", padx=5)

        # Category
        self.tipo_var = ctk.StringVar(value="Todos")
        self.tipo_combo = ctk.CTkComboBox(self.filters_frame, variable=self.tipo_var, values=["Todos", "Alcohol", "Tabaco"], command=self.on_filter_change, width=120)
        self.tipo_combo.pack(side="left", padx=5)

        # Plot selection
        self.plot_type_var = ctk.StringVar(value="Resumen de Métricas")
        self.plot_combo = ctk.CTkComboBox(self.filters_frame, variable=self.plot_type_var, values=[], command=self.update_plot, width=250)
        self.plot_combo.pack(side="right", padx=5)
        
        self.btn_refresh = ctk.CTkButton(self.filters_frame, text="🔄 Refrescar", width=100, command=self.load_filters)
        self.btn_refresh.pack(side="right", padx=5)

        # Content Area
        self.content_frame = ctk.CTkScrollableFrame(self)
        self.content_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.df = pd.DataFrame()
        self.update_plot_options()

    def on_filter_change(self, *args):
        self.update_plot_options()
        self.update_data()

    def update_plot_options(self):
        current = self.plot_type_var.get()
        options = [
            "Resumen de Métricas",
            "Marcas Más Vendidas",
            "Histograma de Precios",
            "Precio vs Grados de Alcohol",
            "Boxplot de Atípicos",
            "Distribución de Descuentos",
            "Top 10 Mayores Descuentos",
            "Matriz de Correlación (Heatmap)",
            "Comparativa de Precios por Marca"
        ]
        
        if self.tipo_var.get() == "Todos":
            options.insert(2, "Proporción Tipos de Producto")
            
        self.plot_combo.configure(values=options)
        if current not in options:
            self.plot_type_var.set("Resumen de Métricas")

    def load_filters(self):
        sources = ["Todas"] + database.get_available_sources()
        dates = ["Todas"] + database.get_available_dates()
        
        self.fuente_combo.configure(values=sources)
        if self.fuente_var.get() not in sources:
            self.fuente_var.set("Todas")
            
        self.fecha_combo.configure(values=dates)
        if self.fecha_var.get() not in dates:
            self.fecha_var.set("Todas")
            
        self.on_filter_change()

    def update_data(self, *args):
        fuente = self.fuente_var.get()
        fecha = self.fecha_var.get()
        tipo = self.tipo_var.get()
        
        self.df = database.get_data_as_dataframe(fuente, fecha, tipo)
        self.update_plot()

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def update_plot(self, *args):
        self.clear_content()
        if self.df is None or self.df.empty:
            ctk.CTkLabel(self.content_frame, text="No hay datos para mostrar con los filtros actuales.", font=ctk.CTkFont(size=16)).pack(pady=50)
            return

        plot_type = self.plot_type_var.get()
        
        if plot_type == "Resumen de Métricas":
            self.render_metrics()
            return

        # Fix memory leak by closing all previous plots
        plt.close('all')

        fig, ax = plt.subplots(figsize=(10, 5))

        if plot_type == "Marcas Más Vendidas":
            counts = self.df['marca'].value_counts().head(10)
            counts.plot(kind='bar', ax=ax, color='#4a90e2')
            ax.set_title("Top 10 Marcas")
            ax.set_ylabel("Cantidad de Productos")
            plt.xticks(rotation=45, ha='right')

        elif plot_type == "Proporción Tipos de Producto":
            counts = self.df['tipo_producto'].value_counts()
            counts.plot(kind='pie', ax=ax, autopct='%1.1f%%', colors=['#ff9999','#66b3ff', '#99ff99'])
            ax.set_title("Proporción por Tipo")
            ax.set_ylabel("")

        elif plot_type == "Histograma de Precios":
            prices = self.df['precio_final'].dropna()
            ax.hist(prices, bins=50, color='#50e3c2', edgecolor='black')
            ax.set_title("Distribución de Precios")
            ax.set_xlabel("Precio (COP)")
            ax.set_ylabel("Frecuencia")
            ax.set_yscale('log')
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))
            
        elif plot_type == "Precio vs Grados de Alcohol":
            df_clean = self.df.dropna(subset=['precio_final', 'grados_alcohol'])
            df_clean['grados_num'] = pd.to_numeric(df_clean['grados_alcohol'].astype(str).str.replace('%', '').str.strip(), errors='coerce')
            df_clean = df_clean.dropna(subset=['grados_num'])
            ax.scatter(df_clean['grados_num'], df_clean['precio_final'], alpha=0.5, c='#f5a623')
            ax.set_title("Precio vs % de Alcohol")
            ax.set_xlabel("% de Alcohol")
            ax.set_ylabel("Precio (COP)")
            ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))

        elif plot_type == "Boxplot de Atípicos":
            prices = self.df['precio_final'].dropna()
            ax.boxplot(prices, vert=False, patch_artist=True, flierprops=dict(marker='o', markerfacecolor='red', markersize=4, alpha=0.5))
            ax.set_title("Detección de Valores Atípicos (Precios)")
            ax.set_xlabel("Precio (COP)")
            ax.set_xscale('log')
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))
            
        elif plot_type == "Distribución de Descuentos":
            df_desc = self.df.dropna(subset=['descuento'])
            df_desc['desc_num'] = pd.to_numeric(df_desc['descuento'].astype(str).str.replace('%', '').str.strip(), errors='coerce')
            df_desc = df_desc[df_desc['desc_num'] > 0].dropna(subset=['desc_num'])
            ax.hist(df_desc['desc_num'], bins=20, color='#9b59b6', edgecolor='black')
            ax.set_title("Frecuencia de Porcentajes de Descuento")
            ax.set_xlabel("Descuento (%)")
            ax.set_ylabel("Frecuencia")
            
        elif plot_type == "Top 10 Mayores Descuentos":
            df_desc = self.df.copy()
            df_desc['desc_num'] = pd.to_numeric(df_desc['descuento'].astype(str).str.replace('%', '').str.strip(), errors='coerce')
            df_desc = df_desc.dropna(subset=['desc_num'])
            top_desc = df_desc.sort_values(by='desc_num', ascending=False).head(10)
            
            names = top_desc['nombre'].str[:25] + "..."
            ax.barh(names, top_desc['desc_num'], color='#e74c3c')
            ax.set_title("Top 10 Productos con Mayor Descuento (%)")
            ax.set_xlabel("Descuento (%)")
            ax.invert_yaxis()

        elif plot_type == "Matriz de Correlación (Heatmap)":
            df_corr = self.df.copy()
            df_corr['Precio Final'] = df_corr['precio_final']
            df_corr['Descuento (%)'] = pd.to_numeric(df_corr['descuento'].astype(str).str.replace('%', '').str.strip(), errors='coerce').fillna(0)
            df_corr['Grados Alcohol'] = pd.to_numeric(df_corr['grados_alcohol'].astype(str).str.replace('%', '').str.strip(), errors='coerce').fillna(0)
            
            corr_data = df_corr[['Precio Final', 'Descuento (%)', 'Grados Alcohol']].corr()
            sns.heatmap(corr_data, annot=True, cmap="coolwarm", ax=ax, fmt=".2f")
            ax.set_title("Correlación de Variables")

        elif plot_type == "Comparativa de Precios por Marca":
            # Top 5 marcas con más productos
            top_marcas = self.df['marca'].value_counts().head(5).index
            df_top = self.df[self.df['marca'].isin(top_marcas)]
            
            sns.boxplot(data=df_top, x='marca', y='precio_final', hue='marca', ax=ax, palette="Set2", showfliers=False, legend=False)
            ax.set_title("Precios por Marca (Top 5)")
            ax.set_xlabel("Marca")
            ax.set_ylabel("Precio (COP)")
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
            mas_caro_idx = df['precio_final'].idxmax()
            prod_caro = df.loc[mas_caro_idx]
            txt_caro = f"{prod_caro['nombre']} (${prod_caro['precio_final']/1000:,.0f}K)"
        except:
            txt_caro = "N/A"
            
        try:
            mas_barato_idx = df['precio_final'].idxmin()
            prod_barato = df.loc[mas_barato_idx]
            txt_barato = f"{prod_barato['nombre']} (${prod_barato['precio_final']/1000:,.0f}K)"
        except:
            txt_barato = "N/A"
            
        df['grados_num'] = pd.to_numeric(df['grados_alcohol'].astype(str).str.replace('%', '').str.strip(), errors='coerce')
        alc_prom = df['grados_num'].mean()
        try:
            mas_alc_idx = df['grados_num'].idxmax()
            prod_alc = df.loc[mas_alc_idx]
            txt_alc = f"{prod_alc['nombre']} ({prod_alc['grados_num']}%)"
        except:
            txt_alc = "N/A"
            
        # Helper conversions
        df['desc_num'] = pd.to_numeric(df['descuento'].astype(str).str.replace('%', '').str.strip(), errors='coerce')
        df_desc = df[df['desc_num'] > 0]
        total_desc = len(df_desc)
        prom_desc = df_desc['desc_num'].mean() if not df_desc.empty else 0
        try:
            mas_desc_idx = df_desc['desc_num'].idxmax()
            prod_desc = df.loc[mas_desc_idx]
            txt_desc = f"{prod_desc['nombre']} (-{prod_desc['desc_num']}%)"
        except:
            txt_desc = "N/A"

        def create_card(parent, title, value, subtitle=""):
            frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
            ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=14, weight="bold"), text_color="#a0a0a0").pack(pady=(15,5), padx=10)
            ctk.CTkLabel(frame, text=value, font=ctk.CTkFont(size=22, weight="bold")).pack(pady=5, padx=10)
            if subtitle:
                ctk.CTkLabel(frame, text=subtitle, font=ctk.CTkFont(size=12), text_color="#7a7a7a", wraplength=300).pack(pady=(0,15), padx=10)
            return frame

        grid = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        grid.pack(fill="x", pady=20, padx=20)
        grid.grid_columnconfigure((0,1,2), weight=1)

        create_card(grid, "Total Productos", f"{total}").grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        create_card(grid, "Precio Promedio", f"${precio_prom/1000:,.1f}K COP").grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        create_card(grid, "Mediana de Precio", f"${precio_med/1000:,.1f}K COP").grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        
        create_card(grid, "Alcohol Promedio", f"{alc_prom:.1f} %").grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        create_card(grid, "Producto Más Caro", txt_caro.split(" ($")[0][:30]+"...", txt_caro).grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        create_card(grid, "Producto Más Barato", txt_barato.split(" ($")[0][:30]+"...", txt_barato).grid(row=1, column=2, padx=10, pady=10, sticky="nsew")
        
        create_card(grid, "Mayor Grado de Alcohol", txt_alc.split(" (")[0][:30]+"...", txt_alc).grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        create_card(grid, "En Oferta / Prom. Descuento", f"{total_desc} ({prom_desc:.1f}%)").grid(row=2, column=1, padx=10, pady=10, sticky="nsew")
        create_card(grid, "Mayor Descuento", txt_desc.split(" (-")[0][:30]+"...", txt_desc).grid(row=2, column=2, padx=10, pady=10, sticky="nsew")


class DeepSeekFilterFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="🤖 Filtro IA (DeepSeek)", font=ctk.CTkFont(size=24, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.controls = ctk.CTkFrame(self, fg_color="transparent")
        self.controls.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self.controls, text="Evaluando directamente en Maestro de Productos", text_color="gray", font=ctk.CTkFont(size=12, slant="italic")).pack(side="left", padx=(0,20))

        self.api_entry = ctk.CTkEntry(self.controls, placeholder_text="Tu DeepSeek API Key", width=200, show="*")
        env_key = os.getenv("DEEPSEEK_API_KEY")
        if env_key:
            self.api_entry.insert(0, env_key)
        self.api_entry.pack(side="left", padx=(0, 10))

        self.btn_detect = ctk.CTkButton(self.controls, text="🔍 Buscar Atípicos", font=ctk.CTkFont(weight="bold"), command=self.detect)
        self.btn_detect.pack(side="left", padx=(0, 10))

        self.btn_remove = ctk.CTkButton(self.controls, text="🗑️ Eliminar BD (Soft)", fg_color="#d32f2f", hover_color="#9a0007", font=ctk.CTkFont(weight="bold"), command=self.remove_selected)
        self.btn_remove.pack(side="right")
        
        self.status_label = ctk.CTkLabel(self.controls, text="", text_color="yellow", font=ctk.CTkFont(weight="bold"))
        self.status_label.pack(side="right", padx=20)

        # Treeview list
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(self.tree_frame, columns=("DB_ID", "Nombre", "Marca", "Tipo"), show="headings")
        self.tree.heading("DB_ID", text="ID Maestro")
        self.tree.heading("Nombre", text="Nombre Estándar")
        self.tree.heading("Marca", text="Marca Estándar")
        self.tree.heading("Tipo", text="Tipo")
        
        self.tree.column("DB_ID", width=150, anchor="center")
        self.tree.column("Nombre", width=450)
        self.tree.column("Marca", width=120, anchor="center")
        self.tree.column("Tipo", width=110, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.false_positives = [] 

    def load_filters(self):
        pass # Filtros removidos por uso directo de Maestro de Productos

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
            # Filtrar los que ya están eliminados
            if 'deleted' in df.columns:
                df = df[df['deleted'] == 0]
                
            if df.empty:
                self.after(0, lambda: messagebox.showinfo("Info", "El Maestro de Productos está vacío."))
                set_status("")
                return

            # Mapear las columnas para que la IA funcione
            df.rename(columns={'codigo_universal': 'id', 'nombre_estandar': 'nombre', 'marca_estandar': 'marca', 'tipo_producto_estandar': 'tipo'}, inplace=True)
            df = df.drop_duplicates(subset=['id'])

            try:
                from openai import OpenAI
            except ImportError:
                self.after(0, lambda: messagebox.showerror("Error", "Falta librería 'openai'"))
                set_status("")
                return
                
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            prompt = """Eres un auditor de datos experto con amplio conocimiento en marcas y productos de consumo.
Tu tarea es determinar si los siguientes productos son un "falso positivo" para la categoría de Alcohol o Tabaco basándote principalmente en el NOMBRE.

Criterio:
1. Evalúa el NOMBRE del producto. Si reconoces que el producto contiene alcohol, tabaco o es un vapeador, NO ES falso positivo (falso positivo = false).
2. Las bebidas que simulan ser alcohólicas pero no contienen alcohol (ej. 'Vino Sin Alcohol', 'Cerveza Zero') NO son falsos positivos.
3. Si el producto es un Combo o Pack que INCLUYE una bebida alcohólica/tabaco/vape, NO es falso positivo.
4. Un producto ES un FALSO POSITIVO (true) ÚNICAMENTE si se trata de un elemento no alcohólico/no tabaco por sí solo (ej. copas, vasos, baterías, hieleras, sodas, agua tónica, exprimidores, estuches vacíos, útiles, etc.).

Recibirás un array JSON. Devuelve ÚNICAMENTE un array plano de cadenas de texto (IDs) con los 'db_id' de aquellos que sí son falsos positivos (true).
Ejemplo de salida estricta: ["id1", "id2", "id3"]
Si ninguno es falso positivo, devuelve un array vacío: []"""
            
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
                        text = response.choices[0].message.content.strip()
                        text = text.replace("```json", "").replace("```", "").strip()
                        ids = json.loads(text)
                        if isinstance(ids, list):
                            fp_db_ids.extend([str(x) for x in ids])
                        break
                    except Exception as loop_e:
                        if attempt < max_retries - 1:
                            print(f"Error AI reintentando en 10s... ({loop_e})")
                            time.sleep(10)
                        else:
                            print(f"Error AI in chunk tras reintentos: {loop_e}")
                            
                time.sleep(0.5)

            self.false_positives = df[df['id'].isin(fp_db_ids)].to_dict('records')
            set_status("¡Análisis completado!")
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
            
        # Select all false positives by default so user can just hit delete
        if all_items:
            self.tree.selection_set(all_items)
            messagebox.showinfo("Búsqueda Lista", f"Se encontraron {len(all_items)} posibles falsos positivos. Revisa y haz clic en Eliminar.")

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
            
        messagebox.showinfo("Éxito", f"Se eliminaron (soft delete) {count} registros de la base de datos.")


class CompareFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text="🌐 Comparativas de Mercado", font=ctk.CTkFont(size=24, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.filters_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.filters_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        # Category Filter
        self.tipo_var = ctk.StringVar(value="Todos")
        self.tipo_combo = ctk.CTkComboBox(self.filters_frame, variable=self.tipo_var, values=["Todos", "Alcohol", "Tabaco"], command=self.update_plot, width=100)
        self.tipo_combo.pack(side="left", padx=(0,5))

        # Metric Filter
        self.metrica_var = ctk.StringVar(value="Promedio")
        self.metrica_combo = ctk.CTkComboBox(self.filters_frame, variable=self.metrica_var, values=["Promedio", "Mediana"], command=self.update_plot, width=100)
        self.metrica_combo.pack(side="left", padx=5)

        self.plot_type_var = ctk.StringVar(value="Buscador Cruzado (Producto)")
        self.plot_combo = ctk.CTkComboBox(self.filters_frame, variable=self.plot_type_var, values=[
            "Buscador Cruzado (Producto)",
            "Evolución Temporal del Mercado"
        ], command=self.update_plot, width=230)
        self.plot_combo.pack(side="left", padx=5)

        self.search_var = ctk.StringVar(value="Haz clic en Elegir Producto 👉")
        
        self.lbl_selected = ctk.CTkLabel(self.filters_frame, textvariable=self.search_var, font=ctk.CTkFont(size=14, slant="italic"))
        self.lbl_selected.pack(side="left", padx=10)
        
        self.btn_search = ctk.CTkButton(self.filters_frame, text="🔍 Elegir Producto", command=self.open_product_modal, width=150, fg_color="#2980b9", hover_color="#1f618d")
        self.btn_search.pack(side="left", padx=5)

        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.raw_df = pd.DataFrame()
        self.df = pd.DataFrame()
        self.unique_products = []

    def load_data(self):
        # Load absolute everything for market comparison
        self.raw_df = database.get_data_as_dataframe("Todas", "Todas", "Todos")
        if not self.raw_df.empty:
            self.unique_products = sorted(self.raw_df['nombre'].dropna().unique().tolist())
        self.update_plot()

    def open_product_modal(self):
        if self.df.empty:
            messagebox.showwarning("Vacío", "La base de datos está vacía.")
            return
            
        modal = ctk.CTkToplevel(self)
        modal.title("Seleccionar Producto")
        modal.geometry("500x600")
        modal.transient(self.winfo_toplevel())
        modal.grab_set()

        ctk.CTkLabel(modal, text="Buscar y Seleccionar Producto", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)
        
        search_entry = ctk.CTkEntry(modal, placeholder_text="Escribe para filtrar...", width=300)
        search_entry.pack(pady=5)
        
        listbox_frame = ctk.CTkFrame(modal)
        listbox_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, font=("Arial", 11), bg="#2b2b2b", fg="white", selectbackground="#3498db")
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
        
        ctk.CTkButton(modal, text="✅ Confirmar Selección", command=on_select).pack(pady=15)

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def update_plot(self, *args):
        self.clear_content()
        if self.raw_df.empty:
            ctk.CTkLabel(self.content_frame, text="No hay datos en la base de datos.", font=ctk.CTkFont(size=16)).pack(pady=50)
            return

        # Apply Category Filter
        if self.tipo_var.get() != "Todos":
            self.df = self.raw_df[self.raw_df['tipo_producto'] == self.tipo_var.get()]
        else:
            self.df = self.raw_df.copy()

        if self.df.empty:
            ctk.CTkLabel(self.content_frame, text="No hay datos para la categoría seleccionada.", font=ctk.CTkFont(size=16)).pack(pady=50)
            return

        plot_type = self.plot_type_var.get()
        plt.close('all')
        fig, ax = plt.subplots(figsize=(10, 5))

        if plot_type == "Buscador Cruzado (Producto)":
            query = self.search_var.get().strip()
            if query == "Haz clic en Elegir Producto 👉" or not query:
                ax.text(0.5, 0.5, "Selecciona un producto usando el botón de arriba.", ha='center', va='center')
            else:
                # Use exact match for the modal selection
                df_filtered = self.df[self.df['nombre'] == query]
                if df_filtered.empty:
                    ax.text(0.5, 0.5, f"No se encontró '{query}' en la categoría seleccionada.", ha='center', va='center')
                else:
                    sns.boxplot(data=df_filtered, x='fuente', y='precio_final', hue='fuente', ax=ax, palette="Set1", showfliers=False, legend=False)
                    ax.set_title(f"Guerra de Precios: '{query}'")
                    ax.set_xlabel("Comercio / Fuente")
                    ax.set_ylabel("Precio (COP)")
                    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))
                    
        elif plot_type == "Evolución Temporal del Mercado":
            if 'fecha_extraccion' in self.df.columns and not self.df['fecha_extraccion'].isnull().all():
                metrica = self.metrica_var.get()
                if metrica == "Mediana":
                    df_time = self.df.groupby(['fecha_extraccion', 'fuente'])['precio_final'].median().reset_index()
                else:
                    df_time = self.df.groupby(['fecha_extraccion', 'fuente'])['precio_final'].mean().reset_index()
                    
                if not df_time.empty:
                    sns.lineplot(data=df_time, x='fecha_extraccion', y='precio_final', hue='fuente', marker='o', linewidth=2, ax=ax)
                    ax.set_title(f"Inflación/Deflación de Precios ({metrica})")
                    ax.set_xlabel("Fecha de Extracción")
                    ax.set_ylabel(f"Precio {metrica} Global (COP)")
                    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'${x/1000:,.0f}K'))
                    plt.xticks(rotation=45)
                else:
                    ax.text(0.5, 0.5, "No hay datos para evolución", ha='center', va='center')
            else:
                ax.text(0.5, 0.5, "No hay fechas suficientes.", ha='center', va='center')

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.content_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

class NormalizationFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure((0, 1), weight=1)

        self.label = ctk.CTkLabel(self, text="🔗 Normalización (MDM)", font=ctk.CTkFont(size=24, weight="bold"))
        self.label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="w")

        self.controls = ctk.CTkFrame(self, fg_color="transparent")
        self.controls.grid(row=1, column=0, columnspan=2, padx=20, pady=5, sticky="ew")

        self.btn_refresh = ctk.CTkButton(self.controls, text="🔄 Refrescar Tablas", command=self.load_data)
        self.btn_refresh.pack(side="left", padx=5)

        self.btn_etl = ctk.CTkButton(self.controls, text="🚀 Ejecutar ETL Normalización", fg_color="#27ae60", hover_color="#219150", command=self.run_etl)
        self.btn_etl.pack(side="right", padx=5)
        
        self.btn_auto = ctk.CTkButton(self.controls, text="🤖 Auto-Mapeo Básico", fg_color="#8e44ad", hover_color="#732d91", command=self.auto_map)
        self.btn_auto.pack(side="right", padx=5)

        self.btn_auto_ai = ctk.CTkButton(self.controls, text="🧠 Auto-Mapeo (DeepSeek)", fg_color="#c0392b", hover_color="#922b21", command=self.auto_map_deepseek)
        self.btn_auto_ai.pack(side="right", padx=5)

        # Left side: Raw unmapped products
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=2, column=0, padx=(20, 10), pady=(0, 20), sticky="nsew")
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.left_frame, text="Productos Sin Mapear (Crudos)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=5)
        self.tree_raw = ttk.Treeview(self.left_frame, columns=("Comercio", "ID", "Nombre", "Marca", "Tipo"), show="headings")
        self.tree_raw.heading("Comercio", text="Comercio")
        self.tree_raw.heading("ID", text="ID")
        self.tree_raw.heading("Nombre", text="Nombre")
        self.tree_raw.heading("Marca", text="Marca")
        self.tree_raw.heading("Tipo", text="Tipo")
        self.tree_raw.column("Comercio", width=80)
        self.tree_raw.column("ID", width=80)
        self.tree_raw.column("Nombre", width=200)
        self.tree_raw.column("Marca", width=100)
        self.tree_raw.column("Tipo", width=100)
        self.tree_raw.grid(row=1, column=0, sticky="nsew")
        
        scrollbar_raw = ttk.Scrollbar(self.left_frame, orient="vertical", command=self.tree_raw.yview)
        self.tree_raw.configure(yscroll=scrollbar_raw.set)
        scrollbar_raw.grid(row=1, column=1, sticky="ns")

        # Right side: Master products
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=2, column=1, padx=(10, 20), pady=(0, 20), sticky="nsew")
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.right_frame, text="Maestro de Productos (Diccionario)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=5)
        self.tree_master = ttk.Treeview(self.right_frame, columns=("Código", "Nombre", "Marca", "Tipo"), show="headings")
        self.tree_master.heading("Código", text="Código")
        self.tree_master.heading("Nombre", text="Nombre Estándar")
        self.tree_master.heading("Marca", text="Marca")
        self.tree_master.heading("Tipo", text="Tipo")
        self.tree_master.column("Código", width=80)
        self.tree_master.column("Nombre", width=200)
        self.tree_master.column("Marca", width=100)
        self.tree_master.column("Tipo", width=100)
        self.tree_master.grid(row=1, column=0, sticky="nsew")
        
        scrollbar_master = ttk.Scrollbar(self.right_frame, orient="vertical", command=self.tree_master.yview)
        self.tree_master.configure(yscroll=scrollbar_master.set)
        scrollbar_master.grid(row=1, column=1, sticky="ns")

        # Bottom controls for linking
        self.bottom_controls = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_controls.grid(row=3, column=0, columnspan=2, padx=20, pady=(0,20), sticky="ew")

        self.btn_link = ctk.CTkButton(self.bottom_controls, text="🔗 Vincular Seleccionados al Maestro", font=ctk.CTkFont(weight="bold"), command=self.link_products)
        self.btn_link.pack(side="left", padx=5)

        self.btn_new_master = ctk.CTkButton(self.bottom_controls, text="➕ Crear Nuevo Maestro desde Crudo", command=self.create_master_from_raw)
        self.btn_new_master.pack(side="left", padx=5)

        self.df_raw = pd.DataFrame()
        self.df_master = pd.DataFrame()

    def load_data(self):
        for i in self.tree_raw.get_children(): self.tree_raw.delete(i)
        for i in self.tree_master.get_children(): self.tree_master.delete(i)

        self.df_raw = database.get_unmapped_products()
        for _, r in self.df_raw.iterrows():
            self.tree_raw.insert("", "end", values=(r['comercio'], r['producto_id'], r['nombre'], r['marca'], r['tipo_producto']))

        self.df_master = database.get_maestro_products()
        for _, r in self.df_master.iterrows():
            self.tree_master.insert("", "end", values=(r['codigo_universal'], r['nombre_estandar'], r['marca_estandar'], r['tipo_producto_estandar']))

    def link_products(self):
        sel_raw = self.tree_raw.selection()
        sel_master = self.tree_master.selection()
        if not sel_raw or not sel_master:
            messagebox.showwarning("Atención", "Debe seleccionar al menos un producto crudo y un producto maestro.")
            return

        master_id = self.tree_master.item(sel_master[0])['values'][0]
        
        for s in sel_raw:
            vals = self.tree_raw.item(s)['values']
            comercio = vals[0]
            prod_id = vals[1]
            database.add_mapping(comercio, str(prod_id), master_id)
        
        messagebox.showinfo("Éxito", f"Vinculados {len(sel_raw)} productos al maestro {master_id}.")
        self.load_data()

    def create_master_from_raw(self):
        sel_raw = self.tree_raw.selection()
        if not sel_raw:
            messagebox.showwarning("Atención", "Selecciona un producto crudo para crear su maestro.")
            return

        vals = self.tree_raw.item(sel_raw[0])['values']
        comercio, prod_id, nombre, marca, tipo = vals[0], vals[1], vals[2], vals[3], vals[4]
        
        row_query = self.df_raw[(self.df_raw['comercio'] == comercio) & (self.df_raw['producto_id'] == str(prod_id))]
        if row_query.empty:
            return
            
        row = row_query.iloc[0]
        
        nuevo_id = database.add_to_maestro(
            nombre=row['nombre'],
            marca=row['marca'] if pd.notnull(row['marca']) else 'Desconocida',
            tipo=row['tipo_producto'] if pd.notnull(row['tipo_producto']) else 'Alcohol',
            subcategoria='General',
            volumen=row['medida'] if pd.notnull(row['medida']) else 'N/A',
            grados=row['grados_alcohol'] if pd.notnull(row['grados_alcohol']) else 'N/A'
        )
        
        for s in sel_raw:
            v = self.tree_raw.item(s)['values']
            database.add_mapping(v[0], str(v[1]), nuevo_id)
            
        messagebox.showinfo("Éxito", f"Maestro creado con código {nuevo_id} y vinculado automáticamente.")
        self.load_data()

    def run_etl(self):
        if messagebox.askyesno("Confirmar", "¿Ejecutar proceso ETL para poblar la tabla Normalizada?"):
            try:
                database.run_normalization_etl()
                messagebox.showinfo("Éxito", "Proceso ETL de normalización completado con éxito.\nAhora puedes consultar la tabla 'productos_normalizados' en la base de datos.")
            except Exception as e:
                messagebox.showerror("Error", f"Fallo al ejecutar ETL: {e}")

    def auto_map(self):
        import difflib
        if self.df_raw.empty or self.df_master.empty:
            messagebox.showinfo("Info", "Se requieren productos sin mapear y productos en el maestro.")
            return
            
        mapped_count = 0
        maestro_names = self.df_master['nombre_estandar'].tolist()
        
        for _, r in self.df_raw.iterrows():
            matches = difflib.get_close_matches(str(r['nombre']), maestro_names, n=1, cutoff=0.85)
            if matches:
                matched_name = matches[0]
                master_row = self.df_master[self.df_master['nombre_estandar'] == matched_name].iloc[0]
                master_id = master_row['codigo_universal']
                database.add_mapping(r['comercio'], str(r['producto_id']), master_id)
                mapped_count += 1
                
        messagebox.showinfo("Auto-Mapeo", f"Se mapearon automáticamente {mapped_count} productos usando similitud de texto.")
        self.load_data()

    def auto_map_deepseek(self):
        import os
        import json
        import threading
        try:
            from openai import OpenAI
        except ImportError:
            messagebox.showerror("Error", "La librería 'openai' no está instalada. Se requiere para conectar con DeepSeek.")
            return
        
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            messagebox.showerror("Error", "No se encontró DEEPSEEK_API_KEY en el archivo .env")
            return
            
        if self.df_raw.empty or self.df_master.empty:
            messagebox.showinfo("Info", "Se requieren productos sin mapear y productos en el maestro.")
            return

        self.btn_auto_ai.configure(state="disabled", text="Procesando...")
        
        def _run_ai():
            try:
                client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                
                master_list = [{"codigo": r['codigo_universal'], "nombre": r['nombre_estandar']} for _, r in self.df_master.iterrows()]
                
                total_mapped = 0
                chunk_size = 30
                total_raw = len(self.df_raw)
                
                for i in range(0, total_raw, chunk_size):
                    self.after(0, lambda i=i, t=total_raw: self.btn_auto_ai.configure(text=f"Procesando {i}/{t}..."))
                    
                    raw_sample = self.df_raw.iloc[i:i+chunk_size]
                    raw_list = [{"id": f"{r['comercio']}__{r['producto_id']}", "nombre": r['nombre']} for _, r in raw_sample.iterrows()]
                    
                    prompt = f"""
Eres un experto en MDM.
Tengo un diccionario MAESTRO de productos y una lista de productos CRUDOS.
Para cada producto crudo, encuentra si existe en el maestro basándote en el nombre.
Si NO existe, debes marcarlo como "es_nuevo": true y proporcionar un nombre_estandar limpio, la marca, y el tipo (Alcohol, Tabaco, Ultraprocesados).

MAESTRO:
{json.dumps(master_list, ensure_ascii=False)}

CRUDOS a procesar:
{json.dumps(raw_list, ensure_ascii=False)}

Devuelve ÚNICAMENTE un JSON array con los resultados para todos los crudos:
[ 
  {{"crudo_id": "Comercio__1234", "maestro_codigo": "EAN_123", "es_nuevo": false}},
  {{"crudo_id": "Comercio__5678", "maestro_codigo": null, "es_nuevo": true, "nombre_estandar": "Ron Ficticio Añejo", "marca": "Ficticio", "tipo": "Alcohol"}}
]
NO escribas markdown, solo JSON puro.
"""
                    
                    response = client.chat.completions.create(
                        model="deepseek-v4-flash",
                        messages=[
                            {"role": "system", "content": "You are a helpful data mapping assistant. Output pure JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0
                    )
                    
                    text_response = response.choices[0].message.content.strip()
                    text_response = text_response.replace("```json", "").replace("```", "").strip()
                    
                    try:
                        mappings = json.loads(text_response)
                        for m in mappings:
                            crudo_id = m.get("crudo_id")
                            if not crudo_id or "__" not in crudo_id:
                                continue
                                
                            comercio, prod_id = crudo_id.split("__", 1)
                            import database
                            
                            if m.get("es_nuevo"):
                                nuevo_id = database.add_to_maestro(
                                    nombre=m.get("nombre_estandar", "Desconocido"),
                                    marca=m.get("marca", "Desconocida"),
                                    tipo=m.get("tipo", "Alcohol"),
                                    subcategoria="General",
                                    volumen="N/A",
                                    grados="N/A"
                                )
                                database.add_mapping(comercio, prod_id, nuevo_id)
                                total_mapped += 1
                                master_list.append({"codigo": nuevo_id, "nombre": m.get("nombre_estandar", "Desconocido")})
                            else:
                                codigo = m.get("maestro_codigo")
                                if codigo:
                                    database.add_mapping(comercio, prod_id, codigo)
                                    total_mapped += 1
                    except Exception as ex:
                        print(f"Error parsing JSON chunk: {ex}")
                        
                self.after(0, lambda: messagebox.showinfo("Auto-Mapeo IA", f"Proceso finalizado. Se mapearon {total_mapped} productos en total."))
                self.after(0, self.load_data)
                
            except Exception as e:
                self.after(0, lambda e=e: messagebox.showerror("Error IA", str(e)))
            finally:
                self.after(0, lambda: self.btn_auto_ai.configure(state="normal", text="🧠 Auto-Mapeo (DeepSeek)"))

        threading.Thread(target=_run_ai, daemon=True).start()

if __name__ == "__main__":
    app = App()
    app.mainloop()
