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

class NotasMixin:

    def _build_notes_tab(self):
        tab = self.tabview.tab("Notas")
        tab.configure(fg_color="#0d0e1a")
        
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=0) # Header
        tab.grid_rowconfigure(1, weight=1) # Main content

        # ── HEADER ──────────────────────────────────────────────────────────
        header_frame = ctk.CTkFrame(tab, fg_color="#12132a", corner_radius=12, height=75)
        header_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header_frame.grid_propagate(False)
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=0)

        # Title
        title_f = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_f.grid(row=0, column=0, sticky="w", padx=16, pady=10)
        
        ctk.CTkLabel(
            title_f,
            text="✉ CONTROL DE CALIFICACIONES",
            font=("Arial", 16, "bold"),
            text_color="#0fbcf9",
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_f,
            text="Gestiona las notas y genera reportes consolidados",
            font=("Arial", 11),
            text_color="#5a5c7a",
        ).pack(anchor="w")

        # Controls & Report Button
        controls_f = ctk.CTkFrame(header_frame, fg_color="transparent")
        controls_f.grid(row=0, column=1, sticky="e", padx=16, pady=10)

        # Semester filter
        ctk.CTkLabel(controls_f, text="SEM:", font=("Arial", 10, "bold"), text_color="#8c8da5").pack(side="left", padx=(0, 4))
        self.notes_semester_filter_var = tk.StringVar(value="")
        self.notes_semester_filter_menu = ctk.CTkOptionMenu(
            controls_f,
            values=[],
            variable=self.notes_semester_filter_var,
            fg_color="#1a1b30",
            button_color="#2c2e4a",
            width=70,
            height=32,
            dynamic_resizing=False,
        )
        self.notes_semester_filter_menu.pack(side="left", padx=(0, 12))
        self.notes_semester_filter_var.trace_add("write", self._on_notes_semester_changed)

        # Period filter
        ctk.CTkLabel(controls_f, text="PER:", font=("Arial", 10, "bold"), text_color="#8c8da5").pack(side="left", padx=(0, 4))
        self.notes_period_filter_var = tk.StringVar(value="")
        self.notes_period_filter_menu = ctk.CTkOptionMenu(
            controls_f,
            values=[],
            variable=self.notes_period_filter_var,
            fg_color="#1a1b30",
            button_color="#2c2e4a",
            width=70,
            height=32,
            dynamic_resizing=False,
        )
        self.notes_period_filter_menu.pack(side="left", padx=(0, 16))
        self.notes_period_filter_var.trace_add("write", self._on_notes_period_changed)

        # Generate Report Button
        self.btn_generate_report = self.create_button(
            "📄  REPORTE PDF",
            command=self.generate_pdf_report,
            master=controls_f,
            font=("Arial", 11, "bold"),
            fg_color="#2c2e4a",
            hover_color="#212338",
            text_color="#8c8da5",
            width=130,
            height=34,
            corner_radius=10,
        )
        self.btn_generate_report.pack(side="left")

        # ── BODY PANEL ──────────────────────────────────────────────────────
        body_frame = ctk.CTkFrame(tab, fg_color="transparent")
        body_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        body_frame.grid_columnconfigure(0, weight=2) # Left list
        body_frame.grid_columnconfigure(1, weight=3) # Right details
        body_frame.grid_rowconfigure(0, weight=1)

        # ── Left Column: Student directory
        left_panel = ctk.CTkFrame(body_frame, fg_color="#12132a", corner_radius=12)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(
            left_panel,
            text="ESTUDIANTES EN EL PERIODO",
            font=("Arial", 12, "bold"),
            text_color="#ffffff",
            anchor="w"
        ).pack(fill="x", padx=16, pady=(16, 2))

        ctk.CTkLabel(
            left_panel,
            text="Selecciona un estudiante para ver detalles",
            font=("Arial", 10),
            text_color="#5a5c7a",
            anchor="w"
        ).pack(fill="x", padx=16, pady=(0, 12))

        self.notes_student_list_scroll = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        self.notes_student_list_scroll.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        # ── Right Column: Detail and grade editing
        self.notes_detail_container = ctk.CTkFrame(body_frame, fg_color="#12132a", corner_radius=12)
        self.notes_detail_container.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # Default state: empty message
        empty_lbl = ctk.CTkLabel(
            self.notes_detail_container,
            text="Selecciona un estudiante del listado\npara gestionar sus calificaciones.",
            font=("Arial", 13),
            text_color="#5a5c7a",
            justify="center"
        )
        empty_lbl.pack(expand=True, pady=100)



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
        try:
            self.check_report_button_state()
        except Exception:
            pass


    def _on_notes_period_changed(self, *args):
        self.refresh_notes_student_menu()
        self.refresh_note_units_menu()
        try:
            self.check_report_button_state()
        except Exception:
            pass


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

        if hasattr(self, 'note_unit_menu') and self.note_unit_menu and self.note_unit_menu.winfo_exists():
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


    def get_student_definitive_grade(self, student_id, semester_id):
        if not semester_id:
            return 0.0, 0
        units = select_units(semester_id)
        if not units:
            return 0.0, 0
        
        notes = select_notes(student_id, semester_id)
        sum_grades = 0.0
        graded_count = 0
        for u in units:
            note_row = next((n for n in notes if n["unidad"] == u["nombre_unidad"]), None)
            if note_row:
                try:
                    val = float(note_row["nota"].replace(",", "."))
                    sum_grades += val
                    graded_count += 1
                except (ValueError, TypeError):
                    pass
        # Promedio definitivo = suma de notas dividido entre el número total de unidades
        average = sum_grades / len(units) if len(units) > 0 else 0.0
        return average, len(units)


    def select_student_for_notes(self, student_id):
        self.selected_note_student_id = student_id
        self.refresh_notes_student_menu()


    def show_edit_note_modal(self, unit, note_row, semester_id):
        if not hasattr(self, 'selected_note_student_id') or self.selected_note_student_id is None:
            return

        modal = ctk.CTkToplevel(self)
        modal.title("Editar Calificación")
        modal.geometry("400x350")
        modal.resizable(False, False)
        modal.configure(fg_color="#0e0f1a")
        
        try:
            modal.grab_set()
        except Exception:
            pass
        try:
            modal.lift()
            modal.focus_force()
        except Exception:
            pass

        ctk.CTkLabel(
            modal,
            text=f"CALIFICACIÓN - {unit['nombre_unidad']}".upper(),
            font=("Arial", 14, "bold"),
            text_color="#0fbcf9"
        ).pack(pady=(20, 10))

        ctk.CTkLabel(modal, text="Nota:", font=("Arial", 11, "bold"), text_color="#8c8da5").pack(anchor="w", padx=30)
        
        nota_var = ctk.StringVar(value=str(note_row["nota"]) if note_row else "")
        nota_entry = ctk.CTkEntry(
            modal,
            textvariable=nota_var,
            font=("Arial", 13),
            fg_color="#141524",
            border_color="#2c2e4a",
            text_color="#ffffff",
            height=36
        )
        nota_entry.pack(fill="x", padx=30, pady=(0, 15))

        ctk.CTkLabel(modal, text="Comentarios:", font=("Arial", 11, "bold"), text_color="#8c8da5").pack(anchor="w", padx=30)
        
        comentarios_var = ctk.StringVar(value=note_row["comentarios"] if note_row and note_row["comentarios"] else "")
        comentarios_entry = ctk.CTkEntry(
            modal,
            textvariable=comentarios_var,
            font=("Arial", 13),
            fg_color="#141524",
            border_color="#2c2e4a",
            text_color="#ffffff",
            height=36
        )
        comentarios_entry.pack(fill="x", padx=30, pady=(0, 20))

        def save():
            nota = nota_var.get().strip()
            comentarios = comentarios_var.get().strip()
            if not nota:
                messagebox.showerror("Error", "La nota es obligatoria.", parent=modal)
                return
            
            insert_or_update_note(self.selected_note_student_id, semester_id, unit["id_unidad"], nota, comentarios)
            modal.destroy()
            self.refresh_notes_student_menu()
            if hasattr(self, 'notes_message_label') and self.notes_message_label.winfo_exists():
                self.notes_message_label.configure(text="Nota actualizada correctamente.", text_color="#8ee58e")

        btn_frame = ctk.CTkFrame(modal, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=(10, 0))
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.create_button("Cancelar", command=modal.destroy, master=btn_frame, fg_color="#3d1e1e", hover_color="#5a2c2c", text_color="#ff4757").grid(row=0, column=0, padx=(0, 5), sticky="ew")
        self.create_button("Guardar", command=save, master=btn_frame, fg_color="#0fbcf9", hover_color="#34e7e4", text_color="#0e0f1a").grid(row=0, column=1, padx=(5, 0), sticky="ew")



    def delete_student_grade(self, unit_id):
        if not hasattr(self, 'selected_note_student_id') or self.selected_note_student_id is None:
            return

        semester_label = self.notes_semester_filter_var.get()
        period_label = self.notes_period_filter_var.get()
        semester_id = next(
            (row["id_SemestrePeriodo"] for row in select_semesters() if row["numero_semestre"] == semester_label and row["numero_periodo"] == period_label),
            None,
        )

        if not semester_id:
            return

        if not messagebox.askyesno("Confirmar eliminación", "¿Deseas eliminar esta calificación?"):
            return

        try:
            delete_note(self.selected_note_student_id, semester_id, unit_id)
            self.refresh_notes_student_menu()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar la nota: {e}")


    def refresh_notes_student_menu(self):
        students = select_students()
        semester_value = self.notes_semester_filter_var.get() if hasattr(self, 'notes_semester_filter_var') else None
        period_value = self.notes_period_filter_var.get() if hasattr(self, 'notes_period_filter_var') else None

        filtered_students = []
        self.notes_student_options = {}
        for student in students:
            if semester_value and period_value and semester_value != "No hay estudiantes" and period_value != "No hay estudiantes":
                if student["numero_semestre"] != semester_value or student["numero_periodo"] != period_value:
                    continue
            filtered_students.append(student)
            label = f"{student['ci']} · {student['nombres']} {student['apellidos']}"
            self.notes_student_options[label] = student["id_estudiantes"]

        # Limpiar listado de la izquierda
        for w in self.notes_student_list_scroll.winfo_children():
            w.destroy()

        if not filtered_students:
            self.create_label(
                "No hay estudiantes registrados",
                master=self.notes_student_list_scroll,
                font=("Arial", 11)
            ).pack(pady=20)
            self.selected_note_student_id = None
            self.refresh_notes_list()
            self.check_report_button_state()
            return

        semester_id = None
        if semester_value and period_value:
            semester_id = next(
                (row["id_SemestrePeriodo"] for row in select_semesters() if row["numero_semestre"] == semester_value and row["numero_periodo"] == period_value),
                None,
            )

        for student in filtered_students:
            student_id = student["id_estudiantes"]
            avg, _ = self.get_student_definitive_grade(student_id, semester_id)
            
            # Colores del badge según promedio
            if avg >= 9.5: # Nota aprobatoria estándar
                badge_bg = "#0f3a20"
                badge_fg = "#00e676"
            elif avg > 0:
                badge_bg = "#3d1e1e"
                badge_fg = "#ff4757"
            else:
                badge_bg = "#1c1e2f"
                badge_fg = "#8c8da5"

            is_selected = (self.selected_note_student_id == student_id)
            card_bg = "#212338" if is_selected else "#141524"
            border_color = "#0fbcf9" if is_selected else "#141524"
            border_w = 1 if is_selected else 0

            # Crear tarjeta de estudiante
            card = ctk.CTkFrame(
                self.notes_student_list_scroll,
                fg_color=card_bg,
                corner_radius=10,
                border_width=border_w,
                border_color=border_color
            )
            card.pack(fill="x", padx=6, pady=4)
            card.configure(cursor="hand2")

            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=12, pady=10)

            name_lbl = ctk.CTkLabel(
                info_frame,
                text=f"{student['nombres']} {student['apellidos']}".upper(),
                font=("Arial", 11, "bold"),
                text_color="#ffffff",
                anchor="w"
            )
            name_lbl.pack(anchor="w")

            ci_lbl = ctk.CTkLabel(
                info_frame,
                text=f"CI: {student['ci']}",
                font=("Arial", 9),
                text_color="#8c8da5",
                anchor="w"
            )
            ci_lbl.pack(anchor="w")

            # Badge del promedio definitivo
            badge = ctk.CTkFrame(card, fg_color=badge_bg, corner_radius=6, height=26, width=50)
            badge.pack(side="right", padx=12, pady=10)
            badge.pack_propagate(False)

            badge_lbl = ctk.CTkLabel(
                badge,
                text=f"{avg:.1f}" if avg > 0 else "0.0",
                font=("Arial", 10, "bold"),
                text_color=badge_fg
            )
            badge_lbl.pack(fill="both", expand=True)

            # Enlazar clics recursivamente para seleccionar estudiante
            def make_select_callback(sid=student_id):
                return lambda e: self.select_student_for_notes(sid)

            card.bind("<Button-1>", make_select_callback())
            info_frame.bind("<Button-1>", make_select_callback())
            name_lbl.bind("<Button-1>", make_select_callback())
            ci_lbl.bind("<Button-1>", make_select_callback())
            badge.bind("<Button-1>", make_select_callback())
            badge_lbl.bind("<Button-1>", make_select_callback())

        # Si el seleccionado ya no es válido, por defecto seleccionar el primero
        student_ids = [s["id_estudiantes"] for s in filtered_students]
        if self.selected_note_student_id not in student_ids:
            self.selected_note_student_id = student_ids[0]
            self.after(50, self.refresh_notes_student_menu)
            return

        self.refresh_notes_list()
        self.check_report_button_state()


    def refresh_notes_list(self):
        for widget in self.notes_detail_container.winfo_children():
            widget.destroy()

        if not hasattr(self, 'selected_note_student_id') or self.selected_note_student_id is None:
            empty_frame = ctk.CTkFrame(self.notes_detail_container, fg_color="transparent")
            empty_frame.pack(fill="both", expand=True)
            ctk.CTkLabel(
                empty_frame,
                text="Selecciona un estudiante del listado\npara gestionar sus calificaciones.",
                font=("Arial", 13),
                text_color="#5a5c7a",
                justify="center"
            ).pack(expand=True, pady=100)
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
            ctk.CTkLabel(
                self.notes_detail_container,
                text="Seleccione un semestre y periodo válidos.",
                font=("Arial", 12),
                text_color="#f55a5a"
            ).pack(pady=40)
            return

        student = next((s for s in select_students() if s["id_estudiantes"] == self.selected_note_student_id), None)
        if not student:
            ctk.CTkLabel(
                self.notes_detail_container,
                text="No se encontró la información del estudiante.",
                font=("Arial", 12),
                text_color="#f55a5a"
            ).pack(pady=40)
            return

        # ── CABECERA DEL ESTUDIANTE ──────────────────────────────────────
        header_card = ctk.CTkFrame(self.notes_detail_container, fg_color="#141524", corner_radius=10, border_width=1, border_color="#2c2e4a")
        header_card.pack(fill="x", padx=16, pady=(16, 8))
        
        info_sub = ctk.CTkFrame(header_card, fg_color="transparent")
        info_sub.pack(side="left", padx=16, pady=12)
        
        ctk.CTkLabel(
            info_sub,
            text=f"{student['nombres']} {student['apellidos']}".upper(),
            font=("Arial", 14, "bold"),
            text_color="#ffffff",
            anchor="w"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            info_sub,
            text=f"CI: {student['ci']}  •  Semestre {student['numero_semestre']} - Periodo {student['numero_periodo']}",
            font=("Arial", 10),
            text_color="#8c8da5",
            anchor="w"
        ).pack(anchor="w")

        # Nota definitiva en cabecera
        avg, _ = self.get_student_definitive_grade(self.selected_note_student_id, semester_id)
        avg_badge_bg = "#0f3a20" if avg >= 9.5 else ("#3d1e1e" if avg > 0 else "#1c1e2f")
        avg_badge_fg = "#00e676" if avg >= 9.5 else ("#ff4757" if avg > 0 else "#8c8da5")
        
        badge_header = ctk.CTkFrame(header_card, fg_color=avg_badge_bg, corner_radius=8, height=36, width=70)
        badge_header.pack(side="right", padx=16, pady=12)
        badge_header.pack_propagate(False)
        
        ctk.CTkLabel(
            badge_header,
            text=f"{avg:.2f}",
            font=("Arial", 12, "bold"),
            text_color=avg_badge_fg
        ).pack(fill="both", expand=True)

        # ── LISTA DE CALIFICACIONES POR UNIDAD ─────────────────────────────────
        grades_scroll = ctk.CTkScrollableFrame(self.notes_detail_container, fg_color="transparent", height=190)
        grades_scroll.pack(fill="both", expand=True, padx=16, pady=4)

        units = select_units(semester_id)
        notes = select_notes(self.selected_note_student_id, semester_id)

        if not units:
            ctk.CTkLabel(
                grades_scroll,
                text="No hay unidades creadas para este semestre.\nUse la pestaña 'Unidades' para agregar una.",
                font=("Arial", 11),
                text_color="#8c8da5",
                justify="center"
            ).pack(pady=30)
        else:
            for u in units:
                note_row = next((n for n in notes if n["unidad"] == u["nombre_unidad"]), None)
                unit_card = ctk.CTkFrame(grades_scroll, fg_color="#181928", corner_radius=8)
                unit_card.pack(fill="x", padx=2, pady=3)

                info_f = ctk.CTkFrame(unit_card, fg_color="transparent")
                info_f.pack(side="left", fill="both", expand=True, padx=12, pady=8)

                ctk.CTkLabel(
                    info_f,
                    text=u["nombre_unidad"].upper(),
                    font=("Arial", 11, "bold"),
                    text_color="#ffffff",
                    anchor="w"
                ).pack(anchor="w")

                comment_str = f"Comentarios: {note_row['comentarios']}" if (note_row and note_row['comentarios']) else "Sin comentarios"
                ctk.CTkLabel(
                    info_f,
                    text=comment_str,
                    font=("Arial", 9),
                    text_color="#5a5c7a",
                    anchor="w"
                ).pack(anchor="w")

                actions_f = ctk.CTkFrame(unit_card, fg_color="transparent")
                actions_f.pack(side="right", padx=12, pady=8)

                if note_row:
                    val = note_row["nota"]
                    try:
                        f_val = float(val.replace(",", "."))
                        val_color = "#00e676" if f_val >= 9.5 else "#ff4757"
                    except ValueError:
                        val_color = "#ffffff"

                    ctk.CTkLabel(
                        actions_f,
                        text=f"Nota: {val}",
                        font=("Arial", 11, "bold"),
                        text_color=val_color
                    ).pack(side="left", padx=(0, 12))

                    self.create_button(
                        "✏️",
                        command=lambda u_obj=u, n_obj=note_row, sid=semester_id: self.show_edit_note_modal(u_obj, n_obj, sid),
                        master=actions_f,
                        width=28,
                        height=24,
                        fg_color="#1a1b30",
                        hover_color="#2c2e4a",
                        text_color="#0fbcf9"
                    ).pack(side="left", padx=(0, 4))

                    self.create_button(
                        "🗑",
                        command=lambda uid=u["id_unidad"]: self.delete_student_grade(uid),
                        master=actions_f,
                        width=28,
                        height=24,
                        fg_color="#3d1e1e",
                        hover_color="#5a2c2c",
                        text_color="#ff4757"
                    ).pack(side="left")
                else:
                    ctk.CTkLabel(
                        actions_f,
                        text="Sin Nota",
                        font=("Arial", 10, "italic"),
                        text_color="#5a5c7a"
                    ).pack(side="left", padx=(0, 12))

                    self.create_button(
                        "✏️",
                        command=lambda u_obj=u, sid=semester_id: self.show_edit_note_modal(u_obj, None, sid),
                        master=actions_f,
                        width=28,
                        height=24,
                        fg_color="#1a1b30",
                        hover_color="#2c2e4a",
                        text_color="#0fbcf9"
                    ).pack(side="left")

        # ── FORMULARIO DE REGISTRO RÁPIDO ─────────────────────────────────────
        form_card = ctk.CTkFrame(self.notes_detail_container, fg_color="#141524", corner_radius=10, border_width=1, border_color="#2c2e4a")
        form_card.pack(fill="x", padx=16, pady=(8, 16))

        ctk.CTkLabel(
            form_card,
            text="REGISTRAR / ACTUALIZAR CALIFICACIÓN",
            font=("Arial", 11, "bold"),
            text_color="#0fbcf9",
            anchor="w"
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(12, 8))

        ctk.CTkLabel(form_card, text="UNIDAD", font=("Arial", 10, "bold"), text_color="#8c8da5").grid(row=1, column=0, sticky="w", padx=14, pady=(4, 2))
        
        unit_menu_f = ctk.CTkFrame(form_card, fg_color="transparent")
        unit_menu_f.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
        unit_menu_f.grid_columnconfigure(0, weight=1)

        self.note_unit_menu = ctk.CTkOptionMenu(
            unit_menu_f,
            values=[],
            variable=self.note_unit_var,
            fg_color="#1a1b30",
            button_color="#2c2e4a",
            height=32,
            dynamic_resizing=False
        )
        self.note_unit_menu.grid(row=0, column=0, sticky="ew")
        
        self.create_button(
            "+", 
            command=self.add_unit_from_notes, 
            master=unit_menu_f, 
            width=32, 
            height=32,
            fg_color="#1a1b30",
            hover_color="#2c2e4a",
            text_color="#0fbcf9"
        ).grid(row=0, column=1, padx=(6, 0))

        ctk.CTkLabel(form_card, text="CALIFICACIÓN", font=("Arial", 10, "bold"), text_color="#8c8da5").grid(row=1, column=1, sticky="w", padx=14, pady=(4, 2))
        self.entry_note_value = self.create_entry("Nota", master=form_card, fg_color="#1a1b30", border_color="#2c2e4a", height=32)
        self.entry_note_value.grid(row=2, column=1, sticky="ew", padx=14, pady=(0, 10))

        save_btn = self.create_button(
            "GUARDAR NOTA",
            command=self.save_note,
            master=form_card,
            font=("Arial", 10, "bold"),
            fg_color="#0fbcf9",
            hover_color="#0da0d4",
            text_color="#0d0e1a",
            height=32
        )
        save_btn.grid(row=2, column=2, sticky="ew", padx=14, pady=(0, 10))

        ctk.CTkLabel(form_card, text="COMENTARIOS", font=("Arial", 10, "bold"), text_color="#8c8da5").grid(row=3, column=0, columnspan=3, sticky="w", padx=14, pady=(4, 2))
        self.entry_note_comments = self.create_entry("Comentarios (opcional)", master=form_card, fg_color="#1a1b30", border_color="#2c2e4a", height=32)
        self.entry_note_comments.grid(row=4, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 10))

        self.notes_message_label = ctk.CTkLabel(form_card, text="", font=("Arial", 10))
        self.notes_message_label.grid(row=5, column=0, columnspan=3, sticky="w", padx=14, pady=(0, 8))

        form_card.grid_columnconfigure((0, 1, 2), weight=1)
        self.refresh_note_units_menu()


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
        self.refresh_notes_student_menu()


