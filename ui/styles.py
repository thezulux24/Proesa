from tkinter import ttk

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
    else:
        bg_color = "#1f2937"
        fg_color = "#f9fafb"
        heading_bg = "#374151"
        heading_fg = "#f9fafb"
        select_bg = "#2563eb"
        select_fg = "#ffffff"

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
