import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from PIL import ImageDraw
try:
    from PIL import Image, ImageTk
except ImportError:
    pass
import sqlite3
from datetime import date
from app.utils.db import *
import io
import threading
from pathlib import Path

class DashboardMixin:

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


