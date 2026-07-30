import datetime
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
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
