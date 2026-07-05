mport customtkinter as ctk
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
        self.resizable(False, False) # 