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

class AdminMixin:

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


    def check_report_button_state(self):
        semester_label = self.notes_semester_filter_var.get() if hasattr(self, 'notes_semester_filter_var') else None
        period_label = self.notes_period_filter_var.get() if hasattr(self, 'notes_period_filter_var') else None
        semester_id = None
        if semester_label and period_label:
            semester_id = next(
                (row["id_SemestrePeriodo"] for row in select_semesters() if row["numero_semestre"] == semester_label and row["numero_periodo"] == period_label),
                None,
            )

        students_count = 0
        if semester_id:
            students = select_students()
            filtered = [s for s in students if s["numero_semestre"] == semester_label and s["numero_periodo"] == period_label]
            students_count = len(filtered)

        if students_count > 0:
            self.btn_generate_report.configure(state="normal", fg_color="#00e676", text_color="#0d0e1a")
        else:
            self.btn_generate_report.configure(state="disabled", fg_color="#2c2e4a", text_color="#8c8da5")


    def generate_pdf_report(self):
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror(
                "Error de Dependencia",
                "La biblioteca 'reportlab' no está instalada.\n"
                "Para generar reportes PDF, por favor ejecute:\n"
                "  pip install reportlab\nen su terminal o consola."
            )
            return

        semester_label = self.notes_semester_filter_var.get()
        period_label = self.notes_period_filter_var.get()
        semester_id = None
        if semester_label and period_label:
            semester_id = next(
                (row["id_SemestrePeriodo"] for row in select_semesters() if row["numero_semestre"] == semester_label and row["numero_periodo"] == period_label),
                None,
            )

        if not semester_id:
            messagebox.showwarning("Reportes", "Selecciona un semestre y periodo válidos.")
            return

        students = select_students()
        filtered_students = [s for s in students if s["numero_semestre"] == semester_label and s["numero_periodo"] == period_label]

        if not filtered_students:
            messagebox.showwarning("Reportes", "No hay estudiantes registrados en este semestre y periodo.")
            return

        # Ordenar estudiantes numéricamente por su cédula
        def get_ci_num(st):
            digits = "".join(c for c in st["ci"] if c.isdigit())
            return int(digits) if digits else 0

        filtered_students.sort(key=get_ci_num)

        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Guardar Reporte de Calificaciones",
            initialfile=f"reporte_notas_sem_{semester_label}_per_{period_label}.pdf"
        )

        if not filename:
            return

        try:
            doc = SimpleDocTemplate(
                filename,
                pagesize=letter,
                rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
            )
            story = []

            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=18,
                textColor=colors.HexColor('#1b1c2b'),
                spaceAfter=6,
                alignment=1
            )
            
            subtitle_style = ParagraphStyle(
                'ReportSubtitle',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=11,
                textColor=colors.HexColor('#5a5c7a'),
                spaceAfter=20,
                alignment=1
            )
            
            meta_style = ParagraphStyle(
                'ReportMeta',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=10,
                textColor=colors.HexColor('#2c2e4a'),
                spaceAfter=15
            )
            
            th_style = ParagraphStyle(
                'TableHeader',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=10,
                textColor=colors.white,
                alignment=1
            )
            
            td_style = ParagraphStyle(
                'TableCell',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=9,
                textColor=colors.HexColor('#1c1e2f')
            )
            
            td_grade_style = ParagraphStyle(
                'TableCellGrade',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=10,
                textColor=colors.HexColor('#1b1c2b'),
                alignment=1
            )

            story.append(Paragraph("SISTEMA DE CONTROL DE ESTUDIANTES WOLFKIT", title_style))
            story.append(Paragraph("REPORTE CONSOLIDADO DE CALIFICACIONES", subtitle_style))
            story.append(Spacer(1, 10))

            from datetime import datetime
            current_date_str = datetime.now().strftime("%d/%m/%Y %I:%M %p")
            
            meta_text = (
                f"<b>Semestre:</b> {semester_label} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; "
                f"<b>Periodo:</b> {period_label} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; "
                f"<b>Total Estudiantes:</b> {len(filtered_students)}<br/>"
                f"<b>Fecha de Generación:</b> {current_date_str}"
            )
            story.append(Paragraph(meta_text, meta_style))
            story.append(Spacer(1, 10))

            table_data = [
                [
                    Paragraph("CÉDULA", th_style),
                    Paragraph("APELLIDO(S)", th_style),
                    Paragraph("NOMBRE(S)", th_style),
                    Paragraph("NOTA DEFINITIVA", th_style)
                ]
            ]

            for s in filtered_students:
                avg, _ = self.get_student_definitive_grade(s["id_estudiantes"], semester_id)
                avg_str = f"{avg:.2f}"
                
                table_data.append([
                    Paragraph(s["ci"], td_style),
                    Paragraph(s["apellidos"], td_style),
                    Paragraph(s["nombres"], td_style),
                    Paragraph(avg_str, td_grade_style)
                ])

            col_widths = [100, 160, 160, 84]
            t = Table(table_data, colWidths=col_widths)
            
            t_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#12132a')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ])
            
            for i in range(1, len(table_data)):
                if i % 2 == 0:
                    t_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f7fafc'))
                else:
                    t_style.add('BACKGROUND', (0, i), (-1, i), colors.white)
                    
            t.setStyle(t_style)
            story.append(t)
            
            def add_page_decorations(canvas, doc):
                canvas.saveState()
                canvas.setStrokeColor(colors.HexColor('#12132a'))
                canvas.setLineWidth(1)
                canvas.line(54, 738, 558, 738)
                canvas.line(54, 50, 558, 50)
                canvas.setFont('Helvetica', 8)
                canvas.setFillColor(colors.HexColor('#8c8da5'))
                canvas.drawString(54, 38, "Wolfkit Control de Estudiantes — Reporte de Calificaciones")
                canvas.drawRightString(558, 38, f"Página {doc.page}")
                canvas.restoreState()

            doc.build(story, onFirstPage=add_page_decorations, onLaterPages=add_page_decorations)
            messagebox.showinfo("Reportes", f"El reporte en PDF ha sido generado con éxito en:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el reporte en PDF: {e}")


            def add_page_decorations(canvas, doc):
                canvas.saveState()
                canvas.setStrokeColor(colors.HexColor('#12132a'))
                canvas.setLineWidth(1)
                canvas.line(54, 738, 558, 738)
                canvas.line(54, 50, 558, 50)
                canvas.setFont('Helvetica', 8)
                canvas.setFillColor(colors.HexColor('#8c8da5'))
                canvas.drawString(54, 38, "Wolfkit Control de Estudiantes — Reporte de Calificaciones")
                canvas.drawRightString(558, 38, f"Página {doc.page}")
                canvas.restoreState()

