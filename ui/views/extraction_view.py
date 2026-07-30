import subprocess
import threading
import customtkinter as ctk
import tkinter as tk

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
