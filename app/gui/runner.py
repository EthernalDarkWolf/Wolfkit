import customtkinter as ctk
import sqlite3
import tkinter as tk
import io
import threading
from datetime import date
from pathlib import Path
from tkinter import messagebox, simpledialog, filedialog
from PIL import ImageDraw

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

try:
    import psutil as _psutil
except ImportError:
    _psutil = None

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from app import APP_NAME
from .base import GuiArchitect
from app.utils.db import (
    init_db,
    delete_all_students,
    delete_student,
    insert_or_update_attendance,
    insert_or_update_note,
    insert_or_update_unit,
    select_attendance_types,
    select_history,
    select_notes,
    select_semesters,
    select_students,
    select_today_attendance,
    select_units,
    delete_unit,
    delete_note,
    insert_student,
    update_student,
    update_unit,
    get_connection,
    update_user_profile_pic,
    get_user_profile_pic,
    update_user_credentials,
    get_user_credentials,
)



def get_widget_bg(widget):
    bg = widget.cget("fg_color")
    if isinstance(bg, (list, tuple)):
        return bg[1] if len(bg) > 1 else bg[0]
    if bg == "transparent" or not bg:
        parent = widget.master
        while parent:
            try:
                p_bg = parent.cget("fg_color")
                if p_bg and p_bg != "transparent":
                    if isinstance(p_bg, (list, tuple)):
                        return p_bg[1] if len(p_bg) > 1 else p_bg[0]
                    return p_bg
            except Exception:
                pass
            parent = parent.master
        return "#2f2f2f"
    return bg


def bind_mouse_wheel_recursive(widget, scrollable_frame):
    """Recursively binds the MouseWheel event of a widget and its children to scroll the given CTkScrollableFrame."""
    def on_mouse_wheel(event):
        if hasattr(scrollable_frame, "_canvas"):
            try:
                scrollable_frame._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

    widget.bind("<MouseWheel>", on_mouse_wheel, add="+")
    for child in widget.winfo_children():
        bind_mouse_wheel_recursive(child, scrollable_frame)


class SidebarTabView:
    def __init__(self, parent, sidebar_parent, app_instance):
        self.parent = parent
        self.sidebar_parent = sidebar_parent
        self.app_instance = app_instance
        self.frames = {}
        self.buttons = {}
        self.active_tab = None

        self.ui_order = []  # list of tuples: ('tab', name) or ('group', name)
        self.groups = {}    # name -> dict

        self._build_sidebar_header()

    def _build_sidebar_header(self):
        # 1. Profile Avatar Canvas with pointer cursor
        self.avatar_canvas = tk.Canvas(self.sidebar_parent, width=110, height=110, bg="#1b1c2b", highlightthickness=0, cursor="hand2")
        self.avatar_canvas.pack(pady=(25, 8))

        # 2. Username label with pointer cursor
        self.username_label = ctk.CTkLabel(
            self.sidebar_parent,
            text="",
            font=("Arial", 14, "bold"),
            text_color="#ffffff",
            cursor="hand2"
        )
        self.username_label.pack(pady=(0, 15))

        # Bind clicks
        self.avatar_canvas.bind("<Button-1>", lambda event: self.app_instance.open_user_settings())
        self.username_label.bind("<Button-1>", lambda event: self.app_instance.open_user_settings())

        # Render avatar and username
        self.refresh_avatar()

        # 3. Search Bar
        self.search_entry = ctk.CTkEntry(
            self.sidebar_parent,
            placeholder_text="SEARCH",
            placeholder_text_color="#6b6d85",
            fg_color="#141520",
            text_color="#ffffff",
            border_color="#2c2e3e",
            corner_radius=8,
            height=32
        )
        self.search_entry.pack(fill="x", padx=16, pady=(0, 20))

    def refresh_avatar(self):
        if not self.avatar_canvas.winfo_exists():
            return

        self.avatar_canvas.delete("all")
        
        img_bytes = get_user_profile_pic(self.app_instance.username)
        if img_bytes and Image is not None:
            try:
                pil_img = Image.open(io.BytesIO(img_bytes))
                pil_img = pil_img.resize((80, 80), Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
                
                # Apply circular mask
                mask = Image.new("L", (80, 80), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, 80, 80), fill=255)
                
                circular_img = Image.new("RGBA", (80, 80), (0,0,0,0))
                circular_img.paste(pil_img, (0, 0), mask=mask)
                
                self.photo_image = ImageTk.PhotoImage(circular_img)
                self.avatar_canvas.create_image(55, 55, image=self.photo_image)
                self.avatar_canvas.create_oval(15, 15, 95, 95, outline="#ffffff", width=2)
            except Exception:
                self._draw_default_avatar()
        else:
            self._draw_default_avatar()

        username_text = (self.app_instance.username or "LOREM IPSUM").upper()
        self.username_label.configure(text=username_text)

    def _draw_default_avatar(self):
        self.avatar_canvas.create_oval(15, 15, 95, 95, outline="#ffffff", width=2)
        self.avatar_canvas.create_oval(40, 30, 70, 60, fill="#ffffff", outline="")
        self.avatar_canvas.create_arc(25, 65, 85, 125, start=0, extent=180, fill="#ffffff", outline="")

    def add_group(self, name, icon_text):
        btn = ctk.CTkButton(
            self.sidebar_parent,
            text=icon_text + "  ▼",
            anchor="w",
            fg_color="transparent",
            text_color="#ffffff",
            hover_color="#212338",
            height=42,
            corner_radius=8,
            font=("Arial", 11, "bold"),
            command=lambda g=name: self.toggle_group(g)
        )
        self.groups[name] = {
            'icon_text': icon_text,
            'items': [],
            'expanded': True,
            'button': btn
        }
        self.ui_order.append(('group', name))
        self._repack_buttons()

    def toggle_group(self, name):
        self.groups[name]['expanded'] = not self.groups[name]['expanded']
        icon = self.groups[name]['icon_text']
        arrow = "  ▼" if self.groups[name]['expanded'] else "  ▲"
        self.groups[name]['button'].configure(text=icon + arrow)
        self._repack_buttons()

    def _repack_buttons(self):
        for g in self.groups.values():
            g['button'].pack_forget()
        for b in self.buttons.values():
            b.pack_forget()

        for item_type, name in self.ui_order:
            if item_type == 'tab':
                if name == "Alojamiento":
                    if self.active_tab in ["Servidor", "Alojamiento"]:
                        self.buttons[name].pack(fill="x", padx=12, pady=4)
                else:
                    self.buttons[name].pack(fill="x", padx=12, pady=4)
            elif item_type == 'group':
                group = self.groups[name]
                group['button'].pack(fill="x", padx=12, pady=4)
                if group['expanded']:
                    for item in group['items']:
                        self.buttons[item].pack(fill="x", padx=12, pady=4)

    def add(self, name, group=None):
        frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.frames[name] = frame

        # Map tab names to mockup sidebar names and icons
        icon_text = ""
        if name == "Servidor":
            icon_text = "⚡  SERVIDOR"
        elif name == "Alojamiento":
            icon_text = "   ↳  ALOJAMIENTO"
        elif name == "Inicio":
            icon_text = "☖  DASHBOARD"
        elif name == "Estudiantes":
            icon_text = "田  ESTUDIANTES"
        elif name == "Asistencia":
            icon_text = "✓  ASISTENCIA"
        elif name == "Notas":
            icon_text = "✉  NOTAS"
        elif name == "Unidades":
            icon_text = "☰  UNIDADES"
        elif name == "Administración":
            icon_text = "⚙  ADMIN"
        else:
            icon_text = f"•  {name.upper()}"

        if group:
            icon_text = "   " + icon_text

        btn = ctk.CTkButton(
            self.sidebar_parent,
            text=icon_text,
            anchor="w",
            fg_color="transparent",
            text_color="#8c8da5",
            hover_color="#212338",
            height=42,
            corner_radius=8,
            font=("Arial", 11, "bold"),
            command=lambda n=name: self.set(n)
        )
        self.buttons[name] = btn

        if group and group in self.groups:
            self.groups[group]['items'].append(name)
        else:
            self.ui_order.append(('tab', name))

        self._repack_buttons()
        return frame

    def tab(self, name):
        return self.frames[name]

    def set(self, name):
        # Hide all frames
        for f in self.frames.values():
            f.pack_forget()
        
        # Show selected frame
        if name in self.frames:
            self.frames[name].pack(fill="both", expand=True)

        # Update button colors
        for tab_name, btn in self.buttons.items():
            if tab_name == name:
                btn.configure(fg_color="#212338", text_color="#ffffff")
            else:
                btn.configure(fg_color="transparent", text_color="#8c8da5")

        self.active_tab = name
        self._repack_buttons()

        # Refresh dashboard if entering Inicio
        if name == "Inicio" and hasattr(self.app_instance, "_refresh_dashboard"):
            self.app_instance._refresh_dashboard()


from .dashboard.frontend import DashboardMixin
from .estudiantes.frontend import EstudiantesMixin
from .asistencia.frontend import AsistenciaMixin
from .notas.frontend import NotasMixin
from .unidades.frontend import UnidadesMixin
from .admin.frontend import AdminMixin
from .servidor.frontend import ServidorMixin
from .alojamiento.frontend import AlojamientoMixin
from .acp.frontend import ACPMixin

class RunnerApp(GuiArchitect, DashboardMixin, EstudiantesMixin, AsistenciaMixin, NotasMixin, UnidadesMixin, AdminMixin, ServidorMixin, AlojamientoMixin, ACPMixin):
    def __init__(self, username=None, user_role=None):
        init_db()
        title = f"{APP_NAME} - Control de Estudiantes - {username}" if username else f"{APP_NAME} - Control de Estudiantes y Asistencias"
        super().__init__(title=title)

        self.username = username
        self.user_role = user_role
        self.selected_student_id = None
        self.semester_options = {}
        self.student_options = {}
        self.delete_student_options = {}
        self.notes_student_options = {}
        self.notes_unit_options = {}
        self.note_unit_var = ctk.StringVar(value="")
        self.attendance_types = {}
        self.filter_semester_options = {}
        self.filter_period_options = {}
        self.notes_filter_semester_options = {}
        self.notes_filter_period_options = {}
        self.units_filter_semester_options = {}
        self.units_filter_period_options = {}

        # Configurar la cuadricula de body para separar la barra lateral del contenido
        self.body.grid_columnconfigure(0, weight=0)
        self.body.grid_columnconfigure(1, weight=1)
        self.body.grid_rowconfigure(0, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self.body, width=220, fg_color="#1b1c2b", corner_radius=15)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        self.main_content_container = ctk.CTkFrame(self.body, fg_color="transparent")
        self.main_content_container.grid(row=0, column=1, sticky="nsew")

        self.tabview = SidebarTabView(self.main_content_container, self.sidebar_frame, self)
        self.tabview.add("Servidor")
        self.tabview.add("Alojamiento")
        self.tabview.add("ACP")
        self.tabview.add_group("Educación", "🎓  EDUCACIÓN")
        self.tabview.add("Inicio", group="Educación")
        self.tabview.add("Estudiantes", group="Educación")
        self.tabview.add("Asistencia", group="Educación")
        self.tabview.add("Notas", group="Educación")
        self.tabview.add("Unidades", group="Educación")
        self.tabview.add("Administración", group="Educación")

        self._build_server_tab()
        self._build_alojamiento_tab()
        self._build_home_tab()
        self._build_students_tab()
        self._build_attendance_tab()
        self._build_notes_tab()
        self._build_units_tab()
        self._build_admin_tab()
        self._build_acp_tab()
        self.refresh_semesters()
        self.refresh_attendance_filters()
        self.refresh_notes_filters()
        self.refresh_units_filters()
        self.refresh_admin_filters()
        self.refresh_student_list()
        self.refresh_student_menu()
        self.refresh_notes_student_menu()
        self.refresh_units_list()
        # Asegurar que el menú de unidades en Notas quede cargado
        try:
            self.refresh_note_units_menu()
        except Exception:
            pass
        self.refresh_delete_menu()
        self.tabview.set("Inicio")

        # Safely shut down all background server processes on exit
        def on_app_close():
            try:
                from app.utils.server_manager import ServerManager
                ServerManager().shutdown_all()
            except Exception:
                pass
            self.quit()

        self.protocol("WM_DELETE_WINDOW", on_app_close)

