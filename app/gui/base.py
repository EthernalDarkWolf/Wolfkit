import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class GuiArchitect(ctk.CTk):
    DEFAULT_SIZE = "940x620"
    DEFAULT_BG = "#2f2f2f"
    DEFAULT_ALPHA = 0.92
    DEFAULT_BUTTON_COLOR = "#444444"
    DEFAULT_BUTTON_HOVER = "#5f5f5f"
    DEFAULT_TEXT_COLOR = "#f5f5f5"

    def __init__(self, title="Educación", size=None, alpha=None, fg_color=None, resizable=(True, True)):
        super().__init__()
        self.title(title)
        self.geometry(size or self.DEFAULT_SIZE)
        self.resizable(*resizable)
        self.configure(fg_color=fg_color or self.DEFAULT_BG)
        self.wm_attributes("-alpha", alpha if alpha is not None else self.DEFAULT_ALPHA)

        self.body = ctk.CTkFrame(self, fg_color=self.cget("fg_color"))
        self.body.pack(fill="both", expand=True, padx=14, pady=14)
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)

        self.protocol("WM_DELETE_WINDOW", self.quit)
        self.widgets = []

    def create_label(self, text, master=None, **kwargs):
        parent = master or self.body
        text_color = kwargs.pop("text_color", self.DEFAULT_TEXT_COLOR)
        label = ctk.CTkLabel(
            parent,
            text=text,
            text_color=text_color,
            **kwargs,
        )
        self.widgets.append(label)
        return label

    def create_button(self, text, command=None, master=None, **kwargs):
        parent = master or self.body
        button = ctk.CTkButton(
            parent,
            text=text,
            command=command,
            fg_color=kwargs.pop("fg_color", self.DEFAULT_BUTTON_COLOR),
            hover_color=kwargs.pop("hover_color", self.DEFAULT_BUTTON_HOVER),
            text_color=kwargs.pop("text_color", self.DEFAULT_TEXT_COLOR),
            corner_radius=kwargs.pop("corner_radius", 12),
            **kwargs,
        )
        self.widgets.append(button)
        return button

    def create_entry(self, placeholder_text="", master=None, **kwargs):
        parent = master or self.body
        entry = ctk.CTkEntry(
            parent,
            placeholder_text=placeholder_text,
            fg_color="#3a3a3a",
            text_color=self.DEFAULT_TEXT_COLOR,
            **kwargs,
        )
        self.widgets.append(entry)
        return entry

    def run(self):
        try:
            self.mainloop()
        except Exception:
            pass
