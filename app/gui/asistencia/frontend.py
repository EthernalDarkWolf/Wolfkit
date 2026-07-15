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

class AsistenciaMixin:

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

