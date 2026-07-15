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

class UnidadesMixin:

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

