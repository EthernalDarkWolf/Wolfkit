import customtkinter as ctk

from app import APP_NAME
from .base import GuiArchitect
from ..utils.auth import get_user_info


class LoginApp(GuiArchitect):
    DEFAULT_SIZE = "420x260"

    def __init__(self):
        super().__init__(title=f"{APP_NAME} - Ingreso al sistema", size=self.DEFAULT_SIZE, resizable=(False, False))
        self.authenticated_user = None
        self.authenticated_role = None
        self._build_login_form()

    def _build_login_form(self):
        self.body.grid_columnconfigure(0, weight=1)

        self.create_label("Iniciar sesión", font=("Arial", 20, "bold")).pack(pady=(20, 12))

        form_frame = ctk.CTkFrame(self.body, fg_color="#242424")
        form_frame.pack(fill="x", padx=24, pady=10)
        form_frame.grid_columnconfigure(1, weight=1)

        self.create_label("Usuario:", master=form_frame).grid(row=0, column=0, sticky="w", padx=12, pady=(14, 4))
        self.entry_username = self.create_entry("Usuario", master=form_frame)
        self.entry_username.grid(row=0, column=1, sticky="ew", padx=12, pady=(14, 4))

        self.create_label("Contraseña:", master=form_frame).grid(row=1, column=0, sticky="w", padx=12, pady=(8, 4))
        self.entry_password = self.create_entry("Contraseña", master=form_frame, show="*")
        self.entry_password.grid(row=1, column=1, sticky="ew", padx=12, pady=(8, 4))

        self.create_button("Entrar", command=self.try_login, master=self.body, width=160).pack(pady=(12, 6))
        self.login_message_label = self.create_label("", master=self.body, font=("Arial", 12))
        self.login_message_label.pack()

    def try_login(self):
        username = self.entry_username.get().strip()
        password = self.entry_password.get().strip()

        if not username or not password:
            self.login_message_label.configure(text="Usuario y contraseña son obligatorios.", text_color="#f55a5a")
            return

        user_info = get_user_info(username, password)
        if user_info:
            self.authenticated_user = user_info["username"]
            self.authenticated_role = user_info["role"]
            self.destroy()
            return

        self.login_message_label.configure(text="Usuario o contraseña incorrectos.", text_color="#f55a5a")
