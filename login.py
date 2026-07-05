import customtkinter as ctk
from tkinter import messagebox

# 1. Configuración del tema y color de la aplicación
ctk.set_appearance_mode("System")  # Opciones: "System", "Dark", "Light"
ctk.set_default_color_theme("blue") # Opciones: "blue", "green", "dark-blue"

# 2. Definición de la clase principal para la ventana
class AppLogin(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 3. Configuración de la ventana principal
        self.title("Mi primer login")
        self.geometry("400x350")
        self.resizable(False, False) # Evita que se maximice para mantener el diseño

        # --- COMPONENTES DE LA INTERFAZ (WIDGETS) ---

        # Etiqueta de Título
        self.title_label = ctk.CTkLabel(
            self, 
            text="Iniciar Sesión", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=(40, 20)) # Margen: 40 arriba, 20 abajo

        # Campo de texto para el Usuario
        self.username_entry = ctk.CTkEntry(
            self, 
            placeholder_text="Nombre de usuario", 
            width=250
        )
        self.username_entry.pack(pady=10)

        # Campo de texto para la Contraseña
        self.password_entry = ctk.CTkEntry(
            self, 
            placeholder_text="Contraseña", 
            show="*", # Oculta los caracteres con asteriscos
            width=250
        )
        self.password_entry.pack(pady=10)

        # Botón de Ingresar
        self.login_button = ctk.CTkButton(
            self, 
            text="Ingresar", 
            command=self.validar_login, # Método que se ejecuta al hacer clic
            width=250
        )
        self.login_button.pack(pady=20)

    # 4. Lógica del negocio: Validación de datos
    def validar_login(self):
        # Capturamos lo que el usuario escribió en los inputs
        usuario = self.username_entry.get()
        contrasenia = self.password_entry.get()

        # Datos quemados (Hardcoded) para la simulación
        USUARIO_CORRECTO = "admin"
        CONTRASENIA_CORRECTA = "1234"

        # Verificación de campos vacíos
        if not usuario or not contrasenia:
            messagebox.showwarning("Atención", "Por favor, llene todos los campos.")
            return

        # Verificación de credenciales
        if usuario == USUARIO_CORRECTO and contrasenia == CONTRASENIA_CORRECTA:
            messagebox.showinfo("Éxito", f"¡Bienvenido, {usuario}!")
            # Aquí se podría destruir esta ventana y abrir la principal del sistema
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos.")


# 5. Ejecución de la aplicación
if __name__ == "__main__":
    app = AppLogin()
    app.mainloop() # Bucle infinito para mantener la ventana abierta