import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import matplotlib.ticker as ticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import database
from ui.components.modals import DateRangeModal

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
