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

class AlojamientoMixin:

    def _build_alojamiento_tab(self):
        tab = self.tabview.tab("Alojamiento")
        tab.configure(fg_color="#0d0e1a")

        header = ctk.CTkFrame(tab, fg_color="#12132a", corner_radius=12, height=70)
        header.pack(fill="x", padx=16, pady=(16, 8))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="🎮 ALOJAMIENTO",
            font=("Arial", 20, "bold"),
            text_color="#0fbcf9",
        ).pack(side="left", padx=16, pady=14)
        
        ctk.CTkLabel(
            header,
            text="  —  Servidores de Juegos y Programas",
            font=("Arial", 12),
            text_color="#5a5c7a",
        ).pack(side="left", pady=14)

        self.alojamiento_body = ctk.CTkFrame(tab, fg_color="transparent")
        self.alojamiento_body.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # Main Selection View
        self.alojamiento_selection_view = ctk.CTkFrame(self.alojamiento_body, fg_color="transparent")
        self.alojamiento_selection_view.pack(fill="both", expand=True)

        self.alojamiento_selection_view.grid_columnconfigure(0, weight=1)
        self.alojamiento_selection_view.grid_columnconfigure(1, weight=1)
        self.alojamiento_selection_view.grid_rowconfigure(0, weight=1)

        # Games Server Card
        games_card = ctk.CTkFrame(self.alojamiento_selection_view, fg_color="#12132a", corner_radius=12, cursor="hand2")
        games_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=20)
        games_card.bind("<Button-1>", lambda e: self._show_terraria_wizard())
        
        ctk.CTkLabel(games_card, text="🎮", font=("Arial", 60)).pack(pady=(60, 20))
        ctk.CTkLabel(games_card, text="SERVER DE JUEGOS", font=("Arial", 18, "bold"), text_color="#ffffff").pack(pady=10)
        ctk.CTkLabel(games_card, text="Alojamiento para juegos multijugador", font=("Arial", 12), text_color="#8c8da5").pack(pady=10)

        for child in games_card.winfo_children():
            child.bind("<Button-1>", lambda e: self._show_terraria_wizard())

        # Programs Server Card
        programs_card = ctk.CTkFrame(self.alojamiento_selection_view, fg_color="#12132a", corner_radius=12, cursor="hand2")
        programs_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=20)
        
        ctk.CTkLabel(programs_card, text="💻", font=("Arial", 60)).pack(pady=(60, 20))
        ctk.CTkLabel(programs_card, text="SERVER PROGRAMS", font=("Arial", 18, "bold"), text_color="#ffffff").pack(pady=10)
        ctk.CTkLabel(programs_card, text="Alojamiento para utilidades y web", font=("Arial", 12), text_color="#8c8da5").pack(pady=10)

        # Terraria Wizard View
        self.terraria_wizard_view = ctk.CTkFrame(self.alojamiento_body, fg_color="transparent")
        
        wizard_container = ctk.CTkFrame(self.terraria_wizard_view, fg_color="#12132a", corner_radius=12)
        wizard_container.pack(fill="both", expand=True, pady=20)

        ctk.CTkLabel(wizard_container, text="SERVER DE TERRARIA", font=("Arial", 20, "bold"), text_color="#00e676").pack(pady=(40, 10))
        ctk.CTkLabel(wizard_container, text="Seleccione el servidor activo para transmutar:", font=("Arial", 14), text_color="#ffffff").pack(pady=20)

        from app.utils.server_manager import ServerManager
        self.alojamiento_server_var = ctk.StringVar(value="")
        
        menu_frame = ctk.CTkFrame(wizard_container, fg_color="transparent")
        menu_frame.pack(pady=20)
        
        self.alojamiento_server_menu = ctk.CTkOptionMenu(
            menu_frame, 
            variable=self.alojamiento_server_var,
            values=["Cargando..."],
            fg_color="#1a1b30",
            button_color="#2c2e4a",
            width=250
        )
        self.alojamiento_server_menu.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            menu_frame, text="⟳", width=36, height=28, fg_color="#1a1b30", hover_color="#2c2e4a",
            command=self._refresh_terraria_wizard_servers
        ).pack(side="left")

        btns_frame = ctk.CTkFrame(wizard_container, fg_color="transparent")
        btns_frame.pack(pady=40)

        ctk.CTkButton(
            btns_frame, text="Volver", command=self._show_alojamiento_selection,
            fg_color="#1a1b30", hover_color="#2c2e4a", width=120
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btns_frame, text="Siguiente", command=self._show_terraria_panel,
            fg_color="#00e676", hover_color="#00c864", text_color="#0d0e1a", width=120
        ).pack(side="left", padx=10)

        # Terraria Control Panel View
        self.terraria_panel_view = ctk.CTkFrame(self.alojamiento_body, fg_color="transparent")
        
        panel_top = ctk.CTkFrame(self.terraria_panel_view, fg_color="transparent")
        panel_top.pack(fill="x", pady=(0, 16))
        
        ctk.CTkButton(panel_top, text="← Volver", command=self._show_terraria_wizard, width=80, fg_color="#1a1b30", hover_color="#2c2e4a").pack(side="left")
        self.terraria_panel_title = ctk.CTkLabel(panel_top, text="Panel de Control - Terraria", font=("Arial", 16, "bold"), text_color="#00e676")
        self.terraria_panel_title.pack(side="left", padx=20)

        panel_content = ctk.CTkFrame(self.terraria_panel_view, fg_color="transparent")
        panel_content.pack(fill="both", expand=True)
        panel_content.grid_columnconfigure(0, weight=1)
        panel_content.grid_columnconfigure(1, weight=1)
        panel_content.grid_rowconfigure(0, weight=1)

        # Left Column - Controls & Graph
        self.panel_left = ctk.CTkScrollableFrame(panel_content, fg_color="transparent")
        self.panel_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        
        # Graph Card
        graph_card = ctk.CTkFrame(self.panel_left, fg_color="#12132a", corner_radius=12, height=200)
        graph_card.pack(fill="x", pady=(0, 16))
        graph_card.pack_propagate(False)
        ctk.CTkLabel(graph_card, text="JUGADORES EN LÍNEA", font=("Arial", 11, "bold"), text_color="#ffffff", anchor="w").pack(fill="x", padx=15, pady=(12, 5))
        self.terraria_graph_canvas = __import__("tkinter").Canvas(graph_card, bg="#12132a", highlightthickness=0)
        self.terraria_graph_canvas.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.terraria_graph_canvas.bind("<Configure>", lambda e: self._refresh_terraria_graph())

        # Config Card
        config_card = ctk.CTkFrame(self.panel_left, fg_color="#12132a", corner_radius=12)
        config_card.pack(fill="x", pady=(0, 16))
        
        ctk.CTkLabel(config_card, text="CONFIGURACIÓN", font=("Arial", 11, "bold"), text_color="#ffffff", anchor="w").pack(fill="x", padx=15, pady=(12, 5))
        
        conf_row = ctk.CTkFrame(config_card, fg_color="transparent")
        conf_row.pack(fill="x", padx=15, pady=(5, 15))
        ctk.CTkLabel(conf_row, text="Jugadores Máximos:", text_color="#8c8da5").pack(side="left")
        self.terraria_max_players = ctk.CTkEntry(conf_row, width=60, justify="center")
        self.terraria_max_players.insert(0, "8")
        self.terraria_max_players.pack(side="right")

        # Tunnel Card
        tunnel_card = ctk.CTkFrame(self.panel_left, fg_color="#12132a", corner_radius=12)
        tunnel_card.pack(fill="x")
        
        ctk.CTkLabel(tunnel_card, text="TRANSMUTACIÓN (TUNNEL)", font=("Arial", 11, "bold"), text_color="#ffffff", anchor="w").pack(fill="x", padx=15, pady=(12, 5))
        
        self.tunnel_status_label = ctk.CTkLabel(tunnel_card, text="ESTADO: DESACTIVADO", text_color="#ff4757", font=("Arial", 12, "bold"))
        self.tunnel_status_label.pack(pady=5)
        
        self.tunnel_inst_label = ctk.CTkLabel(tunnel_card, text="", text_color="#8c8da5", font=("Arial", 11))
        self.tunnel_inst_label.pack()
        
        # IP Frame (IP + copy button)
        self.tunnel_ip_frame = ctk.CTkFrame(tunnel_card, fg_color="transparent")
        self.tunnel_ip_val_lbl = ctk.CTkLabel(self.tunnel_ip_frame, text="", text_color="#0fbcf9", font=("Arial", 12, "bold"))
        self.tunnel_ip_val_lbl.pack(side="left", padx=(0, 10))
        self.tunnel_ip_copy_btn = ctk.CTkButton(
            self.tunnel_ip_frame, text="Copiar IP", width=65, height=24, font=("Arial", 10, "bold"), 
            fg_color="#1a1b30", hover_color="#2c2e4a", border_width=1, border_color="#2c2e4a",
            command=self._copy_ip
        )
        self.tunnel_ip_copy_btn.pack(side="left")
        
        # Port Frame (Port + copy button)
        self.tunnel_port_frame = ctk.CTkFrame(tunnel_card, fg_color="transparent")
        self.tunnel_port_val_lbl = ctk.CTkLabel(self.tunnel_port_frame, text="", text_color="#00e676", font=("Arial", 12, "bold"))
        self.tunnel_port_val_lbl.pack(side="left", padx=(0, 10))
        self.tunnel_port_copy_btn = ctk.CTkButton(
            self.tunnel_port_frame, text="Copiar Puerto", width=85, height=24, font=("Arial", 10, "bold"), 
            fg_color="#1a1b30", hover_color="#2c2e4a", border_width=1, border_color="#2c2e4a",
            command=self._copy_port
        )
        self.tunnel_port_copy_btn.pack(side="left")

        # Public IP Section (Domain + entry + copy button)
        self.tunnel_pub_title_lbl = ctk.CTkLabel(tunnel_card, text="🌐 CONEXIÓN INTERNET (Externa):", font=("Arial", 11, "bold"), text_color="#ffea00")
        
        self.tunnel_pub_ip_frame = ctk.CTkFrame(tunnel_card, fg_color="transparent")
        self.tunnel_pub_ip_lbl = ctk.CTkLabel(self.tunnel_pub_ip_frame, text="IP/Dominio:", text_color="#8c8da5", font=("Arial", 11))
        self.tunnel_pub_ip_lbl.pack(side="left", padx=5)
        self.tunnel_pub_ip_entry = ctk.CTkEntry(self.tunnel_pub_ip_frame, width=180, height=24, font=("Arial", 11))
        self.tunnel_pub_ip_entry.pack(side="left", padx=5)
        self.tunnel_pub_ip_copy_btn = ctk.CTkButton(
            self.tunnel_pub_ip_frame, text="Copiar", width=55, height=24, font=("Arial", 10, "bold"),
            fg_color="#1a1b30", hover_color="#2c2e4a", border_width=1, border_color="#2c2e4a",
            command=self._copy_pub_ip
        )
        self.tunnel_pub_ip_copy_btn.pack(side="left", padx=5)
        
        # Public Port Section (Port + entry + copy button)
        self.tunnel_pub_port_frame = ctk.CTkFrame(tunnel_card, fg_color="transparent")
        self.tunnel_pub_port_lbl = ctk.CTkLabel(self.tunnel_pub_port_frame, text="Puerto:", text_color="#8c8da5", font=("Arial", 11))
        self.tunnel_pub_port_lbl.pack(side="left", padx=5)
        self.tunnel_pub_port_entry = ctk.CTkEntry(self.tunnel_pub_port_frame, width=70, height=24, font=("Arial", 11))
        self.tunnel_pub_port_entry.pack(side="left", padx=5)
        self.tunnel_pub_port_copy_btn = ctk.CTkButton(
            self.tunnel_pub_port_frame, text="Copiar", width=55, height=24, font=("Arial", 10, "bold"),
            fg_color="#1a1b30", hover_color="#2c2e4a", border_width=1, border_color="#2c2e4a",
            command=self._copy_pub_port
        )
        self.tunnel_pub_port_copy_btn.pack(side="left", padx=5)
        
        self.tunnel_pub_ip_entry.bind("<KeyRelease>", self._save_tunnel_settings)
        self.tunnel_pub_port_entry.bind("<KeyRelease>", self._save_tunnel_settings)

        # Playit.gg info label
        self.tunnel_playit_info_lbl = ctk.CTkLabel(tunnel_card, text="", text_color="#8c8da5", font=("Arial", 11), justify="center")

        tunnel_btns = ctk.CTkFrame(tunnel_card, fg_color="transparent")
        tunnel_btns.pack(pady=15)
        
        self.btn_act_tunnel = ctk.CTkButton(tunnel_btns, text="Activar Túnel", fg_color="#0fbcf9", hover_color="#0da0d4", text_color="#0d0e1a", command=self._activate_tunnel)
        self.btn_act_tunnel.pack(side="left", padx=5)
        self.btn_desact_tunnel = ctk.CTkButton(tunnel_btns, text="Desactivar", fg_color="#ff4757", hover_color="#cc3847", command=self._deactivate_tunnel, state="disabled")
        self.btn_desact_tunnel.pack(side="left", padx=5)

        # Right Column - Active Players & Bans
        panel_right = ctk.CTkFrame(panel_content, fg_color="#12132a", corner_radius=12)
        panel_right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        
        # JUGADORES ACTIVOS
        ctk.CTkLabel(panel_right, text="JUGADORES ACTIVOS", font=("Arial", 11, "bold"), text_color="#00e676", anchor="w").pack(fill="x", padx=15, pady=(12, 5))
        self.active_players_frame = ctk.CTkScrollableFrame(panel_right, fg_color="transparent", height=150)
        self.active_players_frame.pack(fill="both", expand=True, padx=15, pady=(5, 10))
        
        # Separator line
        separator = ctk.CTkFrame(panel_right, height=2, fg_color="#1a1b30")
        separator.pack(fill="x", padx=15, pady=5)
        
        # LISTA DE BANEOS
        ctk.CTkLabel(panel_right, text="LISTA DE BANEOS", font=("Arial", 11, "bold"), text_color="#ffffff", anchor="w").pack(fill="x", padx=15, pady=(10, 5))
        
        ban_input_frame = ctk.CTkFrame(panel_right, fg_color="transparent")
        ban_input_frame.pack(fill="x", padx=15, pady=5)
        self.ban_entry = ctk.CTkEntry(ban_input_frame, placeholder_text="Nombre / IP")
        self.ban_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(ban_input_frame, text="Banear", width=80, fg_color="#ff4757", hover_color="#cc3847", command=self._add_ban).pack(side="right")

        self.bans_list_frame = ctk.CTkScrollableFrame(panel_right, fg_color="transparent", height=150)
        self.bans_list_frame.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        self.banned_list = []

        self._refresh_bans()

        bind_mouse_wheel_recursive(self.panel_left, self.panel_left)
        bind_mouse_wheel_recursive(self.active_players_frame, self.active_players_frame)
        bind_mouse_wheel_recursive(self.bans_list_frame, self.bans_list_frame)


    def _show_alojamiento_selection(self):
        self.terraria_wizard_view.pack_forget()
        self.terraria_panel_view.pack_forget()
        self.alojamiento_selection_view.pack(fill="both", expand=True)


    def _show_terraria_wizard(self):
        self.alojamiento_selection_view.pack_forget()
        self.terraria_panel_view.pack_forget()
        self.terraria_wizard_view.pack(fill="both", expand=True)
        self._refresh_terraria_wizard_servers()


    def _refresh_terraria_wizard_servers(self):
        from app.utils.server_manager import ServerManager
        mgr = ServerManager()
        servers = mgr.get_all_servers()
        active_servers = [s['nombre'] for s in servers if s['estado'] == 'encendido']
        
        if active_servers:
            self.alojamiento_server_menu.configure(values=active_servers)
            if self.alojamiento_server_var.get() not in active_servers:
                self.alojamiento_server_menu.set(active_servers[0])
        else:
            self.alojamiento_server_menu.configure(values=["No hay servidores activos"])
            self.alojamiento_server_menu.set("No hay servidores activos")


    def _show_terraria_panel(self):
        selected = self.alojamiento_server_var.get()
        if not selected or selected == "No hay servidores activos" or selected == "Cargando...":
            __import__("tkinter").messagebox.showerror("Error", "Seleccione un servidor activo primero.")
            return

        self.terraria_panel_title.configure(text=f"Panel de Control - {selected} (Terraria)")
        self.terraria_wizard_view.pack_forget()
        self.alojamiento_selection_view.pack_forget()
        self.terraria_panel_view.pack(fill="both", expand=True)
        self._refresh_terraria_graph()


    def _refresh_terraria_graph(self, update_data=False):
        if not hasattr(self, "terraria_graph_canvas") or not self.terraria_graph_canvas.winfo_exists():
            return
        
        from app.utils.server_manager import ServerManager
        mgr = ServerManager()
        selected = self.alojamiento_server_var.get()
        servers = mgr.get_all_servers()
        srv = next((s for s in servers if s['nombre'] == selected), None)
        
        active_players = []
        if srv:
            active_players = mgr.get_active_players(srv['id_servidor'])
            # Sincronizar lista de baneos desde ServerManager
            srv_bans = mgr.get_bans(srv['id_servidor'])
            for ban_target in srv_bans:
                if ban_target not in self.banned_list:
                    self.banned_list.append(ban_target)
            self._refresh_bans()
            
        real_count = len(active_players)

        if not hasattr(self, "terraria_players_history"):
            self.terraria_players_history = [real_count] * 7
            self.after(3000, self._terraria_graph_timer)
            
        if update_data:
            self.terraria_players_history.append(real_count)
            if len(self.terraria_players_history) > 7:
                self.terraria_players_history.pop(0)
        
        # Always refresh active players list UI
        self._refresh_active_players_list(active_players)
        
        c = self.terraria_graph_canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 10 or h < 10: return

        # Draw grid
        max_p_str = self.terraria_max_players.get()
        max_val = int(max_p_str) if max_p_str.isdigit() and int(max_p_str) > 0 else 10
        if max_val < max(self.terraria_players_history):
            max_val = max(self.terraria_players_history) + 2

        chart_top = 20
        chart_bottom = h - 20
        chart_left = 30
        chart_right = w - 10
        chart_height = chart_bottom - chart_top
        chart_width = chart_right - chart_left

        for i in range(5):
            val = (max_val / 4) * i
            y = chart_bottom - (val / max_val) * chart_height
            c.create_line(chart_left, y, chart_right, y, fill="#2c2e4a", dash=(4, 4))
            c.create_text(chart_left - 10, y, text=str(int(val)), fill="#8c8da5", font=("Arial", 8), anchor="e")

        # Dynamic data for players
        pts = list(enumerate(self.terraria_players_history))
        
        coords = []
        for px, py in pts:
            cx = chart_left + (px * (chart_width / 6))
            cy = chart_bottom - (py / max_val) * chart_height
            coords.extend([cx, cy])
            c.create_oval(cx-3, cy-3, cx+3, cy+3, fill="#00e676", outline="")

        if len(coords) >= 4:
            c.create_line(coords, fill="#00e676", width=2, smooth=True, splinesteps=36)

        c.create_text(w/2, chart_bottom+10, text="Tiempo", fill="#8c8da5", font=("Arial", 8))


    def _terraria_graph_timer(self):
        if hasattr(self, "terraria_graph_canvas") and self.terraria_graph_canvas.winfo_exists():
            self._refresh_terraria_graph(update_data=True)
            self.after(3000, self._terraria_graph_timer)


    def _refresh_active_players_list(self, active_players):
        if not hasattr(self, "active_players_frame") or not self.active_players_frame.winfo_exists():
            return

        for w in self.active_players_frame.winfo_children():
            w.destroy()

        if not active_players:
            ctk.CTkLabel(self.active_players_frame, text="No hay jugadores activos", text_color="#5a5c7a").pack(pady=20)
            return

        from app.utils.server_manager import ServerManager
        mgr = ServerManager()
        selected = self.alojamiento_server_var.get()
        servers = mgr.get_all_servers()
        srv = next((s for s in servers if s['nombre'] == selected), None)
        
        creator = ""
        if srv:
            creator = mgr.get_creator(srv['id_servidor'])

        for player in active_players:
            f = ctk.CTkFrame(self.active_players_frame, fg_color="#1a1b30")
            f.pack(fill="x", pady=2)

            dot_canvas = tk.Canvas(f, width=10, height=10, bg="#1a1b30", highlightthickness=0)
            dot_canvas.pack(side="left", padx=(10, 5), pady=8)
            dot_canvas.create_oval(1, 1, 9, 9, fill="#00e676", outline="")

            is_creator = (player == creator)
            display_name = f"👑 {player}" if is_creator else player

            ctk.CTkLabel(f, text=display_name, text_color="#ffffff", font=("Arial", 12, "bold")).pack(side="left", padx=5, pady=5)

            ctk.CTkButton(
                f,
                text="Expulsar",
                font=("Arial", 10, "bold"),
                fg_color="#ff4757",
                hover_color="#cc3847",
                text_color="#ffffff",
                corner_radius=6,
                width=65,
                height=22,
                command=lambda p=player: self._kick_player(p),
            ).pack(side="right", padx=5, pady=5)

            ctk.CTkButton(
                f,
                text="Creador",
                font=("Arial", 10, "bold"),
                fg_color="#ffea00" if is_creator else "#ffb300",
                hover_color="#ff8f00",
                text_color="#000000",
                corner_radius=6,
                width=65,
                height=22,
                command=lambda p=player: self._set_creator(p),
            ).pack(side="right", padx=5, pady=5)


    def _set_creator(self, player_name):
        from app.utils.server_manager import ServerManager
        mgr = ServerManager()
        selected = self.alojamiento_server_var.get()
        servers = mgr.get_all_servers()
        srv = next((s for s in servers if s['nombre'] == selected), None)
        if srv:
            current_creator = mgr.get_creator(srv['id_servidor'])
            if current_creator == player_name:
                mgr.set_creator(srv['id_servidor'], "")
            else:
                mgr.set_creator(srv['id_servidor'], player_name)
            self._refresh_active_players_list(mgr.get_active_players(srv['id_servidor']))


    def _kick_player(self, player_name):
        if not messagebox.askyesno(
            "Expulsar jugador",
            f"¿Estás seguro de que deseas expulsar a '{player_name}' del servidor?",
            parent=self
        ):
            return

        from app.utils.server_manager import ServerManager
        mgr = ServerManager()
        selected = self.alojamiento_server_var.get()
        servers = mgr.get_all_servers()
        srv = next((s for s in servers if s['nombre'] == selected), None)
        if srv:
            mgr.send_server_command(srv['id_servidor'], f"kick {player_name}")
            self.after(500, lambda: self._refresh_terraria_graph(update_data=False))


    def _add_ban(self):
        b_target = self.ban_entry.get().strip()
        if b_target:
            self.banned_list.append(b_target)
            self.ban_entry.delete(0, 'end')
            self._refresh_bans()

            from app.utils.server_manager import ServerManager
            mgr = ServerManager()
            selected = self.alojamiento_server_var.get()
            servers = mgr.get_all_servers()
            srv = next((s for s in servers if s['nombre'] == selected), None)
            if srv:
                mgr.send_server_command(srv['id_servidor'], f"ban {b_target}")
                mgr.add_ban(srv['id_servidor'], b_target)


    def _remove_ban(self, b_target):
        if b_target in self.banned_list:
            self.banned_list.remove(b_target)
            
            from app.utils.server_manager import ServerManager
            mgr = ServerManager()
            selected = self.alojamiento_server_var.get()
            servers = mgr.get_all_servers()
            srv = next((s for s in servers if s['nombre'] == selected), None)
            if srv:
                mgr.send_server_command(srv['id_servidor'], f"unban {b_target}")
                # Also remove from ServerManager's list if present
                with mgr._lock:
                    if srv['id_servidor'] in mgr._banned_players and b_target in mgr._banned_players[srv['id_servidor']]:
                        mgr._banned_players[srv['id_servidor']].remove(b_target)
            
            self._refresh_bans()


    def _refresh_bans(self):
        for w in self.bans_list_frame.winfo_children():
            w.destroy()
        
        if not self.banned_list:
            ctk.CTkLabel(self.bans_list_frame, text="No hay baneos", text_color="#5a5c7a").pack(pady=20)
            return
            
        for b in self.banned_list:
            f = ctk.CTkFrame(self.bans_list_frame, fg_color="#1a1b30")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=b, text_color="#ffffff").pack(side="left", padx=10, pady=5)
            ctk.CTkButton(f, text="X", width=30, fg_color="#ff4757", hover_color="#cc3847", command=lambda x=b: self._remove_ban(x)).pack(side="right", padx=5, pady=5)


    def _activate_tunnel(self):
        self.btn_act_tunnel.configure(state="disabled")
        self.tunnel_status_label.configure(text="Iniciando transmutación...", text_color="#ffab00")
        
        from app.utils.server_manager import ServerManager
        mgr = ServerManager()
        selected = self.alojamiento_server_var.get()
        servers = mgr.get_all_servers()
        srv = next((s for s in servers if s['nombre'] == selected), None)
        port = srv['puerto'] if srv else 8080
        
        # Determine initial public IP/port values
        db_tunnel_ip = srv.get('tunnel_ip') if srv else None
        db_tunnel_port = srv.get('tunnel_port') if srv else None
        
        # Check if playit service is active
        playit_active = False
        try:
            import subprocess
            res = subprocess.run(["playit", "status"], capture_output=True, text=True, timeout=2)
            if "Phase: running" in res.stdout:
                playit_active = True
        except Exception:
            pass

        # Start simulated/placeholder tunnel process via manager
        url = mgr.start_tunnel(port)
        
        # Get actual LAN IP
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"

        if url:
            # Set up initial public IP/port if not configured in DB
            import random
            if not db_tunnel_ip or db_tunnel_ip == 'communications-sn.gl.at.ply.gg':
                if ":" in url:
                    initial_pub_ip, initial_pub_port = url.split(":", 1)
                else:
                    initial_pub_ip = url or 'communications-sn.gl.at.ply.gg'
                    initial_pub_port = str(random.randint(10000, 65535))
            else:
                initial_pub_ip = db_tunnel_ip
                initial_pub_port = str(db_tunnel_port) if db_tunnel_port else str(random.randint(10000, 65535))

            self.tunnel_status_label.configure(text="ESTADO: OPERATIVO", text_color="#00e676")
            
            # Local connection UI
            self.tunnel_inst_label.configure(text="⚡ CONEXIÓN LOCAL (Wi-Fi):")
            self.tunnel_ip_val_lbl.configure(text=f"IP Local: {local_ip}")
            self.tunnel_port_val_lbl.configure(text=f"Puerto: {port}")
            self.tunnel_ip_frame.pack(pady=4)
            self.tunnel_port_frame.pack(pady=4)
            
            # Public connection UI
            self.tunnel_pub_title_lbl.pack(pady=(12, 4))
            self.tunnel_pub_ip_entry.delete(0, 'end')
            self.tunnel_pub_ip_entry.insert(0, initial_pub_ip)
            self.tunnel_pub_port_entry.delete(0, 'end')
            self.tunnel_pub_port_entry.insert(0, initial_pub_port)
            self.tunnel_pub_ip_frame.pack(pady=4)
            self.tunnel_pub_port_frame.pack(pady=4)
            
            # Show playit.gg information
            playit_status_text = "Playit.gg está ACTIVO en tu PC." if playit_active else "Playit.gg no está activo como servicio de Windows."
            self.tunnel_playit_info_lbl.configure(
                text=f"🌐 {playit_status_text}\nConfigura un túnel para el puerto {port} en tu panel de playit.gg\npara permitir conexiones externas desde Internet."
            )
            self.tunnel_playit_info_lbl.pack(pady=(10, 5))
            
            self.btn_desact_tunnel.configure(state="normal")
            
            # Update mouse wheel bindings on new packed widgets
            bind_mouse_wheel_recursive(self.tunnel_ip_frame, self.panel_left)
            bind_mouse_wheel_recursive(self.tunnel_port_frame, self.panel_left)
            bind_mouse_wheel_recursive(self.tunnel_pub_ip_frame, self.panel_left)
            bind_mouse_wheel_recursive(self.tunnel_pub_port_frame, self.panel_left)
            bind_mouse_wheel_recursive(self.tunnel_playit_info_lbl, self.panel_left)
        else:
            self.tunnel_status_label.configure(text="Error al iniciar túnel", text_color="#ff4757")
            self.tunnel_inst_label.configure(text="")
            self.tunnel_ip_val_lbl.configure(text="")
            self.tunnel_port_val_lbl.configure(text="")
            self.tunnel_ip_frame.pack_forget()
            self.tunnel_port_frame.pack_forget()
            self.tunnel_pub_title_lbl.pack_forget()
            self.tunnel_pub_ip_frame.pack_forget()
            self.tunnel_pub_port_frame.pack_forget()
            self.tunnel_playit_info_lbl.pack_forget()
            self.btn_act_tunnel.configure(state="normal")


    def _deactivate_tunnel(self):
        from app.utils.server_manager import ServerManager
        mgr = ServerManager()
        mgr.stop_tunnel()
        
        self.tunnel_status_label.configure(text="ESTADO: DESACTIVADO", text_color="#ff4757")
        self.tunnel_inst_label.configure(text="")
        self.tunnel_ip_val_lbl.configure(text="")
        self.tunnel_port_val_lbl.configure(text="")
        self.tunnel_ip_frame.pack_forget()
        self.tunnel_port_frame.pack_forget()
        self.tunnel_pub_title_lbl.pack_forget()
        self.tunnel_pub_ip_frame.pack_forget()
        self.tunnel_pub_port_frame.pack_forget()
        self.tunnel_playit_info_lbl.pack_forget()
        
        self.btn_act_tunnel.configure(state="normal")
        self.btn_desact_tunnel.configure(state="disabled")


    def _save_tunnel_settings(self, event=None):
        from app.utils.server_manager import ServerManager
        mgr = ServerManager()
        selected = self.alojamiento_server_var.get()
        servers = mgr.get_all_servers()
        srv = next((s for s in servers if s['nombre'] == selected), None)
        if srv:
            pub_ip = self.tunnel_pub_ip_entry.get().strip()
            pub_port_str = self.tunnel_pub_port_entry.get().strip()
            pub_port = int(pub_port_str) if pub_port_str.isdigit() else None
            
            # Update database
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE servidores SET tunnel_ip = ?, tunnel_port = ? WHERE id_servidor = ?",
                (pub_ip, pub_port, srv['id_servidor'])
            )
            conn.commit()
            conn.close()


    def _copy_ip(self):
        val = self.tunnel_ip_val_lbl.cget("text")
        if ":" in val:
            ip_val = val.split(":", 1)[1].strip()
            self.clipboard_clear()
            self.clipboard_append(ip_val)
            self.update()
            self.tunnel_ip_copy_btn.configure(text="¡Copiado!", fg_color="#00e676", text_color="#0d0e1a")
            self.after(2000, lambda: self.tunnel_ip_copy_btn.configure(text="Copiar IP", fg_color="#1a1b30", text_color="#ffffff"))

    def _copy_port(self):
        val = self.tunnel_port_val_lbl.cget("text")
        if ":" in val:
            port_val = val.split(":", 1)[1].strip()
            self.clipboard_clear()
            self.clipboard_append(port_val)
            self.update()
            self.tunnel_port_copy_btn.configure(text="¡Copiado!", fg_color="#00e676", text_color="#0d0e1a")
            self.after(2000, lambda: self.tunnel_port_copy_btn.configure(text="Copiar Puerto", fg_color="#1a1b30", text_color="#ffffff"))

    def _copy_pub_ip(self):
        val = self.tunnel_pub_ip_entry.get().strip()
        if val:
            self.clipboard_clear()
            self.clipboard_append(val)
            self.update()
            self.tunnel_pub_ip_copy_btn.configure(text="¡Copiado!", fg_color="#00e676", text_color="#0d0e1a")
            self.after(2000, lambda: self.tunnel_pub_ip_copy_btn.configure(text="Copiar", fg_color="#1a1b30", text_color="#ffffff"))

    def _copy_pub_port(self):
        val = self.tunnel_pub_port_entry.get().strip()
        if val:
            self.clipboard_clear()
            self.clipboard_append(val)
            self.update()
            self.tunnel_pub_port_copy_btn.configure(text="¡Copiado!", fg_color="#00e676", text_color="#0d0e1a")
            self.after(2000, lambda: self.tunnel_pub_port_copy_btn.configure(text="Copiar", fg_color="#1a1b30", text_color="#ffffff"))

