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

class ServidorMixin:

    def _build_server_tab(self):
        """Build the futuristic server management panel inside the 'Servidor' tab."""
        from app.utils.server_manager import ServerManager

        mgr = ServerManager()
        sys_info = mgr.get_system_info()
        self.resource_labels = {}

        tab = self.tabview.tab("Servidor")
        tab.configure(fg_color="#0d0e1a")

        # ── HEADER ──────────────────────────────────────────────────────
        header = ctk.CTkFrame(tab, fg_color="#12132a", corner_radius=12, height=70)
        header.pack(fill="x", padx=16, pady=(16, 8))
        header.pack_propagate(False)

        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left", fill="y", padx=16)

        ctk.CTkLabel(
            header_left,
            text="⚡ SERVER MANAGER",
            font=("Arial", 20, "bold"),
            text_color="#0fbcf9",
        ).pack(side="left", pady=14)

        ctk.CTkLabel(
            header_left,
            text="  —  Panel de Control de Servidores",
            font=("Arial", 12),
            text_color="#5a5c7a",
        ).pack(side="left", pady=14)

        header_right = ctk.CTkFrame(header, fg_color="transparent")
        header_right.pack(side="right", fill="y", padx=16)

        active_count_label = ctk.CTkLabel(
            header_right,
            text="● 0 activos",
            font=("Arial", 12, "bold"),
            text_color="#00e676",
        )
        active_count_label.pack(side="right", pady=14, padx=(10, 0))

        total_count_label = ctk.CTkLabel(
            header_right,
            text="0 servidores",
            font=("Arial", 12),
            text_color="#8c8da5",
        )
        total_count_label.pack(side="right", pady=14)

        # ── BODY (Left panel + Right panel) ─────────────────────────────
        body = ctk.CTkFrame(tab, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        # ── LEFT PANEL: Create Server ──────────────────────────────────
        left_panel = ctk.CTkFrame(body, fg_color="#12132a", corner_radius=12)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        left_scroll = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        left_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        # Title
        ctk.CTkLabel(
            left_scroll,
            text="CREAR SERVIDOR",
            font=("Arial", 14, "bold"),
            text_color="#ffffff",
        ).pack(anchor="w", padx=16, pady=(16, 4))

        ctk.CTkLabel(
            left_scroll,
            text="Configura los recursos del servidor",
            font=("Arial", 10),
            text_color="#5a5c7a",
        ).pack(anchor="w", padx=16, pady=(0, 12))

        # Server name
        ctk.CTkLabel(left_scroll, text="NOMBRE", font=("Arial", 10, "bold"), text_color="#8c8da5").pack(anchor="w", padx=16, pady=(8, 2))
        server_name_entry = ctk.CTkEntry(
            left_scroll,
            placeholder_text="Mi Servidor",
            fg_color="#1a1b30",
            border_color="#2c2e4a",
            text_color="#ffffff",
            corner_radius=8,
            height=36,
        )
        server_name_entry.pack(fill="x", padx=16, pady=(0, 10))

        # Port
        ctk.CTkLabel(left_scroll, text="PUERTO", font=("Arial", 10, "bold"), text_color="#8c8da5").pack(anchor="w", padx=16, pady=(4, 2))
        port_entry = ctk.CTkEntry(
            left_scroll,
            placeholder_text="8080",
            fg_color="#1a1b30",
            border_color="#2c2e4a",
            text_color="#ffffff",
            corner_radius=8,
            height=36,
        )
        port_entry.insert(0, "8080")
        port_entry.pack(fill="x", padx=16, pady=(0, 10))

        # Version
        ctk.CTkLabel(left_scroll, text="VERSIÓN DE TERRARIA (Opcional, ej: 1.4.5.6)", font=("Arial", 10, "bold"), text_color="#8c8da5").pack(anchor="w", padx=16, pady=(4, 2))
        version_entry = ctk.CTkEntry(
            left_scroll,
            placeholder_text="1.4.4.9",
            fg_color="#1a1b30",
            border_color="#2c2e4a",
            text_color="#ffffff",
            corner_radius=8,
            height=36,
        )
        version_entry.insert(0, "1.4.4.9")
        version_entry.pack(fill="x", padx=16, pady=(0, 10))

        # ── Slider helper ──
        def make_resource_slider(parent, label_text, unit, min_val, max_val, default_val, step, color):
            """Create a labeled slider with live value display."""
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(fill="x", padx=16, pady=(4, 8))

            top_row = ctk.CTkFrame(frame, fg_color="transparent")
            top_row.pack(fill="x")

            ctk.CTkLabel(
                top_row,
                text=label_text,
                font=("Arial", 10, "bold"),
                text_color="#8c8da5",
            ).pack(side="left")

            val_label = ctk.CTkLabel(
                top_row,
                text=f"{default_val} {unit}",
                font=("Arial", 10, "bold"),
                text_color=color,
            )
            val_label.pack(side="right")

            slider = ctk.CTkSlider(
                frame,
                from_=min_val,
                to=max_val,
                number_of_steps=max(1, int((max_val - min_val) / step)),
                fg_color="#1a1b30",
                progress_color=color,
                button_color=color,
                button_hover_color=color,
                height=16,
            )
            slider.set(default_val)
            slider.pack(fill="x", pady=(4, 0))

            def on_change(value):
                rounded = int(round(value / step) * step)
                val_label.configure(text=f"{rounded} {unit}")

            slider.configure(command=on_change)
            return slider, val_label

        # RAM slider
        ram_max = min(sys_info["ram_total_mb"], 32768)
        ram_default = min(512, ram_max)
        ram_slider, ram_label = make_resource_slider(
            left_scroll, "RAM", "MB", 128, ram_max, ram_default, 128, "#0fbcf9"
        )

        # CPU slider
        cpu_max = sys_info["cpu_cores"]
        cpu_slider, cpu_label = make_resource_slider(
            left_scroll, "CPU CORES", "cores", 1, cpu_max, 1, 1, "#a55eea"
        )

        # Disk slider
        disk_max = min(sys_info["disk_free_mb"], 102400)
        disk_default = min(1024, disk_max)
        disk_slider, disk_label = make_resource_slider(
            left_scroll, "ALMACENAMIENTO", "MB", 256, disk_max, disk_default, 256, "#ff6b8b"
        )

        # Directory selector
        ctk.CTkLabel(left_scroll, text="DIRECTORIO RAÍZ", font=("Arial", 10, "bold"), text_color="#8c8da5").pack(anchor="w", padx=16, pady=(8, 2))

        dir_frame = ctk.CTkFrame(left_scroll, fg_color="transparent")
        dir_frame.pack(fill="x", padx=16, pady=(0, 10))

        dir_var = tk.StringVar(value="(automático)")
        dir_display = ctk.CTkLabel(
            dir_frame,
            textvariable=dir_var,
            font=("Arial", 9),
            text_color="#5a5c7a",
            anchor="w",
        )
        dir_display.pack(side="left", fill="x", expand=True)

        def choose_dir():
            path = filedialog.askdirectory(title="Seleccionar directorio raíz", parent=self)
            if path:
                dir_var.set(path)

        ctk.CTkButton(
            dir_frame,
            text="📂",
            width=36,
            height=28,
            fg_color="#1a1b30",
            hover_color="#2c2e4a",
            corner_radius=6,
            command=choose_dir,
        ).pack(side="right", padx=(6, 0))

        # System info display
        sys_frame = ctk.CTkFrame(left_scroll, fg_color="#0a0b18", corner_radius=8)
        sys_frame.pack(fill="x", padx=16, pady=(8, 10))

        ctk.CTkLabel(
            sys_frame,
            text="RECURSOS DEL SISTEMA",
            font=("Arial", 9, "bold"),
            text_color="#5a5c7a",
        ).pack(anchor="w", padx=12, pady=(8, 4))

        sys_items = [
            ("RAM Total", f"{sys_info['ram_total_mb']:,} MB", "#0fbcf9"),
            ("CPU Cores", f"{sys_info['cpu_cores']}", "#a55eea"),
            ("Disco Libre", f"{sys_info['disk_free_mb']:,} MB", "#ff6b8b"),
        ]
        for label_t, val_t, col in sys_items:
            row = ctk.CTkFrame(sys_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=1)
            ctk.CTkLabel(row, text=label_t, font=("Arial", 9), text_color="#5a5c7a").pack(side="left")
            ctk.CTkLabel(row, text=val_t, font=("Arial", 9, "bold"), text_color=col).pack(side="right")

        # Add bottom padding to sys_frame
        ctk.CTkLabel(sys_frame, text="", height=4).pack()

        # Error / status message
        create_msg_label = ctk.CTkLabel(
            left_scroll,
            text="",
            font=("Arial", 10),
            text_color="#ff4757",
            wraplength=280,
        )
        create_msg_label.pack(anchor="w", padx=16, pady=(0, 4))

        # CREATE button
        def do_create_server():
            name = server_name_entry.get().strip()
            port_str = port_entry.get().strip()

            if not name:
                create_msg_label.configure(text="⚠ Ingresa un nombre para el servidor.", text_color="#ff4757")
                return
            if not port_str.isdigit() or not (1024 <= int(port_str) <= 65535):
                create_msg_label.configure(text="⚠ Puerto inválido (1024–65535).", text_color="#ff4757")
                return

            port = int(port_str)
            ram = int(round(ram_slider.get() / 128) * 128)
            cpu = int(round(cpu_slider.get()))
            disk = int(round(disk_slider.get() / 256) * 256)
            root_dir = dir_var.get() if dir_var.get() != "(automático)" else ""
            version_str = version_entry.get().strip() or "1.4.4.9"

            try:
                mgr.create_server(
                    name=name,
                    port=port,
                    ram_mb=ram,
                    cpu_cores=cpu,
                    disk_mb=disk,
                    root_dir=root_dir,
                    version=version_str,
                )
                create_msg_label.configure(text=f"✓ Servidor '{name}' creado.", text_color="#00e676")
                server_name_entry.delete(0, "end")
                # Reset version entry to default
                version_entry.delete(0, "end")
                version_entry.insert(0, "1.4.4.9")
                # Auto-increment port
                port_entry.delete(0, "end")
                port_entry.insert(0, str(port + 1))
                refresh_server_list()
            except Exception as e:
                err_msg = str(e)
                if "UNIQUE" in err_msg.upper():
                    create_msg_label.configure(text="⚠ Nombre o puerto ya en uso.", text_color="#ff4757")
                else:
                    create_msg_label.configure(text=f"⚠ Error: {err_msg}", text_color="#ff4757")

        create_btn = ctk.CTkButton(
            left_scroll,
            text="⚡  CREAR SERVIDOR",
            font=("Arial", 13, "bold"),
            fg_color="#0fbcf9",
            hover_color="#0da0d4",
            text_color="#0d0e1a",
            corner_radius=10,
            height=44,
            command=do_create_server,
        )
        create_btn.pack(fill="x", padx=16, pady=(4, 16))

        bind_mouse_wheel_recursive(left_scroll, left_scroll)

        # ── RIGHT PANEL: Server List ───────────────────────────────────
        right_panel = ctk.CTkFrame(body, fg_color="#12132a", corner_radius=12)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # Right panel header
        right_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        right_header.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            right_header,
            text="SERVIDORES",
            font=("Arial", 14, "bold"),
            text_color="#ffffff",
        ).pack(side="left")

        refresh_btn = ctk.CTkButton(
            right_header,
            text="⟳",
            width=32,
            height=28,
            fg_color="#1a1b30",
            hover_color="#2c2e4a",
            corner_radius=6,
            font=("Arial", 14),
            command=lambda: refresh_server_list(),
        )
        refresh_btn.pack(side="right")

        # Scrollable server list
        server_list_frame = ctk.CTkScrollableFrame(
            right_panel,
            fg_color="transparent",
        )
        server_list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # ── Server card builder ──
        def refresh_server_list():
            self.resource_labels.clear()
            for w in server_list_frame.winfo_children():
                w.destroy()

            servers = mgr.get_all_servers()
            active = sum(1 for s in servers if s["estado"] == "encendido")
            total_count_label.configure(text=f"{len(servers)} servidores")
            active_count_label.configure(text=f"● {active} activos")

            if not servers:
                empty_frame = ctk.CTkFrame(server_list_frame, fg_color="#0a0b18", corner_radius=10)
                empty_frame.pack(fill="x", padx=8, pady=40)
                ctk.CTkLabel(
                    empty_frame,
                    text="No hay servidores creados",
                    font=("Arial", 13),
                    text_color="#5a5c7a",
                ).pack(pady=30)
                ctk.CTkLabel(
                    empty_frame,
                    text="Usa el panel izquierdo para crear uno",
                    font=("Arial", 10),
                    text_color="#3d3f5a",
                ).pack(pady=(0, 30))
                return

            for srv in servers:
                card = build_server_card(srv)
                bind_mouse_wheel_recursive(card, server_list_frame)

        def build_server_card(srv):
            is_on = srv["estado"] == "encendido"

            # Card
            border_color = "#00e676" if is_on else "#2c2e4a"
            card_bg = "#141530" if not is_on else "#0f1f15"
            card = ctk.CTkFrame(
                server_list_frame,
                fg_color=card_bg,
                corner_radius=10,
                border_width=1,
                border_color=border_color,
            )
            card.pack(fill="x", padx=8, pady=5)

            # Top row: Name + Status indicator
            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=14, pady=(12, 4))

            # Status dot (canvas for pulsing effect)
            dot_canvas = tk.Canvas(top_row, width=14, height=14, bg=card_bg, highlightthickness=0)
            dot_canvas.pack(side="left", padx=(0, 8))
            dot_color = "#00e676" if is_on else "#ff4757"
            dot_canvas.create_oval(2, 2, 12, 12, fill=dot_color, outline="")

            # Glow for active servers
            if is_on:
                dot_canvas.create_oval(0, 0, 14, 14, outline="#00e676", width=1)

            ctk.CTkLabel(
                top_row,
                text=srv["nombre"].upper(),
                font=("Arial", 13, "bold"),
                text_color="#ffffff",
            ).pack(side="left")

            status_text = "ENCENDIDO" if is_on else "APAGADO"
            status_color = "#00e676" if is_on else "#ff4757"
            ctk.CTkLabel(
                top_row,
                text=status_text,
                font=("Arial", 10, "bold"),
                text_color=status_color,
            ).pack(side="right")

            # Info row: Port + IP
            info_row = ctk.CTkFrame(card, fg_color="transparent")
            info_row.pack(fill="x", padx=14, pady=(0, 4))

            ctk.CTkLabel(
                info_row,
                text=f":{srv['puerto']}",
                font=("Arial", 10),
                text_color="#0fbcf9",
            ).pack(side="left")

            ctk.CTkLabel(
                info_row,
                text=f"  •  {srv['ip_bind']}",
                font=("Arial", 10),
                text_color="#5a5c7a",
            ).pack(side="left")

            if is_on and srv.get("pid"):
                ctk.CTkLabel(
                    info_row,
                    text=f"  •  PID: {srv['pid']}",
                    font=("Arial", 9),
                    text_color="#3d3f5a",
                ).pack(side="left")

            is_terraria = "terraria" in srv["nombre"].lower()
            if is_terraria:
                version_val = "1.4.4.9"
                try:
                    version_val = srv["version"] or "1.4.4.9"
                except Exception:
                    pass
                ctk.CTkLabel(
                    info_row,
                    text=f"  •  v{version_val}",
                    font=("Arial", 10, "bold"),
                    text_color="#00e676",
                ).pack(side="left")

            # Resource bars
            res_frame = ctk.CTkFrame(card, fg_color="#0a0b18", corner_radius=6)
            res_frame.pack(fill="x", padx=14, pady=(4, 6))

            def mini_bar(parent, label, value, color):
                r = ctk.CTkFrame(parent, fg_color="transparent")
                r.pack(fill="x", padx=10, pady=2)
                ctk.CTkLabel(r, text=label, font=("Arial", 9), text_color="#5a5c7a", width=90, anchor="w").pack(side="left")
                ctk.CTkLabel(r, text=value, font=("Arial", 9, "bold"), text_color=color).pack(side="right")

            mini_bar(res_frame, "RAM", f"{srv['ram_mb']} MB", "#0fbcf9")
            mini_bar(res_frame, "CPU", f"{srv['cpu_cores']} cores", "#a55eea")
            mini_bar(res_frame, "DISCO", f"{srv['disco_mb']} MB", "#ff6b8b")

            # Add padding at bottom of resource frame
            ctk.CTkLabel(res_frame, text="", height=2).pack()

            # Real-time usage (only when running)
            if is_on:
                usage = mgr.get_server_resources(srv["id_servidor"])
                if usage:
                    usage_frame = ctk.CTkFrame(card, fg_color="transparent")
                    usage_frame.pack(fill="x", padx=14, pady=(0, 4))

                    ram_pct = min(100, int((usage["ram_used_mb"] / max(1, srv["ram_mb"])) * 100))
                    ram_bar_color = "#00e676" if ram_pct < 70 else ("#ffab00" if ram_pct < 90 else "#ff4757")

                    usage_lbl = ctk.CTkLabel(
                        usage_frame,
                        text=f"USO: RAM {usage['ram_used_mb']}MB/{srv['ram_mb']}MB ({ram_pct}%)  •  CPU {usage['cpu_percent']}%",
                        font=("Arial", 9),
                        text_color=ram_bar_color,
                    )
                    usage_lbl.pack(side="left")
                    self.resource_labels[srv["id_servidor"]] = usage_lbl

            # Action buttons
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(fill="x", padx=14, pady=(4, 12))

            if is_on:
                ctk.CTkButton(
                    btn_frame,
                    text="⏹  APAGAR",
                    font=("Arial", 10, "bold"),
                    fg_color="#ff4757",
                    hover_color="#cc3847",
                    text_color="#ffffff",
                    corner_radius=8,
                    height=32,
                    command=lambda sid=srv["id_servidor"]: _stop_server(sid),
                ).pack(side="left", padx=(0, 6))

                ctk.CTkButton(
                    btn_frame,
                    text="⚡ PROBAR",
                    font=("Arial", 10, "bold"),
                    fg_color="#0fbcf9",
                    hover_color="#0da0d4",
                    text_color="#0d0e1a",
                    corner_radius=8,
                    height=32,
                    command=lambda sid=srv["id_servidor"], sname=srv["nombre"], sip=srv["ip_bind"], sport=srv["puerto"]: _test_server(sid, sname, sip, sport),
                ).pack(side="left", padx=(0, 6))
            else:
                ctk.CTkButton(
                    btn_frame,
                    text="▶  ENCENDER",
                    font=("Arial", 10, "bold"),
                    fg_color="#00e676",
                    hover_color="#00c864",
                    text_color="#0d0e1a",
                    corner_radius=8,
                    height=32,
                    command=lambda sid=srv["id_servidor"]: _start_server(sid),
                ).pack(side="left", padx=(0, 6))

            ctk.CTkButton(
                btn_frame,
                text="🗑",
                font=("Arial", 12),
                fg_color="#1a1b30",
                hover_color="#8a2424",
                text_color="#ff4757",
                corner_radius=8,
                width=36,
                height=32,
                command=lambda sid=srv["id_servidor"], sname=srv["nombre"]: _delete_server(sid, sname),
            ).pack(side="right")

            return card

        # ── Server actions ──
        def _test_server(server_id, server_name, server_ip, server_port):
            modal = ctk.CTkToplevel(self)
            modal.title(f"Prueba de Servidor - {server_name}")
            modal.geometry("600x400")
            modal.configure(fg_color="#0a0a1a")
            modal.transient(self)
            modal.grab_set()

            title_lbl = ctk.CTkLabel(modal, text="TERMINAL DE DIAGNÓSTICO", font=("Courier New", 14, "bold"), text_color="#0fbcf9")
            title_lbl.pack(pady=(20, 10))

            console_frame = ctk.CTkFrame(modal, fg_color="#05050f", border_width=1, border_color="#1a1b30", corner_radius=5)
            console_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

            console_text = tk.Text(console_frame, bg="#05050f", fg="#00e676", font=("Courier New", 12), bd=0, highlightthickness=0)
            console_text.pack(fill="both", expand=True, padx=10, pady=10)
            console_text.tag_config("error", foreground="#ff4757")
            console_text.tag_config("highlight", foreground="#0fbcf9")
            console_text.tag_config("cursor", foreground="#00e676")
            console_text.configure(state="disabled")

            cursor_state = [True]

            def blink_cursor():
                if not modal.winfo_exists():
                    return
                console_text.configure(state="normal")
                pos = console_text.search("█", "1.0", "end")
                if pos:
                    console_text.delete(pos)
                
                if cursor_state[0]:
                    console_text.insert("end", "█", "cursor")
                
                cursor_state[0] = not cursor_state[0]
                console_text.configure(state="disabled")
                modal.after(500, blink_cursor)

            def append_text(text, tag=None):
                if not modal.winfo_exists():
                    return
                console_text.configure(state="normal")
                pos = console_text.search("█", "1.0", "end")
                if pos:
                    console_text.delete(pos)
                
                if tag:
                    console_text.insert("end", text, tag)
                else:
                    console_text.insert("end", text)
                
                if cursor_state[0]:
                    console_text.insert("end", "█", "cursor")
                    
                console_text.see("end")
                console_text.configure(state="disabled")

            blink_cursor()

            import threading
            import time

            def type_effect(text, tag=None, delay=0.02):
                for char in text:
                    modal.after(0, append_text, char, tag)
                    time.sleep(delay)
                modal.after(0, append_text, "\n")

            def perform_test():
                time.sleep(0.5)
                type_effect("> Inicializando protocolo de prueba...")
                time.sleep(0.2)
                type_effect(f"> Objetivo: {server_ip}:{server_port}")
                time.sleep(0.2)
                
                type_string = "> probando la respuesta del servidor"
                for char in type_string:
                    modal.after(0, append_text, char)
                    time.sleep(0.02)
                
                for _ in range(4):
                    modal.after(0, append_text, ".")
                    time.sleep(0.4)
                modal.after(0, append_text, "\n\n")

                import socket
                host = "127.0.0.1" if server_ip in ["0.0.0.0", ""] else server_ip
                
                success = False
                try:
                    with socket.create_connection((host, server_port), timeout=3):
                        success = True
                except Exception:
                    success = False

                if success:
                    type_effect("> El servidor esta en optimas condiciones:", "highlight")
                    time.sleep(0.2)
                    type_effect(f"> {server_name}: Hola mundo!")
                else:
                    type_effect("> el servidor no a respondido", "error")

            threading.Thread(target=perform_test, daemon=True).start()

        def _start_server(server_id):
            success = mgr.start_server(server_id)
            if success:
                refresh_server_list()
            else:
                messagebox.showerror("Error", "No se pudo iniciar el servidor.", parent=self)

        def _stop_server(server_id):
            mgr.stop_server(server_id)
            refresh_server_list()

        def _delete_server(server_id, server_name):
            if not messagebox.askyesno(
                "Eliminar servidor",
                f"¿Eliminar el servidor '{server_name}'?\nEsto lo detendrá si está encendido.",
                parent=self,
            ):
                return
            mgr.delete_server(server_id)
            refresh_server_list()

        # ── Auto-refresh loop ──
        def auto_refresh():
            if self.tabview.active_tab != "Servidor":
                try:
                    if self.winfo_exists():
                        self.after(5000, auto_refresh)
                except Exception:
                    pass
                return
            try:
                if self.winfo_exists():
                    servers = mgr.get_all_servers()
                    current_snapshot = [(s["id_servidor"], s["estado"], s["pid"]) for s in servers]
                    
                    if not hasattr(self, "_last_servers_snapshot") or self._last_servers_snapshot != current_snapshot:
                        self._last_servers_snapshot = current_snapshot
                        refresh_server_list()
                    else:
                        for srv in servers:
                            if srv["estado"] == "encendido":
                                sid = srv["id_servidor"]
                                usage = mgr.get_server_resources(sid)
                                if usage and sid in self.resource_labels and self.resource_labels[sid].winfo_exists():
                                    ram_pct = min(100, int((usage["ram_used_mb"] / max(1, srv["ram_mb"])) * 100))
                                    ram_bar_color = "#00e676" if ram_pct < 70 else ("#ffab00" if ram_pct < 90 else "#ff4757")
                                    self.resource_labels[sid].configure(
                                        text=f"USO: RAM {usage['ram_used_mb']}MB/{srv['ram_mb']}MB ({ram_pct}%)  •  CPU {usage['cpu_percent']}%",
                                        text_color=ram_bar_color
                                    )
                    self.after(5000, auto_refresh)
            except Exception:
                pass

        # Initial load
        refresh_server_list()

        # Start auto-refresh (every 5 seconds)
        self.after(5000, auto_refresh)



        def make_resource_slider(parent, label_text, unit, min_val, max_val, default_val, step, color):
            """Create a labeled slider with live value display."""
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(fill="x", padx=16, pady=(4, 8))

            top_row = ctk.CTkFrame(frame, fg_color="transparent")
            top_row.pack(fill="x")

            ctk.CTkLabel(
                top_row,
                text=label_text,
                font=("Arial", 10, "bold"),
                text_color="#8c8da5",
            ).pack(side="left")

            val_label = ctk.CTkLabel(
                top_row,
                text=f"{default_val} {unit}",
                font=("Arial", 10, "bold"),
                text_color=color,
            )
            val_label.pack(side="right")

            slider = ctk.CTkSlider(
                frame,
                from_=min_val,
                to=max_val,
                number_of_steps=max(1, int((max_val - min_val) / step)),
                fg_color="#1a1b30",
                progress_color=color,
                button_color=color,
                button_hover_color=color,
                height=16,
            )
            slider.set(default_val)
            slider.pack(fill="x", pady=(4, 0))

            def on_change(value):
                rounded = int(round(value / step) * step)
                val_label.configure(text=f"{rounded} {unit}")

            slider.configure(command=on_change)
            return slider, val_label


        def choose_dir():
            path = filedialog.askdirectory(title="Seleccionar directorio raíz", parent=self)
            if path:
                dir_var.set(path)


        def do_create_server():
            name = server_name_entry.get().strip()
            port_str = port_entry.get().strip()

            if not name:
                create_msg_label.configure(text="⚠ Ingresa un nombre para el servidor.", text_color="#ff4757")
                return
            if not port_str.isdigit() or not (1024 <= int(port_str) <= 65535):
                create_msg_label.configure(text="⚠ Puerto inválido (1024–65535).", text_color="#ff4757")
                return

            port = int(port_str)
            ram = int(round(ram_slider.get() / 128) * 128)
            cpu = int(round(cpu_slider.get()))
            disk = int(round(disk_slider.get() / 256) * 256)
            root_dir = dir_var.get() if dir_var.get() != "(automático)" else ""
            version_str = version_entry.get().strip() or "1.4.4.9"

            try:
                mgr.create_server(
                    name=name,
                    port=port,
                    ram_mb=ram,
                    cpu_cores=cpu,
                    disk_mb=disk,
                    root_dir=root_dir,
                    version=version_str,
                )
                create_msg_label.configure(text=f"✓ Servidor '{name}' creado.", text_color="#00e676")
                server_name_entry.delete(0, "end")
                # Reset version entry to default
                version_entry.delete(0, "end")
                version_entry.insert(0, "1.4.4.9")
                # Auto-increment port
                port_entry.delete(0, "end")
                port_entry.insert(0, str(port + 1))
                refresh_server_list()
            except Exception as e:
                err_msg = str(e)
                if "UNIQUE" in err_msg.upper():
                    create_msg_label.configure(text="⚠ Nombre o puerto ya en uso.", text_color="#ff4757")
                else:
                    create_msg_label.configure(text=f"⚠ Error: {err_msg}", text_color="#ff4757")


        def refresh_server_list():
            self.resource_labels.clear()
            for w in server_list_frame.winfo_children():
                w.destroy()

            servers = mgr.get_all_servers()
            active = sum(1 for s in servers if s["estado"] == "encendido")
            total_count_label.configure(text=f"{len(servers)} servidores")
            active_count_label.configure(text=f"● {active} activos")

            if not servers:
                empty_frame = ctk.CTkFrame(server_list_frame, fg_color="#0a0b18", corner_radius=10)
                empty_frame.pack(fill="x", padx=8, pady=40)
                ctk.CTkLabel(
                    empty_frame,
                    text="No hay servidores creados",
                    font=("Arial", 13),
                    text_color="#5a5c7a",
                ).pack(pady=30)
                ctk.CTkLabel(
                    empty_frame,
                    text="Usa el panel izquierdo para crear uno",
                    font=("Arial", 10),
                    text_color="#3d3f5a",
                ).pack(pady=(0, 30))
                return

            for srv in servers:
                card = build_server_card(srv)
                bind_mouse_wheel_recursive(card, server_list_frame)


        def build_server_card(srv):
            is_on = srv["estado"] == "encendido"

            # Card
            border_color = "#00e676" if is_on else "#2c2e4a"
            card_bg = "#141530" if not is_on else "#0f1f15"
            card = ctk.CTkFrame(
                server_list_frame,
                fg_color=card_bg,
                corner_radius=10,
                border_width=1,
                border_color=border_color,
            )
            card.pack(fill="x", padx=8, pady=5)

            # Top row: Name + Status indicator
            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=14, pady=(12, 4))

            # Status dot (canvas for pulsing effect)
            dot_canvas = tk.Canvas(top_row, width=14, height=14, bg=card_bg, highlightthickness=0)
            dot_canvas.pack(side="left", padx=(0, 8))
            dot_color = "#00e676" if is_on else "#ff4757"
            dot_canvas.create_oval(2, 2, 12, 12, fill=dot_color, outline="")

            # Glow for active servers
            if is_on:
                dot_canvas.create_oval(0, 0, 14, 14, outline="#00e676", width=1)

            ctk.CTkLabel(
                top_row,
                text=srv["nombre"].upper(),
                font=("Arial", 13, "bold"),
                text_color="#ffffff",
            ).pack(side="left")

            status_text = "ENCENDIDO" if is_on else "APAGADO"
            status_color = "#00e676" if is_on else "#ff4757"
            ctk.CTkLabel(
                top_row,
                text=status_text,
                font=("Arial", 10, "bold"),
                text_color=status_color,
            ).pack(side="right")

            # Info row: Port + IP
            info_row = ctk.CTkFrame(card, fg_color="transparent")
            info_row.pack(fill="x", padx=14, pady=(0, 4))

            ctk.CTkLabel(
                info_row,
                text=f":{srv['puerto']}",
                font=("Arial", 10),
                text_color="#0fbcf9",
            ).pack(side="left")

            ctk.CTkLabel(
                info_row,
                text=f"  •  {srv['ip_bind']}",
                font=("Arial", 10),
                text_color="#5a5c7a",
            ).pack(side="left")

            if is_on and srv.get("pid"):
                ctk.CTkLabel(
                    info_row,
                    text=f"  •  PID: {srv['pid']}",
                    font=("Arial", 9),
                    text_color="#3d3f5a",
                ).pack(side="left")

            is_terraria = "terraria" in srv["nombre"].lower()
            if is_terraria:
                version_val = "1.4.4.9"
                try:
                    version_val = srv["version"] or "1.4.4.9"
                except Exception:
                    pass
                ctk.CTkLabel(
                    info_row,
                    text=f"  •  v{version_val}",
                    font=("Arial", 10, "bold"),
                    text_color="#00e676",
                ).pack(side="left")

            # Resource bars
            res_frame = ctk.CTkFrame(card, fg_color="#0a0b18", corner_radius=6)
            res_frame.pack(fill="x", padx=14, pady=(4, 6))

            def mini_bar(parent, label, value, color):
                r = ctk.CTkFrame(parent, fg_color="transparent")
                r.pack(fill="x", padx=10, pady=2)
                ctk.CTkLabel(r, text=label, font=("Arial", 9), text_color="#5a5c7a", width=90, anchor="w").pack(side="left")
                ctk.CTkLabel(r, text=value, font=("Arial", 9, "bold"), text_color=color).pack(side="right")

            mini_bar(res_frame, "RAM", f"{srv['ram_mb']} MB", "#0fbcf9")
            mini_bar(res_frame, "CPU", f"{srv['cpu_cores']} cores", "#a55eea")
            mini_bar(res_frame, "DISCO", f"{srv['disco_mb']} MB", "#ff6b8b")

            # Add padding at bottom of resource frame
            ctk.CTkLabel(res_frame, text="", height=2).pack()

            # Real-time usage (only when running)
            if is_on:
                usage = mgr.get_server_resources(srv["id_servidor"])
                if usage:
                    usage_frame = ctk.CTkFrame(card, fg_color="transparent")
                    usage_frame.pack(fill="x", padx=14, pady=(0, 4))

                    ram_pct = min(100, int((usage["ram_used_mb"] / max(1, srv["ram_mb"])) * 100))
                    ram_bar_color = "#00e676" if ram_pct < 70 else ("#ffab00" if ram_pct < 90 else "#ff4757")

                    usage_lbl = ctk.CTkLabel(
                        usage_frame,
                        text=f"USO: RAM {usage['ram_used_mb']}MB/{srv['ram_mb']}MB ({ram_pct}%)  •  CPU {usage['cpu_percent']}%",
                        font=("Arial", 9),
                        text_color=ram_bar_color,
                    )
                    usage_lbl.pack(side="left")
                    self.resource_labels[srv["id_servidor"]] = usage_lbl

            # Action buttons
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(fill="x", padx=14, pady=(4, 12))

            if is_on:
                ctk.CTkButton(
                    btn_frame,
                    text="⏹  APAGAR",
                    font=("Arial", 10, "bold"),
                    fg_color="#ff4757",
                    hover_color="#cc3847",
                    text_color="#ffffff",
                    corner_radius=8,
                    height=32,
                    command=lambda sid=srv["id_servidor"]: _stop_server(sid),
                ).pack(side="left", padx=(0, 6))

                ctk.CTkButton(
                    btn_frame,
                    text="⚡ PROBAR",
                    font=("Arial", 10, "bold"),
                    fg_color="#0fbcf9",
                    hover_color="#0da0d4",
                    text_color="#0d0e1a",
                    corner_radius=8,
                    height=32,
                    command=lambda sid=srv["id_servidor"], sname=srv["nombre"], sip=srv["ip_bind"], sport=srv["puerto"]: _test_server(sid, sname, sip, sport),
                ).pack(side="left", padx=(0, 6))
            else:
                ctk.CTkButton(
                    btn_frame,
                    text="▶  ENCENDER",
                    font=("Arial", 10, "bold"),
                    fg_color="#00e676",
                    hover_color="#00c864",
                    text_color="#0d0e1a",
                    corner_radius=8,
                    height=32,
                    command=lambda sid=srv["id_servidor"]: _start_server(sid),
                ).pack(side="left", padx=(0, 6))

            ctk.CTkButton(
                btn_frame,
                text="🗑",
                font=("Arial", 12),
                fg_color="#1a1b30",
                hover_color="#8a2424",
                text_color="#ff4757",
                corner_radius=8,
                width=36,
                height=32,
                command=lambda sid=srv["id_servidor"], sname=srv["nombre"]: _delete_server(sid, sname),
            ).pack(side="right")

            return card


            def mini_bar(parent, label, value, color):
                r = ctk.CTkFrame(parent, fg_color="transparent")
                r.pack(fill="x", padx=10, pady=2)
                ctk.CTkLabel(r, text=label, font=("Arial", 9), text_color="#5a5c7a", width=90, anchor="w").pack(side="left")
                ctk.CTkLabel(r, text=value, font=("Arial", 9, "bold"), text_color=color).pack(side="right")


        def _test_server(server_id, server_name, server_ip, server_port):
            modal = ctk.CTkToplevel(self)
            modal.title(f"Prueba de Servidor - {server_name}")
            modal.geometry("600x400")
            modal.configure(fg_color="#0a0a1a")
            modal.transient(self)
            modal.grab_set()

            title_lbl = ctk.CTkLabel(modal, text="TERMINAL DE DIAGNÓSTICO", font=("Courier New", 14, "bold"), text_color="#0fbcf9")
            title_lbl.pack(pady=(20, 10))

            console_frame = ctk.CTkFrame(modal, fg_color="#05050f", border_width=1, border_color="#1a1b30", corner_radius=5)
            console_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

            console_text = tk.Text(console_frame, bg="#05050f", fg="#00e676", font=("Courier New", 12), bd=0, highlightthickness=0)
            console_text.pack(fill="both", expand=True, padx=10, pady=10)
            console_text.tag_config("error", foreground="#ff4757")
            console_text.tag_config("highlight", foreground="#0fbcf9")
            console_text.tag_config("cursor", foreground="#00e676")
            console_text.configure(state="disabled")

            cursor_state = [True]

            def blink_cursor():
                if not modal.winfo_exists():
                    return
                console_text.configure(state="normal")
                pos = console_text.search("█", "1.0", "end")
                if pos:
                    console_text.delete(pos)
                
                if cursor_state[0]:
                    console_text.insert("end", "█", "cursor")
                
                cursor_state[0] = not cursor_state[0]
                console_text.configure(state="disabled")
                modal.after(500, blink_cursor)

            def append_text(text, tag=None):
                if not modal.winfo_exists():
                    return
                console_text.configure(state="normal")
                pos = console_text.search("█", "1.0", "end")
                if pos:
                    console_text.delete(pos)
                
                if tag:
                    console_text.insert("end", text, tag)
                else:
                    console_text.insert("end", text)
                
                if cursor_state[0]:
                    console_text.insert("end", "█", "cursor")
                    
                console_text.see("end")
                console_text.configure(state="disabled")

            blink_cursor()

            import threading
            import time

            def type_effect(text, tag=None, delay=0.02):
                for char in text:
                    modal.after(0, append_text, char, tag)
                    time.sleep(delay)
                modal.after(0, append_text, "\n")

            def perform_test():
                time.sleep(0.5)
                type_effect("> Inicializando protocolo de prueba...")
                time.sleep(0.2)
                type_effect(f"> Objetivo: {server_ip}:{server_port}")
                time.sleep(0.2)
                
                type_string = "> probando la respuesta del servidor"
                for char in type_string:
                    modal.after(0, append_text, char)
                    time.sleep(0.02)
                
                for _ in range(4):
                    modal.after(0, append_text, ".")
                    time.sleep(0.4)
                modal.after(0, append_text, "\n\n")

                import socket
                host = "127.0.0.1" if server_ip in ["0.0.0.0", ""] else server_ip
                
                success = False
                try:
                    with socket.create_connection((host, server_port), timeout=3):
                        success = True
                except Exception:
                    success = False

                if success:
                    type_effect("> El servidor esta en optimas condiciones:", "highlight")
                    time.sleep(0.2)
                    type_effect(f"> {server_name}: Hola mundo!")
                else:
                    type_effect("> el servidor no a respondido", "error")

            threading.Thread(target=perform_test, daemon=True).start()


            def perform_test():
                time.sleep(0.5)
                type_effect("> Inicializando protocolo de prueba...")
                time.sleep(0.2)
                type_effect(f"> Objetivo: {server_ip}:{server_port}")
                time.sleep(0.2)
                
                type_string = "> probando la respuesta del servidor"
                for char in type_string:
                    modal.after(0, append_text, char)
                    time.sleep(0.02)
                
                for _ in range(4):
                    modal.after(0, append_text, ".")
                    time.sleep(0.4)
                modal.after(0, append_text, "\n\n")

                import socket
                host = "127.0.0.1" if server_ip in ["0.0.0.0", ""] else server_ip
                
                success = False
                try:
                    with socket.create_connection((host, server_port), timeout=3):
                        success = True
                except Exception:
                    success = False

                if success:
                    type_effect("> El servidor esta en optimas condiciones:", "highlight")
                    time.sleep(0.2)
                    type_effect(f"> {server_name}: Hola mundo!")
                else:
                    type_effect("> el servidor no a respondido", "error")


        def _start_server(server_id):
            success = mgr.start_server(server_id)
            if success:
                refresh_server_list()
            else:
                messagebox.showerror("Error", "No se pudo iniciar el servidor.", parent=self)


        def _stop_server(server_id):
            mgr.stop_server(server_id)
            refresh_server_list()


        def _delete_server(server_id, server_name):
            if not messagebox.askyesno(
                "Eliminar servidor",
                f"¿Eliminar el servidor '{server_name}'?\nEsto lo detendrá si está encendido.",
                parent=self,
            ):
                return
            mgr.delete_server(server_id)
            refresh_server_list()


        def auto_refresh():
            if self.tabview.active_tab != "Servidor":
                try:
                    if self.winfo_exists():
                        self.after(5000, auto_refresh)
                except Exception:
                    pass
                return
            try:
                if self.winfo_exists():
                    servers = mgr.get_all_servers()
                    current_snapshot = [(s["id_servidor"], s["estado"], s["pid"]) for s in servers]
                    
                    if not hasattr(self, "_last_servers_snapshot") or self._last_servers_snapshot != current_snapshot:
                        self._last_servers_snapshot = current_snapshot
                        refresh_server_list()
                    else:
                        for srv in servers:
                            if srv["estado"] == "encendido":
                                sid = srv["id_servidor"]
                                usage = mgr.get_server_resources(sid)
                                if usage and sid in self.resource_labels and self.resource_labels[sid].winfo_exists():
                                    ram_pct = min(100, int((usage["ram_used_mb"] / max(1, srv["ram_mb"])) * 100))
                                    ram_bar_color = "#00e676" if ram_pct < 70 else ("#ffab00" if ram_pct < 90 else "#ff4757")
                                    self.resource_labels[sid].configure(
                                        text=f"USO: RAM {usage['ram_used_mb']}MB/{srv['ram_mb']}MB ({ram_pct}%)  •  CPU {usage['cpu_percent']}%",
                                        text_color=ram_bar_color
                                    )
                    self.after(5000, auto_refresh)
            except Exception:
                pass

