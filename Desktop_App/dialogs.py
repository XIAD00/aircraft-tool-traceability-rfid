# Dialog windows used to add tools and confirm RFID transactions.

import customtkinter as ctk
from tkinter import messagebox

from tool_manager import ToolManager


class AddToolDialog(ctk.CTkToplevel):
    def __init__(self, parent, refresh_callback=None, tool=None):
        super().__init__(parent)

        self.manager = ToolManager()
        self.refresh_callback = refresh_callback
        self.tool = tool
        self.title("Modifier un outil" if self.tool else "Ajouter un outil")
        self.geometry("500x650")
        self.resizable(False, False)

        self.grab_set()

        ctk.CTkLabel(self, text="RFID UID").pack(pady=(15, 5))
        self.uid = ctk.CTkEntry(self, width=350)
        self.uid.pack()

        ctk.CTkLabel(self, text="Part Number").pack(pady=(15, 5))
        self.part = ctk.CTkEntry(self, width=350)
        self.part.pack()

        ctk.CTkLabel(self, text="Serial Number").pack(pady=(15, 5))
        self.serial = ctk.CTkEntry(self, width=350)
        self.serial.pack()

        ctk.CTkLabel(self, text="Description").pack(pady=(15, 5))
        self.description = ctk.CTkEntry(self, width=350)
        self.description.pack()

        ctk.CTkLabel(self, text="Last Check").pack(pady=(15, 5))
        self.last = ctk.CTkEntry(self, width=350)
        self.last.pack()

        ctk.CTkLabel(self, text="Next Check").pack(pady=(15, 5))
        self.next = ctk.CTkEntry(self, width=350)
        self.next.pack()

        ctk.CTkLabel(self, text="Status").pack(pady=(15, 5))

        self.status = ctk.CTkOptionMenu(
            self,
            values=[
                "AVAILABLE",
                "BORROWED",
                "MAINTENANCE",
                "CALIBRATION_DUE"
            ]
        )

        self.status.pack()

        if self.tool:
            self.uid.insert(0, self.tool["rfid_uid"])
            self.part.insert(0, self.tool["part_number"])
            self.serial.insert(0, self.tool["serial_number"])
            self.description.insert(0, self.tool["description_tool"])
            self.last.insert(0, self.tool["last_check"])
            self.next.insert(0, self.tool["next_check"])
            self.status.set(self.tool["status_"])
            self.uid.configure(state="disabled")

        ctk.CTkButton(
            self,
            text="Enregistrer",
            command=self.save
        ).pack(pady=25)

    def save(self):

        if self.tool:
           uid = self.tool["rfid_uid"]
        else:
           uid = self.uid.get()
        data = {
            "rfid_uid": uid,
            "part_number": self.part.get(),
            "serial_number": self.serial.get(),
            "description_tool": self.description.get(),
            "last_check": self.last.get(),
            "next_check": self.next.get(),
            "status_": self.status.get()
        }

        if self.tool:
            result = self.manager.update_tool(data)
        else:
            result = self.manager.add_tool(data)

        if result.get("success"):
            if self.refresh_callback:
                self.refresh_callback(data["rfid_uid"])
            self.destroy()
        else:
            print(result)


class TransactionDialog(ctk.CTkToplevel):
    """Ask the user to confirm a checkout or return."""

    def __init__(
        self,
        parent,
        scan,
        manager,
        success_callback,
        cancel_callback
    ):
        super().__init__(parent)

        self.scan = scan
        self.manager = manager
        self.success_callback = success_callback
        self.cancel_callback = cancel_callback
        self.action = scan.get("suggested_action")
        self.validated_employee = None
        self.submitting = False
        self.closed = False

        title = "Sortie d'outil" if self.action == "CHECK_OUT" else "Retour d'outil"
        self.title(title)
        self.geometry("560x700")
        self.minsize(520, 640)
        self.resizable(False, True)
        self.configure(fg_color="#1A1A1A")
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self._build_content(title)

        self.grab_set()
        self.after(50, self.matricule_entry.focus_set)

    def _build_content(self, title):
        container = ctk.CTkScrollableFrame(
            self,
            fg_color="#1A1A1A",
            corner_radius=0
        )
        container.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            container,
            text=title,
            font=("Segoe UI", 24, "bold")
        ).pack(anchor="w", pady=(0, 16))

        tool_frame = ctk.CTkFrame(container, fg_color="#242424")
        tool_frame.pack(fill="x", pady=(0, 18))

        details = (
            f"UID : {self.scan.get('rfid_uid', '')}\n"
            f"PN : {self.scan.get('part_number', '')}\n"
            f"SN : {self.scan.get('serial_number', '')}\n"
            f"Description : {self.scan.get('description_tool', '')}\n"
            f"Statut actuel : {self.scan.get('status_', '')}"
        )
        ctk.CTkLabel(
            tool_frame,
            text=details,
            justify="left",
            anchor="w",
            font=("Segoe UI", 14)
        ).pack(fill="x", padx=16, pady=16)

        ctk.CTkLabel(
            container,
            text="Matricule de l'employé",
            font=("Segoe UI", 15, "bold")
        ).pack(anchor="w", pady=(0, 6))

        self.matricule_entry = ctk.CTkEntry(
            container,
            placeholder_text="Saisir le matricule",
            height=38
        )
        self.matricule_entry.pack(fill="x", pady=(0, 10))
        self.matricule_entry.bind("<KeyRelease>", self._employee_input_changed)
        self.matricule_entry.bind("<Return>", lambda _event: self.verify_employee())

        self.verify_button = ctk.CTkButton(
            container,
            text="Vérifier le matricule",
            command=self.verify_employee
        )
        self.verify_button.pack(fill="x", pady=(0, 18))

        self.employee_frame = ctk.CTkFrame(container, fg_color="#242424")
        self.employee_frame.pack(fill="x", pady=(0, 20))

        self.employee_label = ctk.CTkLabel(
            self.employee_frame,
            text="Aucun employé vérifié.",
            justify="left",
            anchor="w",
            text_color="#B7B7B7",
            font=("Segoe UI", 14)
        )
        self.employee_label.pack(fill="x", padx=16, pady=16)

        buttons = ctk.CTkFrame(container, fg_color="transparent")
        buttons.pack(fill="x", pady=(8, 0))
        buttons.grid_columnconfigure((0, 1), weight=1)

        self.cancel_button = ctk.CTkButton(
            buttons,
            text="Annuler",
            command=self.cancel,
            fg_color="#4A4A4A",
            hover_color="#5A5A5A"
        )
        self.cancel_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        confirm_text = "Confirmer la sortie" if self.action == "CHECK_OUT" else "Confirmer le retour"
        self.confirm_button = ctk.CTkButton(
            buttons,
            text=confirm_text,
            command=self.confirm,
            state="disabled"
        )
        self.confirm_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _employee_input_changed(self, _event=None):
        if not self.validated_employee:
            return

        current = self.matricule_entry.get().strip().upper()
        validated = str(self.validated_employee.get("matricule", "")).upper()
        if current != validated:
            self.validated_employee = None
            self.confirm_button.configure(state="disabled")
            self.employee_label.configure(
                text="Le matricule a changé. Vérifiez-le à nouveau.",
                text_color="#D6A84B"
            )

    def verify_employee(self):
        if self.submitting:
            return

        matricule = self.matricule_entry.get().strip().upper()
        if not matricule:
            messagebox.showwarning(
                "Matricule requis",
                "Saisissez le matricule de l'employé.",
                parent=self
            )
            return

        self.verify_button.configure(state="disabled")
        result = self.manager.verify_employee(matricule)
        self.verify_button.configure(state="normal")

        employee = result.get("employee") if isinstance(result, dict) else None
        if (
            not isinstance(result, dict)
            or not result.get("success")
            or not isinstance(employee, dict)
        ):
            self.validated_employee = None
            self.confirm_button.configure(state="disabled")
            self.employee_label.configure(
                text="Employé non validé.",
                text_color="#D66A6A"
            )
            messagebox.showerror(
                "Vérification impossible",
                (
                    result.get("message", "Le matricule n'a pas pu être vérifié.")
                    if isinstance(result, dict)
                    else "Le matricule n'a pas pu être vérifié."
                ),
                parent=self
            )
            return

        self.validated_employee = employee
        self.matricule_entry.delete(0, "end")
        self.matricule_entry.insert(0, employee.get("matricule", matricule))

        name = " ".join(
            value for value in [
                str(employee.get("first_name", "")).strip(),
                str(employee.get("last_name", "")).strip()
            ]
            if value
        )
        info = (
            f"Matricule : {employee.get('matricule', '')}\n"
            f"Employé : {name or '-'}\n"
            f"Département : {employee.get('department') or '-'}\n"
            f"Service : {employee.get('service') or '-'}"
        )
        self.employee_label.configure(text=info, text_color="#79C99E")
        self.confirm_button.configure(state="normal")

    def confirm(self):
        if self.submitting or not self.validated_employee:
            return

        self.submitting = True
        self.confirm_button.configure(state="disabled")
        self.verify_button.configure(state="disabled")
        self.matricule_entry.configure(state="disabled")

        matricule = self.validated_employee.get("matricule", "")
        result = self.manager.confirm_transaction(
            self.scan.get("log_id"),
            self.scan.get("rfid_uid"),
            matricule,
            self.action
        )

        if result.get("success"):
            self._destroy_without_cancel()
            self.success_callback(self.scan, self.action, result)
            return

        self.submitting = False
        self.verify_button.configure(state="normal")
        self.matricule_entry.configure(state="normal")
        status_code = result.get("status_code")

        if status_code != 409:
            self.confirm_button.configure(state="normal")
        else:
            self.employee_label.configure(
                text="Ce scan ne peut plus être confirmé. Annulez puis rescanez l'outil.",
                text_color="#D66A6A"
            )

        messagebox.showerror(
            "Transaction refusée",
            result.get("message", "La transaction n'a pas pu être confirmée."),
            parent=self
        )

    def cancel(self):
        if self.closed:
            return

        self.closed = True
        callback = self.cancel_callback
        scan = self.scan
        self._release_and_destroy()
        callback(scan)

    def _destroy_without_cancel(self):
        if self.closed:
            return
        self.closed = True
        self._release_and_destroy()

    def _release_and_destroy(self):
        try:
            if self.grab_current() == self:
                self.grab_release()
        except Exception:
            pass
        self.destroy()
