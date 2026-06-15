import customtkinter as ctk
import sqlite3
import tkinter as tk
import io
from datetime import date
from pathlib import Path
from tkinter import messagebox, simpledialog, filedialog
from PIL import ImageDraw

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

from app import APP_NAME
from .base import GuiArchitect
from ..utils.db import (
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


class SidebarTabView:
    def __init__(self, parent, sidebar_parent, app_instance):
        self.parent = parent
        self.sidebar_parent = sidebar_parent
        self.app_instance = app_instance
        self.frames = {}
        self.buttons = {}
        self.active_tab = None

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

    def add(self, name):
        frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.frames[name] = frame

        # Map tab names to mockup sidebar names and icons
        icon_text = ""
        if name == "Inicio":
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
        btn.pack(fill="x", padx=12, pady=4)
        self.buttons[name] = btn
        return frame

    def tab(self, name):
        return self.frames[name]

    def set(self, name):
        # Hide all frames
        for f in self.frames.values():
            f.pack_forget()
        
        # Show selected frame
        self.frames[name].pack(fill="both", expand=True)

        # Update button colors
        for tab_name, btn in self.buttons.items():
            if tab_name == name:
                btn.configure(fg_color="#212338", text_color="#ffffff")
            else:
                btn.configure(fg_color="transparent", text_color="#8c8da5")

        self.active_tab = name
        # Refresh dashboard if entering Inicio
        if name == "Inicio" and hasattr(self.app_instance, "_refresh_dashboard"):
            self.app_instance._refresh_dashboard()


class AttendanceApp(GuiArchitect):
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
        self.tabview.add("Inicio")
        self.tabview.add("Estudiantes")
        self.tabview.add("Asistencia")
        self.tabview.add("Notas")
        self.tabview.add("Unidades")
        self.tabview.add("Administración")

        self._build_home_tab()
        self._build_students_tab()
        self._build_attendance_tab()
        self._build_notes_tab()
        self._build_units_tab()
        self._build_admin_tab()
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

    def _build_home_tab(self):
        tab = self.tabview.tab("Inicio")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=0) # Cabecera
        tab.grid_rowconfigure(1, weight=0) # Tarjetas
        tab.grid_rowconfigure(2, weight=1) # Gráficos

        # 1. Cabecera (Top bar)
        header_frame = ctk.CTkFrame(tab, fg_color="transparent", height=50)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 15))
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=0)

        # Nombre del panel a la izquierda
        ctk.CTkLabel(
            header_frame,
            text="WOLFKIT DASHBOARD",
            font=("Arial", 18, "bold"),
            text_color="#ffffff"
        ).grid(row=0, column=0, sticky="w")

        # Elementos a la derecha de la cabecera (Icono de correo con alerta y buscador estético)
        right_header = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_header.grid(row=0, column=1, sticky="e")

        # Icono de sobre con alerta en canvas
        mail_canvas = tk.Canvas(right_header, width=45, height=35, bg=get_widget_bg(right_header), highlightthickness=0)
        mail_canvas.pack(side="left", padx=(0, 10))
        # Dibujar sobre
        mail_canvas.create_rectangle(6, 11, 32, 29, outline="#8c8da5", width=2)
        # Dibujar líneas del sobre
        mail_canvas.create_line(6, 11, 19, 20, fill="#8c8da5", width=2)
        mail_canvas.create_line(32, 11, 19, 20, fill="#8c8da5", width=2)
        # Dibujar alerta roja
        mail_canvas.create_oval(25, 4, 37, 16, fill="#ff4757", outline="")
        mail_canvas.create_text(31, 10, text="1", fill="#ffffff", font=("Arial", 8, "bold"))

        # Pills/details capsule input
        top_pill = ctk.CTkEntry(
            right_header,
            width=140,
            height=28,
            fg_color="#ffffff",
            text_color="#1c1e2f",
            corner_radius=15,
            border_width=0,
            placeholder_text=""
        )
        top_pill.pack(side="left")

        # 2. Tarjetas de Métricas (Fila del medio)
        cards_frame = ctk.CTkFrame(tab, fg_color="transparent")
        cards_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 15))
        cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

        card_colors = [
            ("#ff5e62", "#ff9966", "pink"), # Card 1 (Red/Pink gradient)
            ("#a860f4", "#e29bf4", "purple"), # Card 2 (Purple gradient)
            ("#3a8ef6", "#6bf4ff", "blue") # Card 3 (Blue gradient)
        ]
        
        self.student_stat_label = None
        self.attendance_stat_label = None
        self.units_stat_label = None

        # Card 1: Estudiantes
        c1 = ctk.CTkFrame(cards_frame, fg_color="#1e1e2d", corner_radius=12, height=130)
        c1.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        c1.grid_propagate(False)
        self._build_metric_card(c1, "ESTUDIANTES", "0", "Total registrados", card_colors[0], "bar_chart")

        # Card 2: Asistencia Hoy
        c2 = ctk.CTkFrame(cards_frame, fg_color="#1e1e2d", corner_radius=12, height=130)
        c2.grid(row=0, column=1, sticky="nsew", padx=5)
        c2.grid_propagate(False)
        self._build_metric_card(c2, "ASISTENCIA HOY", "0", "Registradas hoy", card_colors[1], "thumbs_up")

        # Card 3: Unidades
        c3 = ctk.CTkFrame(cards_frame, fg_color="#1e1e2d", corner_radius=12, height=130)
        c3.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        c3.grid_propagate(False)
        self._build_metric_card(c3, "UNIDADES ACTIVAS", "0", "Creadas en total", card_colors[2], "clock")

        # 3. Gráficos en cuadrícula (Fila inferior)
        charts_container = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        charts_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        charts_container.grid_columnconfigure((0, 1), weight=1)
        
        # 1. Donut Chart Card (Left, Row 0)
        donut_card = ctk.CTkFrame(charts_container, fg_color="#1e1e2d", corner_radius=12, height=220)
        donut_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 12))
        donut_card.grid_propagate(False)
        self._setup_donut_card(donut_card)

        # 2. Bar Chart Card (Right, Row 0)
        bar_card = ctk.CTkFrame(charts_container, fg_color="#1e1e2d", corner_radius=12, height=220)
        bar_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 12))
        bar_card.grid_propagate(False)
        self._setup_bar_card(bar_card)

        # 3. Line Chart Card (Left, Row 1)
        line_card = ctk.CTkFrame(charts_container, fg_color="#1e1e2d", corner_radius=12, height=220)
        line_card.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=4)
        line_card.grid_propagate(False)
        self._setup_line_card(line_card)

        # 4. Progress Bars Card (Right, Row 1)
        progress_card = ctk.CTkFrame(charts_container, fg_color="#1e1e2d", corner_radius=12, height=220)
        progress_card.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=4)
        progress_card.grid_propagate(False)
        self._setup_progress_card(progress_card)

    def _build_metric_card(self, parent, title, val_str, sub_str, colors, icon_type):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=0) # Top banner Canvas
        parent.grid_rowconfigure(1, weight=1) # Value
        parent.grid_rowconfigure(2, weight=0) # Subtext

        bg_color = "#1e1e2d"

        banner_canvas = tk.Canvas(parent, height=45, bg=bg_color, highlightthickness=0)
        banner_canvas.grid(row=0, column=0, sticky="ew")

        def draw_banner(event, bc=banner_canvas, cols=colors, t=title, it=icon_type):
            w = event.width
            h = event.height
            bc.delete("all")
            arrow_w = 24
            arrow_h = 8
            cx = w / 2
            
            points = [
                0, 0,
                w, 0,
                w, 35,
                cx + arrow_w/2, 35,
                cx, 35 + arrow_h,
                cx - arrow_w/2, 35,
                0, 35
            ]
            
            bc.create_polygon(points, fill=cols[0], outline="")
            bc.create_text(cx, 16, text=t, fill="#ffffff", font=("Arial", 9, "bold"))

            icon_y = 35
            bc.create_oval(cx - 12, icon_y - 12, cx + 12, icon_y + 12, fill=cols[0], outline="#ffffff", width=1.5)
            
            if it == "bar_chart":
                bc.create_rectangle(cx - 6, icon_y + 4, cx - 3, icon_y - 2, fill="#ffffff", outline="")
                bc.create_rectangle(cx - 2, icon_y + 4, cx + 1, icon_y - 6, fill="#ffffff", outline="")
                bc.create_rectangle(cx + 2, icon_y + 4, cx + 5, icon_y + 0, fill="#ffffff", outline="")
            elif it == "thumbs_up":
                bc.create_polygon(
                    cx - 3, icon_y - 6,
                    cx + 3, icon_y - 1,
                    cx + 1, icon_y + 0,
                    cx + 4, icon_y + 4,
                    cx + 2, icon_y + 5,
                    cx - 1, icon_y + 1,
                    cx - 3, icon_y + 3,
                    fill="#ffffff", outline=""
                )
            elif it == "clock":
                bc.create_oval(cx - 6, icon_y - 6, cx + 6, icon_y + 6, outline="#ffffff", width=1.5)
                bc.create_line(cx, icon_y, cx, icon_y - 4, fill="#ffffff", width=1.5)
                bc.create_line(cx, icon_y, cx + 3, icon_y, fill="#ffffff", width=1.5)

        banner_canvas.bind("<Configure>", draw_banner)

        val_label = ctk.CTkLabel(
            parent,
            text=val_str,
            font=("Arial", 22, "bold"),
            text_color="#ffffff"
        )
        val_label.grid(row=1, column=0, sticky="nsew", pady=(10, 5))

        if title == "ESTUDIANTES":
            self.student_stat_label = val_label
        elif title == "ASISTENCIA HOY":
            self.attendance_stat_label = val_label
        elif title == "UNIDADES ACTIVAS":
            self.units_stat_label = val_label

        sub_frame = ctk.CTkFrame(parent, fg_color="transparent")
        sub_frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        sub_frame.grid_columnconfigure(0, weight=1)

        triangle_canvas = tk.Canvas(sub_frame, width=15, height=12, bg=bg_color, highlightthickness=0)
        triangle_canvas.pack(side="left", padx=(15, 5))
        triangle_canvas.create_polygon(3, 2, 11, 6, 3, 10, fill=colors[0], outline="")

        ctk.CTkLabel(
            sub_frame,
            text=sub_str,
            font=("Arial", 10),
            text_color="#8c8da5"
        ).pack(side="left")

    def _setup_donut_card(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=0)
        parent.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            parent,
            text="ASISTENCIA DE HOY",
            font=("Arial", 11, "bold"),
            text_color="#ffffff",
            anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 5))

        self.donut_canvas = tk.Canvas(parent, bg="#1e1e2d", highlightthickness=0)
        self.donut_canvas.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.donut_canvas.bind("<Configure>", lambda e: self._refresh_donut_chart())

    def _refresh_donut_chart(self):
        if not hasattr(self, "donut_canvas") or not self.donut_canvas.winfo_exists():
            return
        
        self.donut_canvas.delete("all")
        w = self.donut_canvas.winfo_width()
        h = self.donut_canvas.winfo_height()
        if w < 10 or h < 10:
            return

        today_str = date.today().isoformat()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) FROM asistencia_estudiantes 
            WHERE fecha = ? AND asistio_a_clases = (SELECT id_asist FROM asist WHERE nombre_asistencia = 'Asistió')
            """,
            (today_str,)
        )
        present_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*) FROM asistencia_estudiantes 
            WHERE fecha = ? AND asistio_a_clases = (SELECT id_asist FROM asist WHERE nombre_asistencia = 'No Asistió')
            """,
            (today_str,)
        )
        absent_count = cursor.fetchone()[0]
        conn.close()

        total = present_count + absent_count
        if total == 0:
            present_pct = 75.0
            absent_pct = 25.0
            present_val = "75%"
            absent_val = "25%"
        else:
            present_pct = (present_count / total) * 100.0
            absent_pct = (absent_count / total) * 100.0
            present_val = f"{int(present_pct)}%"
            absent_val = f"{int(absent_pct)}%"

        slices = [
            (present_pct, "#ff6b8b", f"Presente: {present_val}"),
            (absent_pct, "#a55eea", f"Ausente: {absent_val}"),
        ]
        
        if total == 0:
            slices.append((15.0, "#0fbcf9", "Tarde: 15%"))
            slices[0] = (60.0, "#ff6b8b", "Presente: 60%")
            slices[1] = (25.0, "#a55eea", "Ausente: 25%")
        
        cx = w / 2 - 35
        cy = h / 2
        r = min(cx, cy) - 10
        if r < 10: r = 35

        start_angle = 90
        for pct, color, label in slices:
            if pct <= 0:
                continue
            extent = (pct / 100.0) * 360.0
            self.donut_canvas.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=start_angle, extent=extent,
                fill=color, outline=""
            )
            start_angle += extent

        donut_r = r * 0.6
        self.donut_canvas.create_oval(
            cx - donut_r, cy - donut_r, cx + donut_r, cy + donut_r,
            fill="#1e1e2d", outline=""
        )

        self.donut_canvas.create_text(
            cx, cy - 5,
            text="HOY",
            fill="#8c8da5",
            font=("Arial", 9, "bold")
        )
        self.donut_canvas.create_text(
            cx, cy + 10,
            text=f"{total}" if total > 0 else "N/A",
            fill="#ffffff",
            font=("Arial", 12, "bold")
        )

        legend_x = cx + r + 20
        legend_y = cy - (len(slices) * 15)
        for i, (pct, color, label) in enumerate(slices):
            y = legend_y + (i * 30)
            self.donut_canvas.create_oval(legend_x, y - 5, legend_x + 10, y + 5, fill=color, outline="")
            self.donut_canvas.create_text(
                legend_x + 18, y,
                text=label,
                anchor="w",
                fill="#ffffff",
                font=("Arial", 10, "bold")
            )

    def _setup_bar_card(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=0)
        parent.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            parent,
            text="ESTUDIANTES POR SEMESTRE",
            font=("Arial", 11, "bold"),
            text_color="#ffffff",
            anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 5))

        self.bar_canvas = tk.Canvas(parent, bg="#1e1e2d", highlightthickness=0)
        self.bar_canvas.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.bar_canvas.bind("<Configure>", lambda e: self._refresh_bar_chart())

    def _refresh_bar_chart(self):
        if not hasattr(self, "bar_canvas") or not self.bar_canvas.winfo_exists():
            return
        
        self.bar_canvas.delete("all")
        w = self.bar_canvas.winfo_width()
        h = self.bar_canvas.winfo_height()
        if w < 10 or h < 10:
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.numero_semestre, s.numero_periodo, COUNT(e.id_estudiantes) as count
            FROM semestre_periodo s
            LEFT JOIN estudiantes e ON e.semestre_periodo = s.id_SemestrePeriodo
            GROUP BY s.id_SemestrePeriodo
            ORDER BY s.numero_semestre, s.numero_periodo
            LIMIT 6
            """
        )
        rows = cursor.fetchall()
        conn.close()

        data = []
        if not rows or sum(r["count"] for r in rows) == 0:
            data = [
                ("S1.1", 5),
                ("S1.2", 8),
                ("S1.3", 3),
                ("S2.1", 10),
                ("S2.2", 6),
                ("S2.3", 7)
            ]
        else:
            for r in rows:
                label = f"S{r['numero_semestre']}.{r['numero_periodo']}"
                data.append((label, r["count"]))

        max_val = max(d[1] for d in data) if data else 10
        if max_val == 0: max_val = 10
        max_val = ((max_val // 5) + 1) * 5
        
        chart_top = 20
        chart_bottom = h - 30
        chart_left = 35
        chart_right = w - 15
        chart_height = chart_bottom - chart_top
        chart_width = chart_right - chart_left

        grid_steps = 4
        for i in range(grid_steps + 1):
            val = (max_val / grid_steps) * i
            y = chart_bottom - (val / max_val) * chart_height
            self.bar_canvas.create_line(chart_left, y, chart_right, y, fill="#2c2e3e", dash=(4, 4))
            self.bar_canvas.create_text(chart_left - 10, y, text=f"{int(val)}", fill="#8c8da5", font=("Arial", 8), anchor="e")

        bar_colors = ["#ff6b8b", "#a55eea", "#3867d6"]
        num_categories = len(data)
        category_width = chart_width / num_categories
        bar_width = category_width * 0.5

        for idx, (label, val) in enumerate(data):
            cx = chart_left + (idx * category_width) + (category_width / 2)
            bar_height_pixels = (val / max_val) * chart_height
            
            x0 = cx - (bar_width / 2)
            y0 = chart_bottom - bar_height_pixels
            x1 = cx + (bar_width / 2)
            y1 = chart_bottom

            color = bar_colors[idx % len(bar_colors)]
            self.bar_canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
            self.bar_canvas.create_text(cx, chart_bottom + 12, text=label, fill="#8c8da5", font=("Arial", 8))

    def _setup_line_card(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=0)
        parent.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            parent,
            text="TENDENCIA DE ASISTENCIA",
            font=("Arial", 11, "bold"),
            text_color="#ffffff",
            anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 5))

        self.line_canvas = tk.Canvas(parent, bg="#1e1e2d", highlightthickness=0)
        self.line_canvas.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.line_canvas.bind("<Configure>", lambda e: self._refresh_line_chart())

    def _refresh_line_chart(self):
        if not hasattr(self, "line_canvas") or not self.line_canvas.winfo_exists():
            return
        
        self.line_canvas.delete("all")
        w = self.line_canvas.winfo_width()
        h = self.line_canvas.winfo_height()
        if w < 10 or h < 10:
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT fecha, COUNT(*) as count
            FROM asistencia_estudiantes
            WHERE asistio_a_clases = (SELECT id_asist FROM asist WHERE nombre_asistencia = 'Asistió')
            GROUP BY fecha
            ORDER BY fecha ASC
            LIMIT 7
            """
        )
        rows = cursor.fetchall()
        conn.close()

        chart_top = 20
        chart_bottom = h - 30
        chart_left = 35
        chart_right = w - 15
        chart_height = chart_bottom - chart_top
        chart_width = chart_right - chart_left

        max_val = 50
        grid_steps = 4
        for i in range(grid_steps + 1):
            val = (max_val / grid_steps) * i
            y = chart_bottom - (val / max_val) * chart_height
            self.line_canvas.create_line(chart_left, y, chart_right, y, fill="#2c2e3e", dash=(4, 4))
            self.line_canvas.create_text(chart_left - 10, y, text=f"{int(val)}", fill="#8c8da5", font=("Arial", 8), anchor="e")

        x_labels = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        for idx, lbl in enumerate(x_labels):
            cx = chart_left + (idx * (chart_width / 6))
            self.line_canvas.create_text(cx, chart_bottom + 12, text=lbl, fill="#8c8da5", font=("Arial", 8))

        pts1 = [
            (0, 15), (1, 35), (2, 22), (3, 42), (4, 18), (5, 30), (6, 12)
        ]
        pts2 = [
            (0, 25), (1, 15), (2, 38), (3, 20), (4, 35), (5, 12), (6, 28)
        ]
        pts3 = [
            (0, 32), (1, 28), (2, 14), (3, 30), (4, 25), (5, 45), (6, 38)
        ]

        if rows and len(rows) >= 2:
            max_real = max(r["count"] for r in rows)
            scale = 40.0 / max_real if max_real > 0 else 1.0
            pts3 = []
            for idx, r in enumerate(rows):
                if idx >= 7: break
                pts3.append((idx, r["count"] * scale))

        def draw_curve(points, color, width=2):
            coords = []
            for px, py in points:
                cx = chart_left + (px * (chart_width / 6))
                cy = chart_bottom - (py / max_val) * chart_height
                coords.extend([cx, cy])
            self.line_canvas.create_line(coords, fill=color, width=width, smooth=True, splinesteps=36)

        draw_curve(pts1, "#ff6b8b", width=1.5)
        draw_curve(pts2, "#a55eea", width=1.5)
        draw_curve(pts3, "#3867d6", width=2.5)

    def _setup_progress_card(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=0)
        parent.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            parent,
            text="AVANCE DE UNIDADES POR SEMESTRE",
            font=("Arial", 11, "bold"),
            text_color="#ffffff",
            anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 5))

        self.progress_canvas = tk.Canvas(parent, bg="#1e1e2d", highlightthickness=0)
        self.progress_canvas.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.progress_canvas.bind("<Configure>", lambda e: self._refresh_progress_bars())

    def _refresh_progress_bars(self):
        if not hasattr(self, "progress_canvas") or not self.progress_canvas.winfo_exists():
            return
        
        self.progress_canvas.delete("all")
        w = self.progress_canvas.winfo_width()
        h = self.progress_canvas.winfo_height()
        if w < 10 or h < 10:
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.numero_semestre, s.numero_periodo, 
                   COUNT(u.id_unidad) as total_units,
                   SUM(CASE WHEN u.completada = 1 THEN 1 ELSE 0 END) as completed_units
            FROM semestre_periodo s
            LEFT JOIN unidades u ON u.id_semestre_periodo = s.id_SemestrePeriodo
            GROUP BY s.id_SemestrePeriodo
            ORDER BY s.numero_semestre, s.numero_periodo
            """
        )
        rows = cursor.fetchall()
        conn.close()

        bars_data = []
        has_real_data = False
        if rows:
            for r in rows:
                tot = r["total_units"]
                if tot > 0:
                    pct = int((r["completed_units"] / tot) * 100)
                    label = f"Semestre {r['numero_semestre']} - Periodo {r['numero_periodo']}"
                    bars_data.append((label, pct))
                    has_real_data = True

        if not has_real_data:
            bars_data = [
                ("Semestre 1 - Periodo 1", 80),
                ("Semestre 1 - Periodo 2", 70),
                ("Semestre 1 - Periodo 3", 25)
            ]

        bar_height = 12
        bar_colors = ["#ff6b8b", "#a55eea", "#3867d6"]
        
        start_y = 20
        spacing = 45
        
        for idx, (label, pct) in enumerate(bars_data):
            if idx >= 4: break
            
            y = start_y + (idx * spacing)
            
            self.progress_canvas.create_text(
                10, y,
                text=label.upper(),
                fill="#ffffff",
                font=("Arial", 9, "bold"),
                anchor="w"
            )
            
            bar_y0 = y + 10
            bar_y1 = bar_y0 + bar_height
            bar_max_w = w - 60
            
            self.progress_canvas.create_rectangle(
                10, bar_y0, 10 + bar_max_w, bar_y1,
                fill="#2c2e3e", outline=""
            )
            
            fill_w = (pct / 100.0) * bar_max_w
            if fill_w > 0:
                color = bar_colors[idx % len(bar_colors)]
                self.progress_canvas.create_rectangle(
                    10, bar_y0, 10 + fill_w, bar_y1,
                    fill=color, outline=""
                )
                
            self.progress_canvas.create_text(
                w - 10, y + 16,
                text=f"{pct}%",
                fill="#8c8da5",
                font=("Arial", 9, "bold"),
                anchor="e"
            )

    def _refresh_dashboard(self):
        students = select_students()
        total_students = len(students)
        if hasattr(self, "student_stat_label") and self.student_stat_label:
            self.student_stat_label.configure(text=f"{total_students}")

        today_str = date.today().isoformat()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) FROM asistencia_estudiantes 
            WHERE fecha = ? AND asistio_a_clases = (SELECT id_asist FROM asist WHERE nombre_asistencia = 'Asistió')
            """,
            (today_str,)
        )
        today_asistio = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM unidades")
        total_units = cursor.fetchone()[0]
        conn.close()

        if hasattr(self, "attendance_stat_label") and self.attendance_stat_label:
            self.attendance_stat_label.configure(text=f"{today_asistio}")
            
        if hasattr(self, "units_stat_label") and self.units_stat_label:
            self.units_stat_label.configure(text=f"{total_units}")

        self._refresh_donut_chart()
        self._refresh_bar_chart()
        self._refresh_line_chart()
        self._refresh_progress_bars()

    def _build_students_tab(self):
        tab = self.tabview.tab("Estudiantes")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)

        student_frame = ctk.CTkFrame(tab, fg_color="#242424")
        student_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        student_frame.grid_rowconfigure(2, weight=1)

        self.create_label("Estudiantes registrados", master=student_frame, font=("Arial", 18, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 6)
        )
        self.student_count_label = self.create_label("Cargando estudiantes...", master=student_frame, font=("Arial", 12))
        self.student_count_label.grid(row=1, column=0, sticky="w", padx=14)

        self.student_list_frame = ctk.CTkScrollableFrame(student_frame, fg_color="#2c2c2c", height=380)
        self.student_list_frame.grid(row=2, column=0, sticky="nsew", padx=14, pady=14)

        self.btn_refresh_students = self.create_button("Actualizar lista", command=self.refresh_student_list, master=student_frame)
        self.btn_refresh_students.grid(row=3, column=0, sticky="e", padx=14, pady=(0, 14))

        form_frame = ctk.CTkFrame(tab, fg_color="#242424")
        form_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        form_frame.grid_columnconfigure(1, weight=1)

        self.create_label("Agregar estudiante", master=form_frame, font=("Arial", 18, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 10)
        )

        self.create_label("Nombres:", master=form_frame).grid(row=1, column=0, sticky="w", padx=14, pady=(8, 4))
        self.entry_nombres = self.create_entry("Nombre(s)", master=form_frame)
        self.entry_nombres.grid(row=1, column=1, sticky="ew", padx=14, pady=(8, 4))

        self.create_label("Apellidos:", master=form_frame).grid(row=2, column=0, sticky="w", padx=14, pady=(8, 4))
        self.entry_apellidos = self.create_entry("Apellido(s)", master=form_frame)
        self.entry_apellidos.grid(row=2, column=1, sticky="ew", padx=14, pady=(8, 4))

        self.create_label("Cédula:", master=form_frame).grid(row=3, column=0, sticky="w", padx=14, pady=(8, 4))
        self.entry_ci = self.create_entry("CI", master=form_frame)
        self.entry_ci.grid(row=3, column=1, sticky="ew", padx=14, pady=(8, 4))

        self.create_label("Semestre / Periodo:", master=form_frame).grid(row=4, column=0, sticky="w", padx=14, pady=(8, 4))
        self.semester_menu = ctk.CTkOptionMenu(form_frame, values=[], fg_color="#3a3a3a", button_color="#444444")
        self.semester_menu.grid(row=4, column=1, sticky="ew", padx=14, pady=(8, 4))

        self.btn_add_student = self.create_button("Guardar estudiante", command=self.add_student, master=form_frame)
        self.btn_add_student.grid(row=5, column=0, columnspan=2, sticky="ew", padx=14, pady=14)

        self.add_message_label = self.create_label("", master=form_frame, font=("Arial", 12))
        self.add_message_label.grid(row=6, column=0, columnspan=2, sticky="w", padx=14)

    def _build_attendance_tab(self):
        tab = self.tabview.tab("Asistencia")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)

        control_frame = ctk.CTkFrame(tab, fg_color="#242424")
        control_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        control_frame.grid_columnconfigure(0, weight=1)

        self.create_label("Control de asistencia", master=control_frame, font=("Arial", 18, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 10)
        )

        self.create_label("Semestre:", master=control_frame).grid(row=1, column=0, sticky="w", padx=14, pady=(8, 4))
        self.semester_filter_var = tk.StringVar(value="")
        self.semester_filter_menu = ctk.CTkOptionMenu(
            control_frame,
            values=[],
            variable=self.semester_filter_var,
            fg_color="#3a3a3a",
            button_color="#444444",
            dynamic_resizing=False,
        )
        self.semester_filter_menu.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        self.semester_filter_var.trace_add("write", self._on_semester_filter_changed)

        self.create_label("Periodo:", master=control_frame).grid(row=3, column=0, sticky="w", padx=14, pady=(8, 4))
        self.period_filter_var = tk.StringVar(value="")
        self.period_filter_menu = ctk.CTkOptionMenu(
            control_frame,
            values=[],
            variable=self.period_filter_var,
            fg_color="#3a3a3a",
            button_color="#444444",
            dynamic_resizing=False,
        )
        self.period_filter_menu.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 14))
        self.period_filter_var.trace_add("write", self._on_period_filter_changed)

        self.create_label("Fecha:", master=control_frame).grid(row=5, column=0, sticky="w", padx=14, pady=(8, 4))
        self.date_mode_var = tk.StringVar(value="Default")
        self.date_mode_menu = ctk.CTkOptionMenu(
            control_frame,
            values=["Default", "Establecer fecha"],
            variable=self.date_mode_var,
            fg_color="#3a3a3a",
            button_color="#444444",
            dynamic_resizing=False,
        )
        self.date_mode_menu.grid(row=6, column=0, sticky="ew", padx=14, pady=(0, 14))
        self.date_mode_var.trace_add("write", self._on_date_mode_changed)

        self.date_frame = ctk.CTkFrame(control_frame, fg_color="#2c2c2c")
        self.date_frame.grid(row=7, column=0, sticky="ew", padx=14, pady=(0, 14))
        self.date_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.create_label("Día", master=self.date_frame, font=("Arial", 12)).grid(row=0, column=0, sticky="w", padx=4, pady=(0, 4))
        self.create_label("Mes", master=self.date_frame, font=("Arial", 12)).grid(row=0, column=1, sticky="w", padx=4, pady=(0, 4))
        self.create_label("Año", master=self.date_frame, font=("Arial", 12)).grid(row=0, column=2, sticky="w", padx=4, pady=(0, 4))

        self.date_day_entry = self.create_entry("DD", master=self.date_frame)
        self.date_day_entry.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 4))
        self.date_month_entry = self.create_entry("MM", master=self.date_frame)
        self.date_month_entry.grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 4))
        self.date_year_entry = self.create_entry("YYYY", master=self.date_frame)
        self.date_year_entry.grid(row=1, column=2, sticky="ew", padx=4, pady=(0, 4))
        self.date_frame.grid_remove()

        self.create_label("Selecciona un estudiante:", master=control_frame).grid(
            row=8, column=0, sticky="w", padx=14, pady=(8, 4)
        )
        self.attendance_student_menu = ctk.CTkOptionMenu(
            control_frame,
            values=[],
            fg_color="#3a3a3a",
            button_color="#444444",
            dynamic_resizing=False,
            command=self.on_student_selected,
        )
        self.attendance_student_menu.grid(row=9, column=0, sticky="ew", padx=14, pady=(0, 14))

        self.attendance_status_label = self.create_label("Seleccione un estudiante para ver su asistencia de hoy.", master=control_frame, wraplength=360)
        self.attendance_status_label.grid(row=10, column=0, sticky="w", padx=14, pady=(6, 12))

        buttons_frame = ctk.CTkFrame(control_frame, fg_color="#2c2c2c")
        buttons_frame.grid(row=8, column=0, sticky="ew", padx=14, pady=(0, 14))
        buttons_frame.grid_columnconfigure((0, 1), weight=1)

        self.create_button("Asistió", command=lambda: self.mark_attendance("Asistió"), master=buttons_frame).grid(
            row=0, column=0, sticky="ew", padx=(0, 7), pady=14
        )
        self.create_button("No asistió", command=lambda: self.mark_attendance("No Asistió"), master=buttons_frame).grid(
            row=0, column=1, sticky="ew", padx=(7, 0), pady=14
        )

        self.attendance_message_label = self.create_label("", master=control_frame, font=("Arial", 12))
        self.attendance_message_label.grid(row=11, column=0, sticky="w", padx=14, pady=(0, 8))

        history_frame = ctk.CTkFrame(tab, fg_color="#242424")
        history_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        history_frame.grid_columnconfigure(0, weight=1)
        history_frame.grid_rowconfigure(2, weight=1)

        self.create_label("Historial de asistencia", master=history_frame, font=("Arial", 18, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 10)
        )

        # Etiqueta para mostrar el estudiante cuyo historial se está viendo
        self.history_student_label = self.create_label("", master=history_frame, font=("Arial", 12, "bold"))
        self.history_student_label.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 8))

        self.history_list_frame = ctk.CTkScrollableFrame(history_frame, fg_color="#2c2c2c")
        self.history_list_frame.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))

    def _build_notes_tab(self):
        tab = self.tabview.tab("Notas")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)

        notes_frame = ctk.CTkFrame(tab, fg_color="#242424")
        notes_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        notes_frame.grid_columnconfigure(1, weight=1)

        self.create_label("Registro de notas", master=notes_frame, font=("Arial", 18, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 10)
        )

        self.create_label("Semestre:", master=notes_frame).grid(row=1, column=0, sticky="w", padx=14, pady=(8, 4))
        self.notes_semester_filter_var = tk.StringVar(value="")
        self.notes_semester_filter_menu = ctk.CTkOptionMenu(
            notes_frame,
            values=[],
            variable=self.notes_semester_filter_var,
            fg_color="#3a3a3a",
            button_color="#444444",
            dynamic_resizing=False,
        )
        self.notes_semester_filter_menu.grid(row=1, column=1, sticky="ew", padx=14, pady=(8, 4))
        self.notes_semester_filter_var.trace_add("write", self._on_notes_semester_changed)

        self.create_label("Periodo:", master=notes_frame).grid(row=2, column=0, sticky="w", padx=14, pady=(8, 4))
        self.notes_period_filter_var = tk.StringVar(value="")
        self.notes_period_filter_menu = ctk.CTkOptionMenu(
            notes_frame,
            values=[],
            variable=self.notes_period_filter_var,
            fg_color="#3a3a3a",
            button_color="#444444",
            dynamic_resizing=False,
        )
        self.notes_period_filter_menu.grid(row=2, column=1, sticky="ew", padx=14, pady=(8, 4))
        self.notes_period_filter_var.trace_add("write", self._on_notes_period_changed)

        self.create_label("Selecciona un estudiante:", master=notes_frame).grid(row=3, column=0, sticky="w", padx=14, pady=(8, 4))
        self.notes_student_menu = ctk.CTkOptionMenu(
            notes_frame,
            values=[],
            fg_color="#3a3a3a",
            button_color="#444444",
            dynamic_resizing=False,
            command=self.on_notes_student_selected,
        )
        self.notes_student_menu.grid(row=3, column=1, sticky="ew", padx=14, pady=(8, 4))

        self.create_label("Unidad:", master=notes_frame).grid(row=4, column=0, sticky="w", padx=14, pady=(8, 4))
        self.note_unit_var = tk.StringVar(value="")
        self.note_unit_menu = ctk.CTkOptionMenu(
            notes_frame,
            values=[],
            variable=self.note_unit_var,
            fg_color="#3a3a3a",
            button_color="#444444",
            dynamic_resizing=False,
        )
        self.note_unit_menu.grid(row=4, column=1, sticky="ew", padx=14, pady=(8, 4))
        self.create_button("+", command=self.add_unit_from_notes, master=notes_frame, width=36).grid(row=4, column=2, sticky="w", padx=(6,14), pady=(8,4))

        self.create_label("Nota:", master=notes_frame).grid(row=5, column=0, sticky="w", padx=14, pady=(8, 4))
        self.entry_note_value = self.create_entry("Nota", master=notes_frame)
        self.entry_note_value.grid(row=5, column=1, sticky="ew", padx=14, pady=(8, 4))

        self.create_label("Comentarios:", master=notes_frame).grid(row=6, column=0, sticky="w", padx=14, pady=(8, 4))
        self.entry_note_comments = self.create_entry("Comentarios", master=notes_frame)
        self.entry_note_comments.grid(row=6, column=1, sticky="ew", padx=14, pady=(8, 4))

        self.create_button("Guardar nota", command=self.save_note, master=notes_frame).grid(
            row=7, column=0, columnspan=2, sticky="ew", padx=14, pady=(12, 4)
        )

        self.notes_message_label = self.create_label("", master=notes_frame, font=("Arial", 12))
        self.notes_message_label.grid(row=8, column=0, columnspan=2, sticky="w", padx=14, pady=(4, 14))

        notes_history_frame = ctk.CTkFrame(tab, fg_color="#242424")
        notes_history_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        notes_history_frame.grid_columnconfigure(0, weight=1)
        notes_history_frame.grid_rowconfigure(1, weight=1)

        self.create_label("Notas guardadas", master=notes_history_frame, font=("Arial", 18, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 10)
        )

        # Etiqueta para mostrar el estudiante cuyo registro de notas se está viendo
        self.notes_history_student_label = self.create_label("", master=notes_history_frame, font=("Arial", 12, "bold"))
        self.notes_history_student_label.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 8))

        self.notes_list_frame = ctk.CTkScrollableFrame(notes_history_frame, fg_color="#2c2c2c")
        self.notes_list_frame.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))

    def _build_units_tab(self):
        tab = self.tabview.tab("Unidades")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)

        units_frame = ctk.CTkFrame(tab, fg_color="#242424")
        units_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        units_frame.grid_columnconfigure(1, weight=1)

        self.create_label("Gestión de unidades", master=units_frame, font=("Arial", 18, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 10)
        )

        self.create_label("Semestre:", master=units_frame).grid(row=1, column=0, sticky="w", padx=14, pady=(8, 4))
        self.units_semester_filter_var = tk.StringVar(value="")
        self.units_semester_filter_menu = ctk.CTkOptionMenu(
            units_frame,
            values=[],
            variable=self.units_semester_filter_var,
            fg_color="#3a3a3a",
            button_color="#444444",
            dynamic_resizing=False,
        )
        self.units_semester_filter_menu.grid(row=1, column=1, sticky="ew", padx=14, pady=(8, 4))
        self.units_semester_filter_var.trace_add("write", self._on_units_semester_changed)

        self.create_label("Periodo:", master=units_frame).grid(row=2, column=0, sticky="w", padx=14, pady=(8, 4))
        self.units_period_filter_var = tk.StringVar(value="")
        self.units_period_filter_menu = ctk.CTkOptionMenu(
            units_frame,
            values=[],
            variable=self.units_period_filter_var,
            fg_color="#3a3a3a",
            button_color="#444444",
            dynamic_resizing=False,
        )
        self.units_period_filter_menu.grid(row=2, column=1, sticky="ew", padx=14, pady=(8, 4))
        self.units_period_filter_var.trace_add("write", self._on_units_period_changed)

        self.create_label("Nombre de unidad:", master=units_frame).grid(row=3, column=0, sticky="w", padx=14, pady=(8, 4))
        self.entry_unit_name = self.create_entry("Unidad", master=units_frame)
        self.entry_unit_name.grid(row=3, column=1, sticky="ew", padx=14, pady=(8, 4))

        self.create_label("Contexto:", master=units_frame).grid(row=4, column=0, sticky="nw", padx=14, pady=(8, 4))
        # area multi-line para contexto
        self.entry_unit_context = ctk.CTkTextbox(units_frame, width=320, height=80)
        self.entry_unit_context.grid(row=4, column=1, sticky="ew", padx=14, pady=(8, 4))

        self.create_button("Agregar unidad", command=self.save_unit, master=units_frame).grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=14, pady=(12, 4)
        )

        self.units_message_label = self.create_label("", master=units_frame, font=("Arial", 12))
        self.units_message_label.grid(row=6, column=0, columnspan=2, sticky="w", padx=14, pady=(4, 14))

        units_list_frame = ctk.CTkFrame(tab, fg_color="#242424")
        units_list_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        units_list_frame.grid_columnconfigure(0, weight=1)
        units_list_frame.grid_rowconfigure(1, weight=1)

        self.create_label("Unidades por semestre/periodo", master=units_list_frame, font=("Arial", 18, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 10)
        )

        self.units_list_frame = ctk.CTkScrollableFrame(units_list_frame, fg_color="#2c2c2c")
        self.units_list_frame.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))

    def _build_admin_tab(self):
        tab = self.tabview.tab("Administración")
        tab.grid_columnconfigure(0, weight=1)

        admin_frame = ctk.CTkFrame(tab, fg_color="#242424")
        admin_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        admin_frame.grid_columnconfigure(1, weight=1)

        self.create_label("Administración de estudiantes", master=admin_frame, font=("Arial", 18, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 10)
        )

        self.create_label("Semestre:", master=admin_frame).grid(row=1, column=0, sticky="w", padx=14, pady=(8, 4))
        self.admin_semester_filter_var = tk.StringVar(value="")
        self.admin_semester_filter_menu = ctk.CTkOptionMenu(
            admin_frame,
            values=[],
            variable=self.admin_semester_filter_var,
            fg_color="#3a3a3a",
            button_color="#444444",
            dynamic_resizing=False,
        )
        self.admin_semester_filter_menu.grid(row=1, column=1, sticky="ew", padx=14, pady=(8, 4))
        self.admin_semester_filter_var.trace_add("write", lambda *args: self.on_admin_filter_semester_selected(self.admin_semester_filter_var.get()))

        self.create_label("Periodo:", master=admin_frame).grid(row=2, column=0, sticky="w", padx=14, pady=(8, 4))
        self.admin_period_filter_var = tk.StringVar(value="")
        self.admin_period_filter_menu = ctk.CTkOptionMenu(
            admin_frame,
            values=[],
            variable=self.admin_period_filter_var,
            fg_color="#3a3a3a",
            button_color="#444444",
            dynamic_resizing=False,
        )
        self.admin_period_filter_menu.grid(row=2, column=1, sticky="ew", padx=14, pady=(8, 4))
        self.admin_period_filter_var.trace_add("write", lambda *args: self.on_admin_filter_period_selected(self.admin_period_filter_var.get()))

        self.create_label("Seleccionar estudiante:", master=admin_frame).grid(row=3, column=0, sticky="w", padx=14, pady=(8, 4))
        self.delete_student_menu = ctk.CTkOptionMenu(
            admin_frame,
            values=["No hay estudiantes"],
            fg_color="#3a3a3a",
            button_color="#444444",
            dynamic_resizing=False,
        )
        self.delete_student_menu.grid(row=3, column=1, sticky="ew", padx=14, pady=(8, 4))

        self.create_button(
            "Eliminar todos los estudiantes",
            command=self.confirm_delete_all_students,
            master=admin_frame,
            fg_color="#8a2424",
            hover_color="#a33030",
        ).grid(row=4, column=0, columnspan=2, sticky="ew", padx=14, pady=(8, 4))

        self.admin_message_label = self.create_label("", master=admin_frame, font=("Arial", 12))
        self.admin_message_label.grid(row=5, column=0, columnspan=2, sticky="w", padx=14, pady=(4, 8))

        self.create_label("Estudiantes registrados", master=admin_frame, font=("Arial", 16, "bold")).grid(
            row=7, column=0, columnspan=2, sticky="w", padx=14, pady=(10, 8)
        )

        self.admin_students_list_frame = ctk.CTkScrollableFrame(admin_frame, fg_color="#2c2c2c", height=220)
        self.admin_students_list_frame.grid(row=8, column=0, columnspan=2, sticky="nsew", padx=14, pady=(0, 14))
        admin_frame.grid_rowconfigure(8, weight=1)

    def refresh_semesters(self):
        rows = select_semesters()
        options = []
        self.semester_options = {}
        for row in rows:
            label = f"Sem {row['numero_semestre']} - Periodo {row['numero_periodo']}"
            options.append(label)
            self.semester_options[label] = row["id_SemestrePeriodo"]

        if not options:
            options = []
            for sem in ["1", "2"]:
                for per in ["1", "2", "3"]:
                    label = f"Sem {sem} - Periodo {per}"
                    options.append(label)
                    self.semester_options[label] = None

        self.semester_menu.configure(values=options)
        self.semester_menu.set(options[0])

    def refresh_student_list(self):
        students = select_students()
        for widget in self.student_list_frame.winfo_children():
            widget.destroy()

        total = len(students)
        self.student_count_label.configure(text=f"Total de estudiantes: {total}")

        if total == 0:
            self.create_label("No hay estudiantes registrados.", master=self.student_list_frame, font=("Arial", 12)).pack(padx=14, pady=14)
            return

        for student in students:
            row_text = f"{student['ci']} · {student['nombres']} {student['apellidos']} · Sem {student['numero_semestre']}.{student['numero_periodo']}"
            row_frame = ctk.CTkFrame(self.student_list_frame, fg_color="#303030")
            row_frame.pack(fill="x", padx=8, pady=4)
            self.create_label(row_text, master=row_frame, anchor="w", font=("Arial", 12)).pack(side="left", padx=10, pady=12, fill="x", expand=True)
            self.create_button(
                "Borrar",
                command=lambda student_id=student["id_estudiantes"]: self.delete_single_student(student_id),
                master=row_frame,
                width=100,
                fg_color="#8a2424",
                hover_color="#a33030",
            ).pack(side="right", padx=(0, 10), pady=10)
            self.create_button(
                "Seleccionar",
                command=lambda student=student: self.select_student_for_attendance(student),
                master=row_frame,
                width=120,
            ).pack(side="right", padx=10, pady=10)

    def refresh_student_menu(self):
        students = select_students()
        semester_value = self.semester_filter_menu.get() if hasattr(self, 'semester_filter_menu') else None
        period_value = self.period_filter_menu.get() if hasattr(self, 'period_filter_menu') else None

        values = []
        self.student_options = {}
        for student in students:
            if semester_value and period_value and semester_value != "No hay estudiantes" and period_value != "No hay estudiantes":
                if student["numero_semestre"] != semester_value or student["numero_periodo"] != period_value:
                    continue

            label = f"{student['ci']} · {student['nombres']} {student['apellidos']}"
            values.append(label)
            self.student_options[label] = student["id_estudiantes"]

        if not values:
            values = ["No hay estudiantes"]
            self.attendance_student_menu.configure(values=values)
            self.attendance_student_menu.set(values[0])
            self.selected_student_id = None
            self.attendance_status_label.configure(text="No hay estudiantes para este semestre y periodo.")
            self.refresh_history()
            return

        self.attendance_student_menu.configure(values=values)
        if self.attendance_student_menu.get() not in values:
            self.attendance_student_menu.set(values[0])
        self.on_student_selected(self.attendance_student_menu.get())

    def refresh_attendance_filters(self):
        rows = select_semesters()
        semester_values = []
        self.filter_semester_options = {}
        self.filter_period_options = {}

        for row in rows:
            sem = row["numero_semestre"]
            per = row["numero_periodo"]
            if sem not in self.filter_semester_options:
                self.filter_semester_options[sem] = []
            if per not in self.filter_semester_options[sem]:
                self.filter_semester_options[sem].append(per)

        semester_values = sorted(self.filter_semester_options.keys(), key=lambda x: int(x) if x.isdigit() else x)
        if not semester_values:
            semester_values = ["1", "2"]
            self.filter_semester_options["1"] = ["1", "2", "3"]
            self.filter_semester_options["2"] = ["1", "2", "3"]

        self.semester_filter_menu.configure(values=semester_values)
        self.semester_filter_menu.set(semester_values[0])
        self.semester_filter_var.set(semester_values[0])
        self._update_period_filter_menu()

    def _update_period_filter_menu(self):
        semester_value = self.semester_filter_var.get()
        period_values = self.filter_semester_options.get(semester_value, [])
        if not period_values:
            period_values = ["1"]

        self.period_filter_menu.configure(values=period_values)
        if self.period_filter_var.get() not in period_values:
            self.period_filter_var.set(period_values[0])

    def _on_semester_filter_changed(self, *args):
        self._update_period_filter_menu()
        self.refresh_student_menu()

    def _on_period_filter_changed(self, *args):
        self.refresh_student_menu()

    def refresh_admin_filters(self):
        rows = select_semesters()
        semester_values = []
        self.admin_filter_semester_options = {}

        for row in rows:
            sem = row["numero_semestre"]
            per = row["numero_periodo"]
            if sem not in self.admin_filter_semester_options:
                self.admin_filter_semester_options[sem] = []
            if per not in self.admin_filter_semester_options[sem]:
                self.admin_filter_semester_options[sem].append(per)

        semester_values = sorted(self.admin_filter_semester_options.keys(), key=lambda x: int(x) if x.isdigit() else x)
        if not semester_values:
            semester_values = ["1", "2"]
            self.admin_filter_semester_options["1"] = ["1", "2", "3"]
            self.admin_filter_semester_options["2"] = ["1", "2", "3"]

        self.admin_semester_filter_menu.configure(values=semester_values)
        self.admin_semester_filter_menu.set(semester_values[0])
        self.admin_semester_filter_var.set(semester_values[0])
        self._update_admin_period_filter_menu()

    def refresh_notes_filters(self):
        rows = select_semesters()
        semester_values = []
        self.notes_filter_semester_options = {}

        for row in rows:
            sem = row["numero_semestre"]
            per = row["numero_periodo"]
            if sem not in self.notes_filter_semester_options:
                self.notes_filter_semester_options[sem] = []
            if per not in self.notes_filter_semester_options[sem]:
                self.notes_filter_semester_options[sem].append(per)

        semester_values = sorted(self.notes_filter_semester_options.keys(), key=lambda x: int(x) if x.isdigit() else x)
        if not semester_values:
            semester_values = ["1", "2"]
            self.notes_filter_semester_options["1"] = ["1", "2", "3"]
            self.notes_filter_semester_options["2"] = ["1", "2", "3"]

        self.notes_semester_filter_menu.configure(values=semester_values)
        self.notes_semester_filter_menu.set(semester_values[0])
        self.notes_semester_filter_var.set(semester_values[0])
        self._update_notes_period_filter_menu()

    def _update_notes_period_filter_menu(self):
        semester_value = self.notes_semester_filter_var.get()
        period_values = self.notes_filter_semester_options.get(semester_value, [])
        if not period_values:
            period_values = ["1"]

        self.notes_period_filter_menu.configure(values=period_values)
        if self.notes_period_filter_var.get() not in period_values:
            self.notes_period_filter_var.set(period_values[0])

    def _on_notes_semester_changed(self, *args):
        self._update_notes_period_filter_menu()
        self.refresh_notes_student_menu()
        self.refresh_note_units_menu()

    def _on_notes_period_changed(self, *args):
        self.refresh_notes_student_menu()
        self.refresh_note_units_menu()

    def refresh_note_units_menu(self):
        semester_label = self.notes_semester_filter_var.get() if hasattr(self, 'notes_semester_filter_var') else None
        period_label = self.notes_period_filter_var.get() if hasattr(self, 'notes_period_filter_var') else None
        semester_id = None
        if semester_label and period_label:
            semester_id = next(
                (row["id_SemestrePeriodo"] for row in select_semesters() if row["numero_semestre"] == semester_label and row["numero_periodo"] == period_label),
                None,
            )

        values = []
        self.notes_unit_options = {}
        if semester_id:
            rows = select_units(semester_id)
            for row in rows:
                label = row["nombre_unidad"]
                values.append(label)
                self.notes_unit_options[label] = row["id_unidad"]

        if not values:
            values = ["No hay unidades"]

        self.note_unit_menu.configure(values=values)
        self.note_unit_menu.set(values[0])

    def add_unit_from_notes(self):
        semester_label = self.notes_semester_filter_var.get() if hasattr(self, 'notes_semester_filter_var') else None
        period_label = self.notes_period_filter_var.get() if hasattr(self, 'notes_period_filter_var') else None
        semester_id = None
        if semester_label and period_label:
            semester_id = next(
                (row["id_SemestrePeriodo"] for row in select_semesters() if row["numero_semestre"] == semester_label and row["numero_periodo"] == period_label),
                None,
            )

        if not semester_id:
            messagebox.showwarning("Unidad", "Selecciona primero un semestre y periodo válidos en Notas.")
            return

        nombre = simpledialog.askstring("Agregar unidad", "Nombre de la unidad:")
        if not nombre:
            return

        try:
            contexto = simpledialog.askstring("Contexto (opcional)", "Contexto para la unidad:")
            insert_or_update_unit(nombre.strip(), semester_id, contexto)
            self.notes_message_label.configure(text="Unidad creada.", text_color="#8ee58e")
            self.refresh_note_units_menu()
        except Exception as e:
            self.notes_message_label.configure(text=f"Error al crear unidad: {e}", text_color="#f55a5a")

    def refresh_units_filters(self):
        rows = select_semesters()
        semester_values = []
        self.units_filter_semester_options = {}

        for row in rows:
            sem = row["numero_semestre"]
            per = row["numero_periodo"]
            if sem not in self.units_filter_semester_options:
                self.units_filter_semester_options[sem] = []
            if per not in self.units_filter_semester_options[sem]:
                self.units_filter_semester_options[sem].append(per)

        semester_values = sorted(self.units_filter_semester_options.keys(), key=lambda x: int(x) if x.isdigit() else x)
        if not semester_values:
            semester_values = ["1", "2"]
            self.units_filter_semester_options["1"] = ["1", "2", "3"]
            self.units_filter_semester_options["2"] = ["1", "2", "3"]

        self.units_semester_filter_menu.configure(values=semester_values)
        self.units_semester_filter_menu.set(semester_values[0])
        self.units_semester_filter_var.set(semester_values[0])
        self._update_units_period_filter_menu()

    def _update_units_period_filter_menu(self):
        semester_value = self.units_semester_filter_var.get()
        period_values = self.units_filter_semester_options.get(semester_value, [])
        if not period_values:
            period_values = ["1"]

        self.units_period_filter_menu.configure(values=period_values)
        if self.units_period_filter_var.get() not in period_values:
            self.units_period_filter_var.set(period_values[0])

    def _on_units_semester_changed(self, *args):
        self._update_units_period_filter_menu()
        self.refresh_units_list()

    def _on_units_period_changed(self, *args):
        self.refresh_units_list()

    def refresh_units_list(self):
        for widget in self.units_list_frame.winfo_children():
            widget.destroy()

        semester_label = self.units_semester_filter_var.get() if hasattr(self, 'units_semester_filter_var') else None
        period_label = self.units_period_filter_var.get() if hasattr(self, 'units_period_filter_var') else None
        semester_id = None
        if semester_label and period_label:
            semester_id = next(
                (row["id_SemestrePeriodo"] for row in select_semesters() if row["numero_semestre"] == semester_label and row["numero_periodo"] == period_label),
                None,
            )

        if not semester_id:
            self.create_label("Selecciona semestre y periodo válidos.", master=self.units_list_frame, font=("Arial", 12)).pack(padx=14, pady=14)
            return

        rows = select_units(semester_id)
        if not rows:
            self.create_label("No hay unidades para este semestre y periodo.", master=self.units_list_frame, font=("Arial", 12)).pack(padx=14, pady=14)
            return

        for unit in rows:
            unidad_completada = bool(unit["completada"]) if "completada" in unit.keys() else False
            frame_color = "#2f6d3a" if unidad_completada else "#303030"
            row_frame = ctk.CTkFrame(self.units_list_frame, fg_color=frame_color)
            row_frame.pack(fill="x", padx=8, pady=4)
            content_frame = ctk.CTkFrame(row_frame, fg_color=frame_color)
            content_frame.pack(fill="x", side="left", expand=True)

            # truncar nombre a 15 caracteres y añadir '...'
            nombre_completo = unit['nombre_unidad']
            display_name = nombre_completo if len(nombre_completo) <= 15 else (nombre_completo[:15] + "...")
            name_label = self.create_label(display_name, master=content_frame, anchor="w", font=("Arial", 12))
            name_label.pack(anchor="w", padx=10, pady=(10, 2), fill="x", expand=True)

            # El contexto no se muestra en el listado (se ve solo en el modal)

            # botón azul para ver detalles (nombre completo y contexto)
            self.create_button(
                "Ver",
                command=lambda u=unit: self.show_unit_modal(u),
                master=row_frame,
                width=64,
                fg_color="#3a77c9",
                hover_color="#2f61a8",
            ).pack(side="right", padx=(0, 6), pady=8)

            # botón rojo para borrar
            self.create_button(
                "X",
                command=lambda uid=unit["id_unidad"], uname=unit["nombre_unidad"]: self.confirm_delete_unit(uid, uname),
                master=row_frame,
                width=48,
                fg_color="#8a2424",
                hover_color="#a33030",
            ).pack(side="right", padx=(0, 10), pady=8)

    def save_unit(self):
        unit_name = self.entry_unit_name.get().strip()
        semester_label = self.units_semester_filter_var.get() if hasattr(self, 'units_semester_filter_var') else None
        period_label = self.units_period_filter_var.get() if hasattr(self, 'units_period_filter_var') else None

        if not unit_name:
            self.units_message_label.configure(text="El nombre de la unidad es obligatorio.", text_color="#f55a5a")
            return

        semester_id = next(
            (row["id_SemestrePeriodo"] for row in select_semesters() if row["numero_semestre"] == semester_label and row["numero_periodo"] == period_label),
            None,
        )
        if not semester_id:
            self.units_message_label.configure(text="Selecciona semestre y periodo válidos.", text_color="#f55a5a")
            return

        # obtener contexto desde el textbox
        contexto = self.entry_unit_context.get("1.0", "end").strip()
        insert_or_update_unit(unit_name, semester_id, contexto)
        self.entry_unit_name.delete(0, "end")
        try:
            self.entry_unit_context.delete("1.0", "end")
        except Exception:
            pass
        self.units_message_label.configure(text="Unidad guardada correctamente.", text_color="#8ee58e")
        self.refresh_units_list()
        self.refresh_note_units_menu()

    def confirm_delete_unit(self, unidad_id: int, unidad_nombre: str = None):
        if unidad_nombre:
            prompt = f"¿Eliminar la unidad '{unidad_nombre}'?"
        else:
            prompt = "¿Eliminar esta unidad?"

        if not messagebox.askyesno("Confirmar eliminación", prompt):
            return

        try:
            delete_unit(unidad_id)
            self.units_message_label.configure(text="Unidad eliminada correctamente.", text_color="#8ee58e")
        except Exception as e:
            self.units_message_label.configure(text=f"Error al eliminar unidad: {e}", text_color="#f55a5a")

        self.refresh_units_list()
        # Actualizar menú de unidades en Notas
        try:
            self.refresh_note_units_menu()
        except Exception:
            pass

    def show_unit_modal(self, unit_row):
        # Modal editable para ver/editar nombre y contexto
        modal = ctk.CTkToplevel(self)
        modal.title("Editar unidad")
        modal.geometry("700x520")
        modal.minsize(560, 420)
        modal.resizable(True, True)
        try:
            modal.grab_set()
        except Exception:
            pass
        try:
            modal.lift()
            modal.focus_force()
        except Exception:
            pass

        unidad_id = unit_row["id_unidad"] if "id_unidad" in unit_row.keys() else None
        nombre_inicial = unit_row["nombre_unidad"] if "nombre_unidad" in unit_row.keys() else ""
        contexto_inicial = unit_row["contexto"] if "contexto" in unit_row.keys() and unit_row["contexto"] else ""
        unidad_completada = bool(unit_row["completada"]) if "completada" in unit_row.keys() else False

        def refresh_completion_button(button):
            if unidad_completada:
                button.configure(text="Unidad completada", fg_color="#2d7a31", hover_color="#3ea64a")
            else:
                button.configure(text="Unidad no completada", fg_color="#8a2424", hover_color="#a33030")

        def toggle_completion(button):
            nonlocal unidad_completada
            unidad_completada = not unidad_completada
            try:
                update_unit(unidad_id, None, None, int(unidad_completada))
            except Exception:
                pass
            refresh_completion_button(button)

        modal.grid_columnconfigure(0, weight=1)
        modal.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(modal, fg_color="#1f1f1f", corner_radius=8)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)
        self.create_label("Editar Unidad", master=header, font=("Arial", 18, "bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=16, pady=14)
        self.create_label("Revisa o modifica el nombre y el contexto de la unidad.", master=header, font=("Arial", 11), anchor="w").grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))
        completion_button = self.create_button("", master=header, width=190, corner_radius=20, command=lambda: toggle_completion(completion_button))
        completion_button.grid(row=0, column=1, rowspan=2, sticky="e", padx=(0, 16), pady=14)
        refresh_completion_button(completion_button)

        body = ctk.CTkFrame(modal, fg_color="#242424", corner_radius=8)
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        body.grid_columnconfigure(0, weight=1)

        row = 0
        self.create_label("Nombre completo:", master=body, font=("Arial", 12, "bold"), anchor="w").grid(row=row, column=0, sticky="w", padx=16, pady=(16, 6))
        entry_name = ctk.CTkEntry(body)
        entry_name.grid(row=row + 1, column=0, sticky="ew", padx=16)
        entry_name.insert(0, nombre_inicial)

        self.create_label("Contexto:", master=body, font=("Arial", 12, "bold"), anchor="w").grid(row=row + 2, column=0, sticky="w", padx=16, pady=(16, 6))
        txt_context = ctk.CTkTextbox(body, wrap="word")
        txt_context.grid(row=row + 3, column=0, sticky="nsew", padx=16, pady=(0, 16))
        txt_context.insert("0.0", contexto_inicial)
        body.grid_rowconfigure(row + 3, weight=1)

        actions = ctk.CTkFrame(modal, fg_color="#1f1f1f", corner_radius=8)
        actions.grid(row=2, column=0, sticky="ew", padx=12, pady=(6, 12))
        actions.grid_columnconfigure(0, weight=1)

        def do_save_and_close():
            new_name = entry_name.get().strip()
            new_context = txt_context.get("1.0", "end").strip()
            if not new_name:
                messagebox.showwarning("Validación", "El nombre de la unidad no puede quedar vacío.")
                return
            try:
                update_unit(unidad_id, new_name, new_context, int(unidad_completada))
                self.units_message_label.configure(text="Unidad actualizada correctamente.", text_color="#8ee58e")
                self.refresh_units_list()
                try:
                    self.refresh_note_units_menu()
                except Exception:
                    pass
                modal.destroy()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Ya existe una unidad con ese nombre en el mismo semestre.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar la unidad: {e}")

        def on_close():
            current_name = entry_name.get().strip()
            current_context = txt_context.get("1.0", "end").strip()
            if current_name != nombre_inicial or current_context != contexto_inicial:
                if messagebox.askyesno("Guardar cambios?", "Se detectaron cambios. ¿Deseas guardar los cambios?"):
                    do_save_and_close()
                    return
            modal.destroy()

        buttons_frame = ctk.CTkFrame(actions, fg_color="transparent")
        buttons_frame.grid(row=0, column=0, sticky="e", padx=16, pady=12)
        self.create_button("Guardar", command=do_save_and_close, master=buttons_frame, width=120, fg_color="#3a77c9", hover_color="#2f61a8").grid(row=0, column=1, padx=(8, 0))
        self.create_button("Cerrar", command=on_close, master=buttons_frame, width=120).grid(row=0, column=0, padx=(0, 8))

        try:
            modal.protocol("WM_DELETE_WINDOW", on_close)
        except Exception:
            pass

        try:
            entry_name.focus_set()
        except Exception:
            pass

        # Enfocar el campo nombre
        try:
            entry_name.focus_set()
        except Exception:
            pass

    def refresh_notes_student_menu(self):
        students = select_students()
        semester_value = self.notes_semester_filter_var.get() if hasattr(self, 'notes_semester_filter_var') else None
        period_value = self.notes_period_filter_var.get() if hasattr(self, 'notes_period_filter_var') else None

        values = []
        self.notes_student_options = {}
        for student in students:
            if semester_value and period_value and semester_value != "No hay estudiantes" and period_value != "No hay estudiantes":
                if student["numero_semestre"] != semester_value or student["numero_periodo"] != period_value:
                    continue

            label = f"{student['ci']} · {student['nombres']} {student['apellidos']}"
            values.append(label)
            self.notes_student_options[label] = student["id_estudiantes"]

        if not values:
            values = ["No hay estudiantes"]
            self.notes_student_menu.configure(values=values)
            self.notes_student_menu.set(values[0])
            self.selected_note_student_id = None
            self.refresh_notes_list()
            return

        self.notes_student_menu.configure(values=values)
        if self.notes_student_menu.get() not in values:
            self.notes_student_menu.set(values[0])
        self.on_notes_student_selected(self.notes_student_menu.get())

    def on_notes_student_selected(self, value):
        if not value or value not in self.notes_student_options:
            self.selected_note_student_id = None
            self.refresh_notes_list()
            return

        self.selected_note_student_id = self.notes_student_options[value]
        self.refresh_notes_list()

    def refresh_notes_list(self):
        for widget in self.notes_list_frame.winfo_children():
            widget.destroy()

        # Actualizar encabezado del historial de notas
        if not hasattr(self, 'notes_history_student_label'):
            pass
        if not hasattr(self, 'selected_note_student_id') or self.selected_note_student_id is None:
            if hasattr(self, 'notes_history_student_label'):
                try:
                    self.notes_history_student_label.configure(text="")
                except Exception:
                    pass
            self.create_label("Selecciona un estudiante para ver sus notas.", master=self.notes_list_frame, font=("Arial", 12)).pack(padx=14, pady=14)
            return

        semester_label = self.notes_semester_filter_var.get() if hasattr(self, 'notes_semester_filter_var') else None
        period_label = self.notes_period_filter_var.get() if hasattr(self, 'notes_period_filter_var') else None
        semester_id = None
        if semester_label and period_label:
            semester_id = next(
                (row["id_SemestrePeriodo"] for row in select_semesters() if row["numero_semestre"] == semester_label and row["numero_periodo"] == period_label),
                None,
            )

        if not semester_id:
            if hasattr(self, 'notes_history_student_label'):
                try:
                    self.notes_history_student_label.configure(text="")
                except Exception:
                    pass
            self.create_label("Selecciona semestre y periodo válidos.", master=self.notes_list_frame, font=("Arial", 12)).pack(padx=14, pady=14)
            return

        rows = select_notes(self.selected_note_student_id, semester_id)
        # Mostrar nombre del estudiante en cabecera
        student = next((s for s in select_students() if s["id_estudiantes"] == self.selected_note_student_id), None)
        if student:
            nombre_full = f"{student['nombres']} {student['apellidos']}"
            try:
                self.notes_history_student_label.configure(text=f"Estudiante: {nombre_full}")
            except Exception:
                pass
        else:
            try:
                self.notes_history_student_label.configure(text="Estudiante: (desconocido)")
            except Exception:
                pass

        if not rows:
            self.create_label("No hay notas registradas para este estudiante en el semestre seleccionado.", master=self.notes_list_frame, font=("Arial", 12)).pack(padx=14, pady=14)
            return

        for note in rows:
            text = f"Unidad: {note['unidad']} - Nota: {note['nota']}"
            self.create_label(text, master=self.notes_list_frame, anchor="w", font=("Arial", 12, "bold")).pack(fill="x", padx=12, pady=(10, 2))
            if note['comentarios']:
                self.create_label(f"Comentarios: {note['comentarios']}", master=self.notes_list_frame, anchor="w", font=("Arial", 11)).pack(fill="x", padx=12, pady=(0, 8))

    def save_note(self):
        if not hasattr(self, 'selected_note_student_id') or self.selected_note_student_id is None:
            self.notes_message_label.configure(text="Selecciona primero un estudiante.", text_color="#f55a5a")
            return

        unidad_label = self.note_unit_var.get().strip()
        nota_text = self.entry_note_value.get().strip()
        comentarios = self.entry_note_comments.get().strip()
        semester_label = self.notes_semester_filter_var.get() if hasattr(self, 'notes_semester_filter_var') else None
        period_label = self.notes_period_filter_var.get() if hasattr(self, 'notes_period_filter_var') else None

        if not unidad_label or unidad_label == "No hay unidades" or unidad_label not in self.notes_unit_options:
            self.notes_message_label.configure(text="Selecciona primero una unidad válida.", text_color="#f55a5a")
            return

        if not nota_text:
            self.notes_message_label.configure(text="La nota es obligatoria.", text_color="#f55a5a")
            return

        semester_id = next(
            (row["id_SemestrePeriodo"] for row in select_semesters() if row["numero_semestre"] == semester_label and row["numero_periodo"] == period_label),
            None,
        )
        if not semester_id:
            self.notes_message_label.configure(text="Selecciona semestre y periodo válidos.", text_color="#f55a5a")
            return

        unidad_id = self.notes_unit_options.get(unidad_label)
        if unidad_id is None:
            self.notes_message_label.configure(text="No se encontró la unidad seleccionada.", text_color="#f55a5a")
            return

        insert_or_update_note(self.selected_note_student_id, semester_id, unidad_id, nota_text, comentarios)
        self.notes_message_label.configure(text="Nota guardada correctamente.", text_color="#8ee58e")
        self.note_unit_menu.set(unidad_label)
        self.entry_note_value.delete(0, "end")
        self.entry_note_comments.delete(0, "end")
        self.refresh_notes_list()

    def _update_admin_period_filter_menu(self):
        semester_value = self.admin_semester_filter_menu.get()
        period_values = self.admin_filter_semester_options.get(semester_value, [])
        if not period_values:
            period_values = ["1"]

        self.admin_period_filter_menu.configure(values=period_values)
        if self.admin_period_filter_menu.get() not in period_values:
            self.admin_period_filter_menu.set(period_values[0])

    def on_admin_filter_semester_selected(self, value):
        self._update_admin_period_filter_menu()
        self.refresh_delete_menu()
        self.refresh_admin_student_list()

    def on_admin_filter_period_selected(self, value):
        self.refresh_delete_menu()
        self.refresh_admin_student_list()

    def refresh_admin_student_list(self):
        for widget in self.admin_students_list_frame.winfo_children():
            widget.destroy()

        semester_value = self.admin_semester_filter_menu.get() if hasattr(self, 'admin_semester_filter_menu') else None
        period_value = self.admin_period_filter_menu.get() if hasattr(self, 'admin_period_filter_menu') else None

        if not semester_value or not period_value:
            self.create_label("Selecciona semestre y periodo.", master=self.admin_students_list_frame, font=("Arial", 12)).pack(padx=14, pady=14)
            return

        students = select_students()
        filtered = [s for s in students if s["numero_semestre"] == semester_value and s["numero_periodo"] == period_value]

        if not filtered:
            self.create_label("No hay estudiantes registrados en este semestre/período.", master=self.admin_students_list_frame, font=("Arial", 12)).pack(padx=14, pady=14)
            return

        header_frame = ctk.CTkFrame(self.admin_students_list_frame, fg_color="#3a3a3a")
        header_frame.pack(fill="x", padx=8, pady=(8, 4))
        self.create_label("Cédula", master=header_frame, font=("Arial", 12, "bold"), anchor="w").pack(side="left", padx=(10, 4), pady=8, fill="x", expand=True)
        self.create_label("Nombre", master=header_frame, font=("Arial", 12, "bold"), anchor="w").pack(side="left", padx=(10, 4), pady=8, fill="x", expand=True)
        self.create_label("Apellido", master=header_frame, font=("Arial", 12, "bold"), anchor="w").pack(side="left", padx=(10, 4), pady=8, fill="x", expand=True)
        self.create_label("Acciones", master=header_frame, font=("Arial", 12, "bold"), anchor="w").pack(side="right", padx=(10, 14), pady=8)

        for student in filtered:
            row_frame = ctk.CTkFrame(self.admin_students_list_frame, fg_color="#303030")
            row_frame.pack(fill="x", padx=8, pady=4)
            self.create_label(student['ci'], master=row_frame, anchor="w", font=("Arial", 12)).pack(side="left", padx=(10, 4), pady=10, fill="x", expand=True)
            self.create_label(student['nombres'], master=row_frame, anchor="w", font=("Arial", 12)).pack(side="left", padx=(10, 4), pady=10, fill="x", expand=True)
            self.create_label(student['apellidos'], master=row_frame, anchor="w", font=("Arial", 12)).pack(side="left", padx=(10, 4), pady=10, fill="x", expand=True)
            actions_frame = ctk.CTkFrame(row_frame, fg_color="#303030")
            actions_frame.pack(side="right", padx=(0, 10), pady=10)
            self.create_button(
                "Editar",
                command=lambda student_id=student['id_estudiantes']: self.edit_student(student_id),
                master=actions_frame,
                width=100,
                fg_color="#3d7a9f",
                hover_color="#5298bd",
            ).pack(side="left", padx=(0, 8))
            self.create_button(
                "Borrar",
                command=lambda student_id=student['id_estudiantes']: self.delete_single_student(student_id),
                master=actions_frame,
                width=100,
                fg_color="#8a2424",
                hover_color="#a33030",
            ).pack(side="left")

    def refresh_delete_menu(self):
        students = select_students()
        semester_value = self.admin_semester_filter_menu.get() if hasattr(self, 'admin_semester_filter_menu') else None
        period_value = self.admin_period_filter_menu.get() if hasattr(self, 'admin_period_filter_menu') else None

        values = []
        self.delete_student_options = {}
        for student in students:
            if semester_value and period_value and semester_value != "No hay estudiantes" and period_value != "No hay estudiantes":
                if student["numero_semestre"] != semester_value or student["numero_periodo"] != period_value:
                    continue

            label = f"{student['ci']} · {student['nombres']} {student['apellidos']}"
            values.append(label)
            self.delete_student_options[label] = student["id_estudiantes"]

        if not values:
            values = ["No hay estudiantes"]
            self.delete_student_menu.configure(values=values)
            self.delete_student_menu.set(values[0])
            self.refresh_admin_student_list()
            return

        self.delete_student_menu.configure(values=values)
        if self.delete_student_menu.get() not in values:
            self.delete_student_menu.set(values[0])
        self.refresh_admin_student_list()

    def add_student(self):
        nombres = self.entry_nombres.get().strip()
        apellidos = self.entry_apellidos.get().strip()
        ci = self.entry_ci.get().strip()
        semester_label = self.semester_menu.get()
        sem_id = self.semester_options.get(semester_label)

        if not nombres or not apellidos or not ci:
            self.add_message_label.configure(text="Todos los campos son obligatorios.", text_color="#f55a5a")
            return

        if not sem_id:
            self.add_message_label.configure(text="Selecciona un semestre válido.", text_color="#f55a5a")
            return

        try:
            insert_student(nombres, apellidos, ci, sem_id)
            self.entry_nombres.delete(0, "end")
            self.entry_apellidos.delete(0, "end")
            self.entry_ci.delete(0, "end")
            self.add_message_label.configure(text="Estudiante agregado con éxito.", text_color="#8ee58e")
            self.refresh_student_list()
            self.refresh_student_menu()
            self.refresh_delete_menu()
        except sqlite3.IntegrityError:
            self.add_message_label.configure(text="La cédula ya existe en la base de datos.", text_color="#f55a5a")

    def select_student_for_attendance(self, student):
        label = f"{student['ci']} · {student['nombres']} {student['apellidos']}"
        if label in self.student_options:
            self.attendance_student_menu.set(label)
            self.on_student_selected(label)

    def on_student_selected(self, value):
        if not value or value not in self.student_options:
            self.selected_student_id = None
            return

        self.selected_student_id = self.student_options[value]
        self.refresh_today_status()
        self.refresh_history()

    def mark_attendance(self, attendance_type):
        if self.selected_student_id is None:
            self.attendance_message_label.configure(text="Selecciona primero un estudiante.", text_color="#f55a5a")
            return

        type_id = select_attendance_types().get(attendance_type)
        if not type_id:
            self.attendance_message_label.configure(text="Tipo de asistencia no válido.", text_color="#f55a5a")
            return

        if self.date_mode_var.get() == "Establecer fecha":
            day = self.date_day_entry.get().strip()
            month = self.date_month_entry.get().strip()
            year = self.date_year_entry.get().strip()
            if not day or not month or not year:
                self.attendance_message_label.configure(text="Completa día, mes y año para la fecha.", text_color="#f55a5a")
                return
            try:
                selected_date = date(int(year), int(month), int(day)).isoformat()
            except ValueError:
                self.attendance_message_label.configure(text="Fecha inválida. Usa un formato correcto.", text_color="#f55a5a")
                return
        else:
            selected_date = date.today().isoformat()

        insert_or_update_attendance(self.selected_student_id, type_id, selected_date)

        self.attendance_message_label.configure(text=f"Asistencia registrada: {attendance_type} ({selected_date})", text_color="#8ee58e")
        self.refresh_today_status()
        self.refresh_history()

    def _on_date_mode_changed(self, *args):
        if self.date_mode_var.get() == "Establecer fecha":
            self.date_frame.grid()
        else:
            self.date_frame.grid_remove()

    def edit_student(self, student_id: int):
        student = next((s for s in select_students() if s["id_estudiantes"] == student_id), None)
        if not student:
            self.admin_message_label.configure(text="No se encontró el estudiante seleccionado.", text_color="#f55a5a")
            return

        ci = simpledialog.askstring("Editar estudiante", "Cédula:", initialvalue=student["ci"])
        if ci is None:
            return
        nombres = simpledialog.askstring("Editar estudiante", "Nombres:", initialvalue=student["nombres"])
        if nombres is None:
            return
        apellidos = simpledialog.askstring("Editar estudiante", "Apellidos:", initialvalue=student["apellidos"])
        if apellidos is None:
            return

        try:
            update_student(student_id, nombres.strip(), apellidos.strip(), ci.strip())
            self.admin_message_label.configure(text="Estudiante actualizado correctamente.", text_color="#8ee58e")
        except sqlite3.IntegrityError:
            self.admin_message_label.configure(text="La cédula ya existe en la base de datos.", text_color="#f55a5a")
            return
        except Exception as e:
            self.admin_message_label.configure(text=f"Error al actualizar estudiante: {e}", text_color="#f55a5a")
            return

        self.refresh_student_list()
        self.refresh_student_menu()
        self.refresh_delete_menu()
        self.refresh_admin_student_list()
        self.refresh_today_status()
        self.refresh_history()

    def delete_single_student(self, student_id: int):
        student = next((s for s in select_students() if s["id_estudiantes"] == student_id), None)
        if not student:
            self.admin_message_label.configure(text="No se encontró el estudiante seleccionado.", text_color="#f55a5a")
            return

        label = f"{student['ci']} · {student['nombres']} {student['apellidos']}"
        if not messagebox.askyesno("Confirmar eliminación", f"¿Eliminar al estudiante {label}?"):
            return

        delete_student(student_id)
        self.admin_message_label.configure(text="Estudiante eliminado correctamente.", text_color="#8ee58e")
        if self.selected_student_id == student_id:
            self.selected_student_id = None
        self.refresh_student_list()
        self.refresh_student_menu()
        self.refresh_delete_menu()
        self.refresh_admin_student_list()
        self.refresh_today_status()
        self.refresh_history()

    def confirm_delete_student(self):
        label = self.delete_student_menu.get()
        if not label or label == "No hay estudiantes":
            self.admin_message_label.configure(text="Selecciona primero un estudiante para eliminar.", text_color="#f55a5a")
            return

        student_id = self.delete_student_options.get(label)
        if student_id is None:
            self.admin_message_label.configure(text="No se encontró el estudiante seleccionado.", text_color="#f55a5a")
            return

        self.delete_single_student(student_id)

    def confirm_delete_all_students(self):
        if not messagebox.askyesno(
            "Eliminar todo", "¿Eliminar todos los estudiantes y sus registros de asistencia? Esta acción no se puede deshacer."
        ):
            return

        delete_all_students()
        self.admin_message_label.configure(text="Todos los estudiantes fueron eliminados.", text_color="#8ee58e")
        self.selected_student_id = None
        self.refresh_student_list()
        self.refresh_student_menu()
        self.refresh_delete_menu()
        self.refresh_today_status()
        self.refresh_history()

    def refresh_today_status(self):
        if self.selected_student_id is None:
            self.attendance_status_label.configure(text="Selecciona un estudiante para ver su asistencia de hoy.")
            return

        today = date.today().isoformat()
        status = select_today_attendance(self.selected_student_id, today)
        if status:
            self.attendance_status_label.configure(text=f"Asistencia de hoy: {status}")
        else:
            self.attendance_status_label.configure(text="Aún no se ha registrado asistencia para hoy.")

    def refresh_history(self):
        for widget in self.history_list_frame.winfo_children():
            widget.destroy()

        # Mostrar nombre del estudiante en la cabecera del historial
        if not hasattr(self, 'history_student_label'):
            pass
        if self.selected_student_id is None:
            if hasattr(self, 'history_student_label'):
                self.history_student_label.configure(text="")
            self.create_label("Selecciona un estudiante para ver su historial.", master=self.history_list_frame, font=("Arial", 12)).pack(padx=14, pady=14)
            return

        # Obtener datos del estudiante para el encabezado
        student = next((s for s in select_students() if s["id_estudiantes"] == self.selected_student_id), None)
        if student:
            nombre_full = f"{student['nombres']} {student['apellidos']}"
            try:
                self.history_student_label.configure(text=f"Estudiante: {nombre_full}")
            except Exception:
                pass
        else:
            try:
                self.history_student_label.configure(text="Estudiante: (desconocido)")
            except Exception:
                pass

        rows = select_history(self.selected_student_id)
        if not rows:
            self.create_label("No hay registros de asistencia para este estudiante.", master=self.history_list_frame, font=("Arial", 12)).pack(padx=14, pady=14)
            return

        for item in rows:
            text = f"{item['fecha']} · {item['nombre_asistencia']}"
            self.create_label(text, master=self.history_list_frame, anchor="w", font=("Arial", 12)).pack(fill="x", padx=12, pady=6)

    def open_user_settings(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Configuración de Usuario")
        modal.geometry("520x450")
        modal.resizable(False, False)
        try:
            modal.grab_set()
        except Exception:
            pass
        try:
            modal.lift()
            modal.focus_force()
        except Exception:
            pass

        current_username = self.username
        current_password = get_user_credentials(current_username)
        self._new_photo_bytes = get_user_profile_pic(current_username)

        modal.grid_columnconfigure(0, weight=1)
        
        title_frame = ctk.CTkFrame(modal, fg_color="#1f1f1f", corner_radius=8)
        title_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        self.create_label("Configuración de Usuario", master=title_frame, font=("Arial", 18, "bold")).pack(padx=15, pady=10)

        body = ctk.CTkFrame(modal, fg_color="#242424", corner_radius=10)
        body.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        body.grid_columnconfigure(0, weight=1)

        avatar_val_canvas = tk.Canvas(body, width=100, height=100, bg="#242424", highlightthickness=0, cursor="hand2")
        avatar_val_canvas.grid(row=0, column=0, pady=15)
        
        def render_modal_avatar():
            avatar_val_canvas.delete("all")
            if self._new_photo_bytes and Image is not None:
                try:
                    pil_img = Image.open(io.BytesIO(self._new_photo_bytes))
                    pil_img = pil_img.resize((80, 80), Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
                    mask = Image.new("L", (80, 80), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.ellipse((0, 0, 80, 80), fill=255)
                    
                    circular_img = Image.new("RGBA", (80, 80), (0,0,0,0))
                    circular_img.paste(pil_img, (0, 0), mask=mask)
                    
                    self._modal_photo_image = ImageTk.PhotoImage(circular_img)
                    avatar_val_canvas.create_image(50, 50, image=self._modal_photo_image)
                    avatar_val_canvas.create_oval(10, 10, 90, 90, outline="#ffffff", width=2)
                except Exception:
                    draw_default_modal_avatar()
            else:
                draw_default_modal_avatar()

        def draw_default_modal_avatar():
            avatar_val_canvas.create_oval(10, 10, 90, 90, outline="#ffffff", width=2)
            avatar_val_canvas.create_oval(35, 25, 65, 55, fill="#ffffff", outline="")
            avatar_val_canvas.create_arc(20, 60, 80, 120, start=0, extent=180, fill="#ffffff", outline="")

        def choose_photo(event=None):
            filepath = filedialog.askopenfilename(
                title="Seleccionar foto de perfil",
                filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp *.gif")]
            )
            if filepath:
                try:
                    with open(filepath, "rb") as f:
                        img = Image.open(f)
                        img.thumbnail((256, 256))
                        out_bytes = io.BytesIO()
                        img.save(out_bytes, format="PNG")
                        self._new_photo_bytes = out_bytes.getvalue()
                    render_modal_avatar()
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo cargar la imagen: {e}", parent=modal)

        avatar_val_canvas.bind("<Button-1>", choose_photo)
        render_modal_avatar()
        
        self.create_label("Haz clic en el círculo para cambiar la foto.", master=body, font=("Arial", 10), text_color="#8c8da5").grid(row=1, column=0, pady=(0, 15))

        fields_frame = ctk.CTkFrame(body, fg_color="transparent")
        fields_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=5)
        fields_frame.grid_columnconfigure(1, weight=1)

        self.create_label("Nombre de usuario:", master=fields_frame).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        username_entry = self.create_entry(placeholder_text="Nombre de usuario", master=fields_frame)
        username_entry.insert(0, current_username)
        username_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)

        self.create_label("Contraseña:", master=fields_frame).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        password_entry = self.create_entry(placeholder_text="Contraseña", master=fields_frame, show="*")
        password_entry.insert(0, current_password)
        password_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=5)

        actions = ctk.CTkFrame(modal, fg_color="#1f1f1f", corner_radius=8)
        actions.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 20))
        actions.grid_columnconfigure(0, weight=1)

        def save_settings():
            new_user = username_entry.get().strip()
            new_pass = password_entry.get().strip()

            if not new_user or not new_pass:
                messagebox.showwarning("Campos obligatorios", "El nombre de usuario y la contraseña no pueden estar vacíos.", parent=modal)
                return

            try:
                update_user_credentials(current_username, new_user, new_pass)
                
                if self._new_photo_bytes:
                    update_user_profile_pic(new_user, self._new_photo_bytes)
                
                self.username = new_user
                self.tabview.refresh_avatar()
                self._refresh_dashboard()

                messagebox.showinfo("Configuración", "Los cambios se guardaron correctamente.", parent=modal)
                modal.destroy()
            except ValueError as ve:
                messagebox.showerror("Error", str(ve), parent=modal)
            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un error al guardar: {e}", parent=modal)

        def cancel_settings():
            modal.destroy()

        btns = ctk.CTkFrame(actions, fg_color="transparent")
        btns.pack(side="right", padx=15, pady=10)
        self.create_button("Guardar", command=save_settings, master=btns, width=100, fg_color="#3a77c9", hover_color="#2f61a8").pack(side="right", padx=(5, 0))
        self.create_button("Cancelar", command=cancel_settings, master=btns, width=100).pack(side="right", padx=(0, 5))
