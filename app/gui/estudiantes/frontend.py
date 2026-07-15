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

class EstudiantesMixin:

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
            try:
                self.refresh_notes_student_menu()
            except Exception:
                pass
        except sqlite3.IntegrityError:
            self.add_message_label.configure(text="La cédula ya existe en la base de datos.", text_color="#f55a5a")


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
        try:
            self.refresh_notes_student_menu()
        except Exception:
            pass


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
        try:
            self.refresh_notes_student_menu()
        except Exception:
            pass


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
        try:
            self.refresh_notes_student_menu()
        except Exception:
            pass


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

