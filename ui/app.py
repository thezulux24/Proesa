import os
import threading
import customtkinter as ctk
from PIL import Image
import database
from core import replica
from ui.styles import configure_treeview_style
from ui.views.extraction_view import ExtraccionFrame
from ui.views.raw_viewer_view import DataViewerFrame
from ui.views.normalized_viewer_view import NormalizedViewerFrame
from ui.views.analysis_view import UnifiedAnalysisFrame
from ui.views.standardization_view import UnifiedStandardizationFrame

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class DataSuiteApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        db = database.DataSuiteDB()
        db.init_db()

        # Backup diario de la maestra y réplica siempre al día con lo que se edite en la suite
        threading.Thread(target=replica.hacer_backup, kwargs={"solo_si_no_hay_hoy": True}, daemon=True).start()
        self._firma_publicada = None
        self._firma_vista = replica.firma_maestra()
        self._publicando = False
        self.after(1000, self._sincronizar_replica)
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)
        
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
        base_dir = os.path.dirname(os.path.dirname(__file__))
        logo_path = os.path.join(base_dir, "logo.webp")
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

    def _sincronizar_replica(self):
        """Cada 30 s: si la maestra cambió y ya no se está escribiendo, republica la réplica."""
        firma = replica.firma_maestra()
        if not self._publicando and firma != self._firma_publicada and firma == self._firma_vista:
            self._publicando = True
            threading.Thread(target=self._publicar_replica, args=(firma,), daemon=True).start()
        self._firma_vista = firma
        self.after(30000, self._sincronizar_replica)

    def _publicar_replica(self, firma):
        try:
            replica.publicar_replica()
            self._firma_publicada = firma
        except Exception as e:
            print(f"[REPLICA] No se pudo publicar la réplica (se reintenta en 30 s): {e}")
        finally:
            self._publicando = False

    def _al_cerrar(self):
        if not self._publicando and replica.firma_maestra() != self._firma_publicada:
            try:
                replica.publicar_replica()
            except Exception as e:
                print(f"[REPLICA] No se pudo publicar la réplica al cerrar: {e}")
        self.destroy()

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
