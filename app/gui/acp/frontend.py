import customtkinter as ctk
from tkinter import simpledialog, filedialog, messagebox
import shutil
import os
import threading
from datetime import date
from app.utils.db import insert_acp_cuota, get_acp_cuotas, update_acp_costo, insert_acp_pago, get_acp_pagos, DATABASE_DIR, delete_acp_pago, update_acp_pago, delete_acp_cuota, update_acp_cuota_name

class ACPMixin:

    def _build_acp_tab(self):
        self.acp_tab = self.tabview.tab("ACP")
        self.acp_tab.grid_columnconfigure(0, weight=1)
        self.acp_tab.grid_rowconfigure(0, weight=1)
        self.acp_tab.configure(fg_color="#141523") # Dark theme

        self.acp_main_frame = ctk.CTkFrame(self.acp_tab, fg_color="transparent")
        self.acp_main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.acp_main_frame.grid_columnconfigure(0, weight=1)
        self.acp_main_frame.grid_rowconfigure(1, weight=1)

        self.acp_details_frame = ctk.CTkFrame(self.acp_tab, fg_color="transparent")
        self.acp_details_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.acp_details_frame.grid_remove() # Hide initially

        # Variables for PyDolarVenezuela
        self.current_usd_rate = None
        self.rate_status_var = ctk.StringVar(value="Cargando tasa del BCV...")

        self._fetch_bcv_rate_bg()
        
        self._build_acp_main_view()
        self._build_acp_details_view()
        self._refresh_acp_list()

    def _fetch_bcv_rate_bg(self):
        def fetch():
            try:
                from pyDolarVenezuela.pages import BCV
                from pyDolarVenezuela import Monitor
                m = Monitor(BCV, 'USD')
                dolar_monitor = next((mon for mon in m.get_all_monitors() if mon.title == 'Dólar estadounidense'), None)
                if dolar_monitor and dolar_monitor.price:
                    self.current_usd_rate = float(dolar_monitor.price)
                    self.rate_status_var.set(f"Tasa BCV actual: Bs. {self.current_usd_rate:.2f}")
                else:
                    self.rate_status_var.set("No se pudo obtener la tasa.")
            except Exception as e:
                print("Error obteniendo tasa BCV:", e)
                self.rate_status_var.set("Error de conexión BCV.")
                self.current_usd_rate = None

        threading.Thread(target=fetch, daemon=True).start()

    def _build_acp_main_view(self):
        header_frame = ctk.CTkFrame(self.acp_main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        title_lbl = ctk.CTkLabel(header_frame, text="CUOTAS DIARIAS (ACP)", font=("Arial", 22, "bold"), text_color="#ffffff")
        title_lbl.pack(side="left")

        # BCV Indicator
        bcv_lbl = ctk.CTkLabel(header_frame, textvariable=self.rate_status_var, font=("Arial", 12), text_color="#0fbcf9")
        bcv_lbl.pack(side="left", padx=20)

        add_btn = ctk.CTkButton(header_frame, text="+  NUEVA CUOTA", font=("Arial", 12, "bold"), fg_color="#3e44d6", hover_color="#2b31b3", command=self._add_acp_cuota)
        add_btn.pack(side="right")

        self.acp_scroll_frame = ctk.CTkScrollableFrame(self.acp_main_frame, fg_color="#1b1c2b", corner_radius=10)
        self.acp_scroll_frame.grid(row=1, column=0, sticky="nsew")

    def _build_acp_details_view(self):
        self.acp_details_frame.grid_columnconfigure(0, weight=1)
        self.acp_details_frame.grid_rowconfigure(2, weight=1)
        
        header_frame = ctk.CTkFrame(self.acp_details_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        back_btn = ctk.CTkButton(header_frame, text="◀ Volver", font=("Arial", 12, "bold"), fg_color="#2c2e4a", hover_color="#3c3f61", width=80, command=self._show_acp_main)
        back_btn.pack(side="left")

        self.acp_detail_title = ctk.CTkLabel(header_frame, text="", font=("Arial", 20, "bold"), text_color="#ffffff")
        self.acp_detail_title.pack(side="left", padx=15)

        # Opportunely placed BCV Indicator in Details view
        self.acp_detail_bcv_lbl = ctk.CTkLabel(header_frame, textvariable=self.rate_status_var, font=("Arial", 14, "bold"), text_color="#0fbcf9")
        self.acp_detail_bcv_lbl.pack(side="right", padx=15)

        # Upper section: Quota summary and config
        top_content = ctk.CTkFrame(self.acp_details_frame, fg_color="transparent")
        top_content.grid(row=1, column=0, sticky="ew", pady=10)
        top_content.grid_columnconfigure(0, weight=1)
        top_content.grid_columnconfigure(1, weight=1)

        # Info Box
        info_box = ctk.CTkFrame(top_content, fg_color="#1b1c2b", corner_radius=10)
        info_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(info_box, text="Configuración de Costo (USD)", font=("Arial", 14, "bold"), text_color="#8c8da5").pack(anchor="w", padx=15, pady=(15, 5))
        
        cost_f = ctk.CTkFrame(info_box, fg_color="transparent")
        cost_f.pack(fill="x", padx=15, pady=(0, 15))
        self.acp_cost_entry = ctk.CTkEntry(cost_f, placeholder_text="0.00", font=("Arial", 14))
        self.acp_cost_entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        ctk.CTkButton(cost_f, text="Guardar", font=("Arial", 12, "bold"), fg_color="#3e44d6", width=80, command=self._save_acp_cost).pack(side="left")

        self.acp_summary_lbl = ctk.CTkLabel(info_box, text="Pagado: $0.00 | Restante: $0.00", font=("Arial", 18, "bold"), text_color="#ffffff")
        self.acp_summary_lbl.pack(anchor="w", padx=15, pady=(5, 15))

        # Payment Box
        pay_box = ctk.CTkFrame(top_content, fg_color="#1b1c2b", corner_radius=10)
        pay_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        ctk.CTkLabel(pay_box, text="Registrar Pago", font=("Arial", 14, "bold"), text_color="#8c8da5").pack(anchor="w", padx=15, pady=(15, 0))
        
        pay_inputs = ctk.CTkFrame(pay_box, fg_color="transparent")
        pay_inputs.pack(fill="x", padx=15, pady=(10, 5))
        
        self.acp_pay_type_var = ctk.StringVar(value="Bs.")
        type_menu = ctk.CTkOptionMenu(pay_inputs, values=["Bs.", "USD"], variable=self.acp_pay_type_var, width=80, fg_color="#2c2e4a", button_color="#3c3f61")
        type_menu.pack(side="left", padx=(0, 10))
        
        self.acp_pay_entry = ctk.CTkEntry(pay_inputs, placeholder_text="Monto", font=("Arial", 14))
        self.acp_pay_entry.pack(side="left", expand=True, fill="x")

        comps_f = ctk.CTkFrame(pay_box, fg_color="transparent")
        comps_f.pack(fill="x", padx=15, pady=5)
        
        self.acp_comprobante_path = None
        self.acp_comprobante_lbl = ctk.CTkLabel(comps_f, text="No hay comprobante", font=("Arial", 11), text_color="#5a5c7a")
        self.acp_comprobante_lbl.pack(side="left", expand=True, fill="x")
        
        ctk.CTkButton(comps_f, text="Adjuntar", font=("Arial", 11), fg_color="#2c2e4a", width=60, command=self._select_comprobante).pack(side="right")
        
        ctk.CTkButton(pay_box, text="Procesar Pago", font=("Arial", 12, "bold"), fg_color="#00e676", text_color="#000000", hover_color="#00c853", command=self._save_acp_pago).pack(fill="x", padx=15, pady=(5, 15))

        # Bottom section: History
        hist_box = ctk.CTkFrame(self.acp_details_frame, fg_color="#1b1c2b", corner_radius=10)
        hist_box.grid(row=2, column=0, sticky="nsew", pady=10)
        
        ctk.CTkLabel(hist_box, text="Historial de Pagos", font=("Arial", 14, "bold"), text_color="#8c8da5").pack(anchor="w", padx=15, pady=10)
        
        self.acp_pagos_scroll = ctk.CTkScrollableFrame(hist_box, fg_color="transparent")
        self.acp_pagos_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _add_acp_cuota(self):
        nombre = simpledialog.askstring("Nueva Cuota", "Ingresa el nombre descriptivo de la cuota:")
        if nombre and nombre.strip():
            insert_acp_cuota(nombre.strip())
            self._refresh_acp_list()

    def _refresh_acp_list(self):
        for widget in self.acp_scroll_frame.winfo_children():
            widget.destroy()

        cuotas = get_acp_cuotas()
        if not cuotas:
            ctk.CTkLabel(self.acp_scroll_frame, text="Aún no tienes cuotas guardadas.\nHaz clic en 'NUEVA CUOTA' para comenzar.", font=("Arial", 14), text_color="#5a5c7a").pack(pady=50)
            return

        row, col, max_cols = 0, 0, 3
        for cuota in cuotas:
            card = ctk.CTkFrame(self.acp_scroll_frame, fg_color="#2c2e4a", corner_radius=15, width=280, height=170)
            card.grid_propagate(False)
            card.grid(row=row, column=col, padx=15, pady=15)
            
            # Hover effect bindings
            def on_enter(e, c=card): c.configure(fg_color="#3c3f61")
            def on_leave(e, c=card): c.configure(fg_color="#2c2e4a")
            card.bind("<Enter>", on_enter)
            card.bind("<Leave>", on_leave)
            
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=15, pady=(15, 5))
            
            lbl_name = ctk.CTkLabel(header, text=cuota['nombre'].upper(), font=("Arial", 15, "bold"), text_color="#ffffff")
            lbl_name.pack(side="left", expand=True, anchor="w")
            
            btn_edit = ctk.CTkButton(header, text="✎", width=30, height=30, font=("Arial", 14), fg_color="#3e44d6", hover_color="#2b31b3", command=lambda c=cuota: self._edit_acp_cuota(c))
            btn_edit.pack(side="right", padx=(5, 0))
            
            btn_del = ctk.CTkButton(header, text="✖", width=30, height=30, font=("Arial", 14), fg_color="#d32f2f", hover_color="#b71c1c", command=lambda c=cuota: self._delete_acp_cuota(c))
            btn_del.pack(side="right")

            costo = cuota['costo_total']
            pagos = get_acp_pagos(cuota['id_cuota'])
            pagado = sum(p['cantidad_pagada'] for p in pagos)
            restante = max(0, costo - pagado)
            
            progress_val = pagado / costo if costo > 0 else 0
            if progress_val > 1: progress_val = 1
            progress_color = "#00e676" if restante <= 0 and costo > 0 else "#0fbcf9"
            
            prog = ctk.CTkProgressBar(card, height=8, progress_color=progress_color, fg_color="#1b1c2b")
            prog.set(progress_val)
            prog.pack(fill="x", padx=15, pady=(15, 15))
            
            stats = ctk.CTkFrame(card, fg_color="transparent")
            stats.pack(fill="x", padx=15)
            
            lbl_total = ctk.CTkLabel(stats, text=f"Total:\n${costo:.2f}", font=("Arial", 13), text_color="#8c8da5", justify="left")
            lbl_total.pack(side="left")
            
            status_text = "¡COMPLETADO!" if restante <= 0 and costo > 0 else f"Restante:\n${restante:.2f}"
            lbl_status = ctk.CTkLabel(stats, text=status_text, font=("Arial", 13, "bold"), text_color=progress_color, justify="right")
            lbl_status.pack(side="right")
            
            # Clickable areas to open details (excluding buttons)
            for w in [card, lbl_name, prog, stats, lbl_total, lbl_status]:
                w.bind("<Button-1>", lambda e, c=cuota: self._open_acp_details(c))

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _show_acp_main(self):
        self.acp_details_frame.grid_remove()
        self.acp_main_frame.grid()
        self._refresh_acp_list()

    def _open_acp_details(self, cuota):
        self.current_acp_cuota = cuota
        self.acp_main_frame.grid_remove()
        self.acp_details_frame.grid()
        self._refresh_acp_details()

    def _refresh_acp_details(self):
        c = self.current_acp_cuota
        self.acp_detail_title.configure(text=f"CUOTA: {c['nombre'].upper()}")
        
        self.acp_cost_entry.delete(0, 'end')
        if c['costo_total'] > 0:
            self.acp_cost_entry.insert(0, f"{c['costo_total']:.2f}")

        self.acp_pay_entry.delete(0, 'end')
        self.acp_comprobante_path = None
        self.acp_comprobante_lbl.configure(text="No hay comprobante")

        pagos = get_acp_pagos(c['id_cuota'])
        pagado = sum(p['cantidad_pagada'] for p in pagos)
        restante = max(0, c['costo_total'] - pagado)

        self.acp_summary_lbl.configure(text=f"Pagado: ${pagado:.2f}  |  Restante: ${restante:.2f}")

        for widget in self.acp_pagos_scroll.winfo_children():
            widget.destroy()

        if not pagos:
            ctk.CTkLabel(self.acp_pagos_scroll, text="No hay pagos registrados aún.", text_color="#5a5c7a").pack(pady=20)
        else:
            for p in pagos:
                f = ctk.CTkFrame(self.acp_pagos_scroll, fg_color="#2c2e4a", corner_radius=6)
                f.pack(fill="x", pady=4)
                
                info_text = f"📅 {p['fecha']}   |   Abono: ${p['cantidad_pagada']:.2f}"
                if p.get('cantidad_ves', 0) > 0:
                    info_text += f"   (Bs. {p['cantidad_ves']:.2f} a tasa {p['tasa_cambio']:.2f})"
                
                comp = "📂 Comprobante" if p['ruta_comprobante'] else ""
                
                ctk.CTkLabel(f, text=info_text, font=("Arial", 12), text_color="#ffffff").pack(side="left", padx=15, pady=10)
                
                actions_f = ctk.CTkFrame(f, fg_color="transparent")
                actions_f.pack(side="right", padx=15, pady=10)
                
                if comp:
                    ctk.CTkLabel(actions_f, text=comp, font=("Arial", 11, "bold"), text_color="#0fbcf9").pack(side="left", padx=(0, 15))
                    
                ctk.CTkButton(actions_f, text="✎ Editar", font=("Arial", 11), width=50, fg_color="#3e44d6", hover_color="#2b31b3", command=lambda pago=p: self._edit_acp_pago(pago)).pack(side="left", padx=(0, 5))
                ctk.CTkButton(actions_f, text="✖ Borrar", font=("Arial", 11), width=50, fg_color="#d32f2f", hover_color="#b71c1c", command=lambda pago=p: self._delete_acp_pago(pago)).pack(side="left")

    def _save_acp_cost(self):
        val = self.acp_cost_entry.get().replace(',', '.')
        try:
            costo = float(val)
            update_acp_costo(self.current_acp_cuota['id_cuota'], costo)
            self.current_acp_cuota['costo_total'] = costo
            self._refresh_acp_details()
        except ValueError:
            messagebox.showerror("Error", "Monto inválido.")

    def _select_comprobante(self):
        filepath = filedialog.askopenfilename(title="Seleccionar comprobante", filetypes=[("Imágenes", "*.png *.jpg *.jpeg")])
        if filepath:
            self.acp_comprobante_path = filepath
            self.acp_comprobante_lbl.configure(text=f"...{filepath[-20:]}")

    def _save_acp_pago(self):
        val = self.acp_pay_entry.get().replace(',', '.')
        try:
            monto_input = float(val)
            if monto_input <= 0: return
            
            tipo = self.acp_pay_type_var.get()
            tasa = 0.0
            cantidad_ves = 0.0
            cantidad_usd = 0.0
            
            if tipo == "Bs.":
                if not self.current_usd_rate:
                    messagebox.showerror("Error", "Aún no se ha cargado la tasa BCV. Espera un momento.")
                    return
                tasa = self.current_usd_rate
                cantidad_ves = monto_input
                cantidad_usd = monto_input / tasa
            else:
                cantidad_usd = monto_input
            
            dest_path = None
            if self.acp_comprobante_path:
                comp_dir = DATABASE_DIR / "comprobantes"
                comp_dir.mkdir(exist_ok=True)
                filename = f"cuota_{self.current_acp_cuota['id_cuota']}_{int(date.today().strftime('%Y%m%d%H%M'))}_{os.path.basename(self.acp_comprobante_path)}"
                dest_path = str(comp_dir / filename)
                shutil.copy2(self.acp_comprobante_path, dest_path)
            
            fecha = date.today().strftime("%Y-%m-%d")
            insert_acp_pago(
                self.current_acp_cuota['id_cuota'], 
                cantidad_usd, 
                fecha, 
                dest_path, 
                cantidad_ves=cantidad_ves, 
                tasa_cambio=tasa
            )
            self.acp_pay_entry.delete(0, 'end')
            self._refresh_acp_details()
        except ValueError:
            messagebox.showerror("Error", "Monto inválido para pago.")
        except Exception as e:
            messagebox.showerror("Error Interno", f"Ocurrió un error al procesar el pago:\n{e}")

    def _edit_acp_pago(self, pago):
        nuevo_monto = simpledialog.askfloat("Editar Pago", "Ingresa el nuevo monto en USD:", initialvalue=pago['cantidad_pagada'])
        if nuevo_monto is not None and nuevo_monto > 0:
            # Si el pago original tenía una tasa de cambio (fue en Bs.), calculamos los nuevos Bs.
            cantidad_ves = 0.0
            tasa = pago.get('tasa_cambio', 0.0)
            if tasa > 0:
                cantidad_ves = nuevo_monto * tasa
            update_acp_pago(pago['id_pago'], nuevo_monto, cantidad_ves, tasa)
            self._refresh_acp_details()

    def _delete_acp_pago(self, pago):
        if messagebox.askyesno("Borrar Pago", "¿Estás seguro de que deseas borrar este pago? Esta acción no se puede deshacer."):
            delete_acp_pago(pago['id_pago'])
            self._refresh_acp_details()

    def _edit_acp_cuota(self, cuota):
        nuevo_nombre = simpledialog.askstring("Editar Cuota", "Ingresa el nuevo nombre de la cuota:", initialvalue=cuota['nombre'])
        if nuevo_nombre and nuevo_nombre.strip():
            update_acp_cuota_name(cuota['id_cuota'], nuevo_nombre.strip())
            self._refresh_acp_list()

    def _delete_acp_cuota(self, cuota):
        if messagebox.askyesno("Borrar Cuota", f"¿Estás seguro de que deseas borrar la cuota '{cuota['nombre']}' y todos sus pagos? Esta acción no se puede deshacer."):
            delete_acp_cuota(cuota['id_cuota'])
            self._refresh_acp_list()
