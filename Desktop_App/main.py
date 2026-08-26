# Main window of the RFID tool tracking app.

import importlib
import importlib.util
import os
from datetime import datetime
import customtkinter as ctk
from tkinter import ttk, messagebox
from winotify import Notification


LAST_SCAN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_scan.txt")

PROFILE_LABELS = {
    "storekeeper": "Storekeeper",
    "supervisor": "Supervisor",
    "administrator": "Administrator",
}

# Demo PINs used only for this project.
PROFILE_PINS = {
    "storekeeper": "0000",
    "supervisor": "1111",
    "administrator": "3333",
}

# I keep all role permissions here so I can change them easily.
ROLE_PERMISSIONS = {
    role: {
        "view_history": True,
        "add_tool": True,
        "edit_tool": True,
        "delete_tool": True,
        "confirm_transaction": True,
    }
    for role in ("storekeeper", "supervisor")
}
ROLE_PERMISSIONS["administrator"] = {
    "view_history": True,
    "add_tool": False,
    "edit_tool": False,
    "delete_tool": False,
    "confirm_transaction": False,
}

READ_ONLY_PERMISSIONS = {
    "view_history": False,
    "add_tool": False,
    "edit_tool": False,
    "delete_tool": False,
    "confirm_transaction": False,
}

Image = None
if importlib.util.find_spec("PIL") is not None:
    try:
        Image = importlib.import_module("PIL").Image
    except Exception:  # pragma: no cover - Pillow is optional for the logo asset
        Image = None

from config import WINDOW_TITLE
from tool_manager import ToolManager
from dialogs import TransactionDialog

# App theme

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class ToolTrackerApp(ctk.CTk):
    """Main window for the RFID tool tracking app."""

    def __init__(self):
        super().__init__()

        self.manager = ToolManager()
        self.current_mode = "add"
        self.current_tool = None
        self.active_filter = None
        self.account_menu = None
        self.current_user_role = None
        self.pin_dialog = None
        self.pin_entry = None
        self.pin_error_label = None
        self.transaction_dialog = None
        self.pending_scan_id = None
        self.deferred_scan = None
        self.deferred_scan_id = None
        self.initial_scan_checked = False

        if os.path.exists(LAST_SCAN_FILE):
            with open(LAST_SCAN_FILE, "r") as f:
                self.last_scan_uid = f.read().strip()
        else:
            self.last_scan_uid = ""

        self.after(1000, self.watch_scans)
        self.role_menu_visible = False

        self.title(WINDOW_TITLE)
        self.geometry("1200x750")  # Use this size after leaving full screen.
        self.configure(fg_color="#1A1A1A")
        self.after(0, self._maximize_window_on_startup)

        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.search_var = ctk.StringVar()

        self.create_header()
        self.create_toolbar()
        self.create_dashboard()
        self.create_table()
        self.create_side_panel()
        self.apply_role_permissions()

        self.bind("<FocusOut>", self._on_app_focus_out, add="+")

        self.search_var.trace_add("write", lambda *args: self.load_tools())
        self.history_tool_uid = None
        self.load_tools()

    def _maximize_window_on_startup(self):
        def apply_maximize():
            try:
                if self.winfo_exists() and self.state() != "zoomed":
                    self.state("zoomed")
            except Exception:
                pass

        # Wait a little so Windows can open the app in full screen correctly.
        self.after(250, apply_maximize)

    # Main header

    def create_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=24, pady=(40, 20))

        header_left = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_left.pack(side="left")

        title_row = ctk.CTkFrame(header_left, fg_color="transparent")
        title_row.pack(anchor="w")

        self.logo = ctk.CTkLabel(
            title_row,
            text="",
            fg_color="transparent"
        )
        self.logo.pack(side="left", padx=(0, 24))
        self._load_logo_image()

        titles_frame = ctk.CTkFrame(title_row, fg_color="transparent")
        titles_frame.pack(side="left")

        title = ctk.CTkLabel(
            titles_frame,
            text="Aircraft Tool Tracking System",
            font=("Segoe UI", 32, "bold"),
            text_color="#F5F5F5"
        )
        title.pack(anchor="w")

        ctk.CTkLabel(
            titles_frame,
            text="Royal Air Maroc",
            font=("Segoe UI", 18),
            text_color="#B7B7B7"
        ).pack(anchor="w", pady=(4, 0))

        header_right = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_right.pack(side="right")

        self.status_button = ctk.CTkButton(
            header_right,
            text="Not connected ▼",
            width=230,
            height=46,
            corner_radius=12,
            fg_color="#242424",
            hover_color="#C8102E",
            border_color="#3B3B3B",
            border_width=1,
            font=("Segoe UI", 16, "bold"),
            command=self.toggle_account_menu
        )
        self.status_button.pack(anchor="e", pady=(2, 6))

        self.user_label = ctk.CTkLabel(
            header_right,
            text="Read-only mode",
            font=("Segoe UI", 16, "bold"),
            text_color="#F5F5F5"
        )
        self.user_label.pack(anchor="e")

        self.create_account_menu()

    # Toolbar

    def create_toolbar(self):
        toolbar_frame = ctk.CTkFrame(self, fg_color="transparent")
        toolbar_frame.pack(fill="x", padx=24, pady=(0, 16))

        # Put the buttons on the right so they always stay visible.
        self.buttons_frame = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
        self.buttons_frame.pack(side="right")

        self.search_entry = ctk.CTkEntry(
            toolbar_frame,
            height=46,
            textvariable=self.search_var,
            fg_color="#242424",
            border_color="#3B3B3B",
            text_color="#888888",
            font=("Segoe UI", 16)
        )
        # The search box takes the free space on the left.
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.search_var.set("🔍 Search tool...")
        self.search_focused = False
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)

        self.history_button = ctk.CTkButton(
            self.buttons_frame, text="📜 History", command=self.show_history_action,
            height=46, corner_radius=10, fg_color="#2F2F2F", hover_color="#3A3A3A",
            border_color="#3B3B3B", border_width=1, font=("Segoe UI", 14, "bold")
        )
        self.history_button.grid(row=0, column=0, padx=(0, 8), pady=0)

        self.refresh_button = ctk.CTkButton(
            self.buttons_frame, text="🔄 Refresh", command=self.refresh_all,
            height=46, corner_radius=10, fg_color="#3A3A3A", hover_color="#474747",
            border_color="#3B3B3B", border_width=1, font=("Segoe UI", 14, "bold")
        )
        self.refresh_button.grid(row=0, column=1, padx=(0, 8), pady=0)

        self.add_button = ctk.CTkButton(
            self.buttons_frame, text="➕ Add", command=lambda: self.show_side_panel("add"),
            height=46, corner_radius=10, fg_color="#C8102E", hover_color="#E11F3E",
            font=("Segoe UI", 14, "bold")
        )
        self.add_button.grid(row=0, column=2, padx=(0, 8), pady=0)

        self.edit_button = ctk.CTkButton(
            self.buttons_frame, text="✏ Edit", command=self.edit_tool,
            height=46, corner_radius=10, fg_color="#2F2F2F", hover_color="#3A3A3A",
            border_color="#3B3B3B", border_width=1, font=("Segoe UI", 14, "bold")
        )
        self.edit_button.grid(row=0, column=3, padx=(0, 8), pady=0)

        self.delete_button = ctk.CTkButton(
            self.buttons_frame, text="🗑 Delete", command=self.delete_tool,
            height=46, corner_radius=10, fg_color="#4B1A1A", hover_color="#5E2020",
            border_color="#3B3B3B", border_width=1, font=("Segoe UI", 14, "bold")
        )
        self.delete_button.grid(row=0, column=4, padx=0, pady=0)

    def _on_search_focus_in(self, event):
        self.search_focused = True
        current_val = self.search_var.get()
        # Remove the search text when the user clicks inside.
        if current_val in ["🔍 Search tool...", "🔍"]:
            self.search_var.set("")
            self.search_entry.configure(text_color="#F5F5F5")
        self._apply_toolbar_layout()

    def _on_search_focus_out(self, event):
        self.search_focused = False
        if not self.search_var.get().strip():
            self.search_entry.configure(text_color="#888888")
            self.search_var.set("🔍 Search tool...")  # Make it shorter when there is less space.
        self._apply_toolbar_layout()

    # Dashboard cards

    def create_dashboard(self):
        dashboard_frame = ctk.CTkFrame(self, fg_color="transparent")
        dashboard_frame.pack(fill="x", padx=24, pady=(0, 12))

        self.dashboard_cards = []

        for index in range(5):
            dashboard_frame.grid_columnconfigure(index, weight=1)

        for title, value, accent in [
            ("All", "0", "#1A5276"),
            ("Available", "0", "#2E8B57"),
            ("Borrowed", "0", "#E53935"),
            ("Maintenance", "0", "#696969"),
            ("Calibration Due", "0", "#FF8C00")
        ]:
            card = ctk.CTkFrame(
                dashboard_frame,
                height=100,
                corner_radius=18,
                fg_color=accent,
                border_width=2,
                border_color=accent
            )
            card.grid(row=0, column=len(self.dashboard_cards), sticky="nsew", padx=(0, 10))
            card.pack_propagate(False)

            card.bind("<Enter>", lambda event, widget=card: self._hover_dashboard_card(widget, True))
            card.bind("<Leave>", lambda event, widget=card: self._hover_dashboard_card(widget, False))
            card.bind("<Button-1>", lambda event, title=title: self.apply_dashboard_filter(title))

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(side="left", fill="both", expand=True, padx=(10, 12), pady=10)

            inner.bind("<Button-1>", lambda event, title=title: self.apply_dashboard_filter(title))

            title_label = ctk.CTkLabel(
                inner,
                text=title,
                font=("Segoe UI", 16, "bold"),
                text_color="#FFFFFF"
            )
            title_label.pack(anchor="w", pady=(4, 0))
            title_label.bind("<Button-1>", lambda event, title=title: self.apply_dashboard_filter(title))

            value_label = ctk.CTkLabel(
                inner,
                text=value,
                font=("Segoe UI", 26, "bold"),
                text_color="#FFFFFF"
            )
            value_label.pack(anchor="w")
            value_label.bind("<Button-1>", lambda event, title=title: self.apply_dashboard_filter(title))

            self.dashboard_cards.append({
                "title": title,
                "card": card,
                "title_label": title_label,
                "value_label": value_label,
                "accent": accent
            })

        self.update_dashboard_selection()

    # Main content

    def create_table(self):
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=0, minsize=0)
        self.content_frame.grid_rowconfigure(0, weight=1)

        self.table_host = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.table_host.grid(row=0, column=0, sticky="nsew", padx=(0, 0))
        self.table_host.grid_rowconfigure(1, weight=1)
        self.table_host.grid_columnconfigure(0, weight=1)

        self.table_frame = ctk.CTkFrame(
            self.table_host,
            corner_radius=0,
            fg_color="#242424",
            border_width=0,
        )
        self.table_frame.grid(row=1, column=0, sticky="nsew")
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(1, weight=0)
        self.table_frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure(
            "Treeview",
            background="#242424",
            foreground="#F5F5F5",
            fieldbackground="#242424",
            rowheight=60,
            bordercolor="#3B3B3B",
            font=("Segoe UI", 16)
        )
        style.map(
            "Treeview",
            background=[("selected", "#C8102E")],
            foreground=[("selected", "#FFFFFF")]
        )
        style.configure(
            "Treeview.Heading",
            background="#1F1F1F",
            foreground="#F5F5F5",
            relief="flat",
            font=("Segoe UI", 18, "bold"),
            padding=(10, 15)
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#2A2A2A")]
        )

        self.tree = ttk.Treeview(
            self.table_frame,
            columns=(
                "UID",
                "Part Number",
                "Serial Number",
                "Description",
                "Last Check",
                "Next Check",
                "Status"
            ),
            show="headings",
            height=16
        )
        self.tree.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.tree.tag_configure("even", background="#2A2A2A")
        self.tree.tag_configure("odd", background="#242424")

        self._tree_column_widths = {
            "large": {
                "UID": 140,
                "Part Number": 170,
                "Serial Number": 170,
                "Description": 420,
                "Last Check": 170,
                "Next Check": 170,
                "Status": 150,
            },
            "medium": {
                "UID": 120,
                "Part Number": 140,
                "Serial Number": 140,
                "Description": 320,
                "Last Check": 140,
                "Next Check": 140,
                "Status": 120,
            },
            "small": {
                "UID": 100,
                "Part Number": 100,
                "Serial Number": 100,
                "Description": 220,
                "Last Check": 100,
                "Next Check": 100,
                "Status": 90,
            },
        }
        self._tree_header_labels = {
            "large": {
                "UID": "RFID UID",
                "Part Number": "Part Number",
                "Serial Number": "Serial Number",
                "Description": "Description",
                "Last Check": "Last Check",
                "Next Check": "Next Check",
                "Status": "Status",
            },
            "medium": {
                "UID": "UID",
                "Part Number": "PN",
                "Serial Number": "SN",
                "Description": "Description",
                "Last Check": "Last Check",
                "Next Check": "Next Check",
                "Status": "Status",
            },
            "small": {
                "UID": "UID",
                "Part Number": "PN",
                "Serial Number": "SN",
                "Description": "DESC",
                "Last Check": "LAST",
                "Next Check": "NEXT",
                "Status": "STAT",
            },
        }

        self.tree.bind("<MouseWheel>", self._on_mousewheel)
        self.tree.bind("<Button-4>", self._on_mousewheel)
        self.tree.bind("<Button-5>", self._on_mousewheel)
        self.bind("<Configure>", self._on_window_resize)

        self._apply_tree_layout()

        self.tree_scroll_y = ctk.CTkScrollbar(
            self.table_frame,
            orientation="vertical",
            command=self.tree.yview,
            fg_color="#1F1F1F",
            button_color="#3B3B3B",
            button_hover_color="#4A4A4A"
        )
        self.tree_scroll_y.grid(row=0, column=1, sticky="ns")

        self.tree_scroll_x = ctk.CTkScrollbar(
            self.table_frame,
            orientation="horizontal",
            command=self.tree.xview,
            fg_color="#1F1F1F",
            button_color="#3B3B3B",
            button_hover_color="#4A4A4A"
        )
        self.tree_scroll_x.grid(row=1, column=0, sticky="ew")

        self.tree.configure(yscrollcommand=self.tree_scroll_y.set)
        self.tree.configure(xscrollcommand=self.tree_scroll_x.set)

    def _get_side_panel_width(self):
        if not hasattr(self, "side_panel_frame") or not self.side_panel_frame.winfo_exists():
            return 0

        try:
            available = max(0, self.winfo_width() - 40)
            min_width = 300
            max_width = 460
            if available <= 0:
                return 0
            return max(min_width, min(max_width, int(available * 0.28)))
        except Exception:
            return 0

    def _apply_main_layout(self):
        if not hasattr(self, "side_panel_frame"):
            return

        if not self.side_panel_frame.winfo_exists():
            return

        try:
            self.update_idletasks()

            panel_visible = self.side_panel_frame.winfo_ismapped()
            panel_width = self._get_side_panel_width()
            table_min_width = 760
            available_width = max(0, self.winfo_width() - 40)

            if panel_visible and available_width >= table_min_width + panel_width:
                self.side_panel_frame.grid(row=0, column=1, sticky="nsew")
                self.side_panel_frame.configure(width=panel_width)
                self.content_frame.grid_columnconfigure(0, weight=1)
                self.content_frame.grid_columnconfigure(1, weight=0, minsize=panel_width)
                self.table_host.grid_configure(padx=(0, 12))
            else:
                self.side_panel_frame.grid_remove()
                self.content_frame.grid_columnconfigure(0, weight=1)
                self.content_frame.grid_columnconfigure(1, weight=0, minsize=0)
                self.table_host.grid_configure(padx=(0, 0))

            self.content_frame.grid_columnconfigure(0, weight=1)
            self.content_frame.grid_columnconfigure(1, weight=0)
            self.table_host.grid_columnconfigure(0, weight=1)
            self.table_frame.grid_columnconfigure(0, weight=1)

            if hasattr(self, "tree") and self.tree.winfo_exists():
                self.update_idletasks()
                if hasattr(self, "_apply_tree_layout"):
                    self._apply_tree_layout()

        except Exception as e:
            print(f"Side panel responsive warning: {e}")

    def _apply_tree_layout(self):
        if not hasattr(self, "tree"):
            return

        columns = ["UID", "Part Number", "Serial Number", "Description", "Last Check", "Next Check", "Status"]
        natural_widths = {
            "UID": 140,
            "Part Number": 170,
            "Serial Number": 170,
            "Description": 420,
            "Last Check": 170,
            "Next Check": 170,
            "Status": 150,
        }
        minimum_widths = {
            "UID": 90,
            "Part Number": 110,
            "Serial Number": 110,
            "Description": 180,
            "Last Check": 110,
            "Next Check": 110,
            "Status": 80,
        }

        available_width = max(600, self.table_frame.winfo_width() - 30)
        total_natural = sum(natural_widths.values())
        total_minimum = sum(minimum_widths.values())

        if available_width <= total_minimum:
            widths = minimum_widths.copy()
        elif available_width >= total_natural:
            widths = natural_widths.copy()
            extra = available_width - total_natural
            if extra > 0:
                total_base = sum(natural_widths.values())
                if total_base > 0:
                    for column in columns:
                        extra_share = int((natural_widths[column] / total_base) * extra)
                        widths[column] += extra_share
        else:
            widths = {}
            scale = (available_width - total_minimum) / max(1, total_natural - total_minimum)
            for column in columns:
                natural = natural_widths[column]
                minimum = minimum_widths[column]
                widths[column] = int(minimum + (natural - minimum) * scale)

        header_abbrev = {
            "UID": "UID",
            "Part Number": "PN",
            "Serial Number": "SN",
            "Description": "DESC",
            "Last Check": "LAST",
            "Next Check": "NEXT",
            "Status": "STAT",
        }
        header_medium = {
            "UID": "UID",
            "Part Number": "Part Number",
            "Serial Number": "Serial Number",
            "Description": "Description",
            "Last Check": "Last",
            "Next Check": "Next",
            "Status": "Status",
        }
        full_names = {
            "UID": "RFID UID",
            "Part Number": "Part Number",
            "Serial Number": "Serial Number",
            "Description": "Description",
            "Last Check": "Last Check",
            "Next Check": "Next Check",
            "Status": "Status",
        }

        for column in columns:
            width = max(minimum_widths.get(column, 80), widths.get(column, minimum_widths.get(column, 80)))
            if width >= 200:
                label = full_names.get(column, column)
            elif width >= 130:
                label = header_medium.get(column, column)
            else:
                label = header_abbrev.get(column, column)

            self.tree.heading(column, text=label)
            self.tree.column(
                column,
                width=width,
                minwidth=minimum_widths.get(column, 80),
                anchor="center" if column != "Description" else "w",
                stretch=False
            )

        self.tree.column("Description", anchor="w")

    def _on_window_resize(self, event=None):
        """Update the layout after resizing the window."""
        if event is not None and getattr(event, "widget", None) is not self:
            return

        if self.role_menu_visible and self.account_menu is not None:
            self._position_account_menu()

        if hasattr(self, "_resize_job"):
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass

        self._resize_job = self.after(60, self._safe_apply_responsive_layout)

    def _safe_apply_responsive_layout(self):
        """Do nothing if the app is already closed."""
        try:
            if not self.winfo_exists():
                return

            self._apply_responsive_layout()

        except Exception as e:
            print(f"Responsive layout warning: {e}")

        finally:
            self._resize_job = None

    def _apply_responsive_layout(self):
        """Update all parts when the window size changes."""

        try:
            if not self.winfo_exists():
                return

            if hasattr(self, "content_frame") and self.content_frame.winfo_exists():
                self._apply_main_layout()

            if hasattr(self, "tree") and self.tree.winfo_exists():
                self._apply_tree_layout()

            if hasattr(self, "dashboard_cards"):
                self._apply_dashboard_layout()

            if hasattr(self, "buttons_frame") and self.buttons_frame.winfo_exists():
                self._apply_toolbar_layout()

        except Exception as e:
            print(f"Responsive layout warning: {e}")

    def _apply_toolbar_layout(self):
        """Resize the search box and buttons to fit the window."""

        if not hasattr(self, "buttons_frame"):
            return

        if not self.buttons_frame.winfo_exists():
            return

        if not hasattr(self, "search_entry") or not self.search_entry.winfo_exists():
            return

        try:
            self.update_idletasks()

            toolbar_width = max(300, self.winfo_width() - 48)

            buttons = [
                (self.history_button, "📜 History", "📜"),
                (self.refresh_button, "🔄 Refresh", "🔄"),
                (self.add_button, "➕ Add", "➕"),
                (self.edit_button, "✏ Edit", "✏"),
                (self.delete_button, "🗑 Delete", "🗑"),
            ]

            full_button_width = 104
            compact_button_width = 48
            gap = 8

            full_buttons_width = (
                len(buttons) * full_button_width
                + (len(buttons) - 1) * gap
            )

            search_min = 180

            if toolbar_width >= full_buttons_width + search_min + 20:
                self.search_entry.configure(width=max(260, toolbar_width - full_buttons_width - 20))
                self.search_entry.pack_configure(
                    side="left",
                    fill="x",
                    expand=True,
                    padx=(0, 12)
                )

                for button, full_text, compact_text in buttons:
                    button.configure(
                        text=full_text,
                        width=full_button_width
                    )

                self._place_toolbar_buttons_one_row()

            elif toolbar_width >= (
                len(buttons) * compact_button_width
                + (len(buttons) - 1) * gap
                + search_min
                + 20
            ):
                self.search_entry.configure(
                    width=max(
                        search_min,
                        toolbar_width
                        - (
                            len(buttons) * compact_button_width
                            + (len(buttons) - 1) * gap
                        )
                        - 20
                    )
                )

                self.search_entry.pack_configure(
                    side="left",
                    fill="x",
                    expand=True,
                    padx=(0, 12)
                )

                for button, full_text, compact_text in buttons:
                    button.configure(
                        text=compact_text,
                        width=compact_button_width
                    )

                self._place_toolbar_buttons_one_row()

            else:
                self.search_entry.configure(width=180)
                self.search_entry.pack_configure(
                    side="left",
                    fill="x",
                    expand=True,
                    padx=(0, 12)
                )

                for button, full_text, compact_text in buttons:
                    button.configure(
                        text=compact_text,
                        width=compact_button_width
                    )

                self._place_toolbar_buttons_wrapped()

        except Exception as e:
            print(f"Toolbar responsive warning: {e}")

    def _place_toolbar_buttons_one_row(self):
        """Keep all toolbar buttons in one row."""

        buttons = [
            self.history_button,
            self.refresh_button,
            self.add_button,
            self.edit_button,
            self.delete_button,
        ]

        for index, button in enumerate(buttons):
            button.grid(
                row=0,
                column=index,
                padx=(0, 8 if index < len(buttons) - 1 else 0),
                pady=0,
                sticky="ew"
            )

        for index in range(len(buttons)):
            self.buttons_frame.grid_columnconfigure(
                index,
                weight=0
            )

    def _place_toolbar_buttons_wrapped(self):
        """Move toolbar buttons to a second row when needed."""

        buttons = [
            self.history_button,
            self.refresh_button,
            self.add_button,
            self.edit_button,
            self.delete_button,
        ]

        buttons_per_row = 3

        for index, button in enumerate(buttons):
            row = index // buttons_per_row
            column = index % buttons_per_row

            button.grid(
                row=row,
                column=column,
                padx=(0, 8),
                pady=(0, 6),
                sticky="ew"
            )

        for column in range(buttons_per_row):
            self.buttons_frame.grid_columnconfigure(
                column,
                weight=0
            )

    def _apply_dashboard_layout(self):
        """Make dashboard labels shorter but keep the same values."""

        if not hasattr(self, "dashboard_cards"):
            return

        try:
            self.update_idletasks()

            available_width = self.winfo_width()

            full_map = {
                "All": "ALL",
                "Available": "AVAILABLE",
                "Borrowed": "BORROWED",
                "Maintenance": "MAINTENANCE",
                "Calibration Due": "CALIBRATION DUE",
            }

            medium_map = {
                "All": "ALL",
                "Available": "AVAIL",
                "Borrowed": "BORROWED",
                "Maintenance": "MAINT",
                "Calibration Due": "CAL DUE",
            }

            compact_map = {
                "All": "ALL",
                "Available": "AVAIL",
                "Borrowed": "BR",
                "Maintenance": "MN",
                "Calibration Due": "CD",
            }

            if available_width >= 1500:
                label_map = full_map
            elif available_width >= 1050:
                label_map = medium_map
            else:
                label_map = compact_map

            for card_info in self.dashboard_cards:
                original_title = card_info.get("title")
                label_widget = card_info.get("title_label")

                if (
                    label_widget is not None
                    and label_widget.winfo_exists()
                ):
                    label_widget.configure(
                        text=label_map.get(
                            original_title,
                            original_title
                        )
                    )

        except Exception as e:
            print(f"Dashboard responsive warning: {e}")

    def _on_mousewheel(self, event):
        import time

        if not hasattr(self, "_last_scroll_time"):
            self._last_scroll_time = time.perf_counter()
            self._scroll_mult = 1.0

        now = time.perf_counter()
        dt = now - self._last_scroll_time
        self._last_scroll_time = now

        # Scroll farther when the mouse wheel moves fast.
        if dt < 0.10:
            self._scroll_mult = min(self._scroll_mult + 5.0, 60.0)
        elif dt > 0.25:
            self._scroll_mult = 9.0

        delta = getattr(event, "delta", 0)
        if delta == 0:
            return

        # Calculate one scroll value for every wheel speed.
        base_speed = 40.0
        raw_steps = (delta / 120.0) * base_speed * self._scroll_mult
        amount = int(raw_steps)

        if abs(amount) == 0:
            amount = 1 if delta > 0 else -1

        # Reverse it because Tkinter scrolls in the other direction.
        self.tree.yview_scroll(-amount, "units")

    # Side panel

    def create_side_panel(self):
        self.side_panel_frame = ctk.CTkFrame(
            self.content_frame,
            width=420,
            corner_radius=20,
            fg_color="#262626",
            border_width=2,
            border_color="#444444"
        )
        self.side_panel_frame.grid(row=0, column=1, sticky="nsew")
        self.side_panel_frame.grid_remove()
        self.side_panel_frame.grid_columnconfigure(0, weight=1)
        self.side_panel_frame.grid_rowconfigure(1, weight=1)

        header_panel = ctk.CTkFrame(self.side_panel_frame, fg_color="transparent")
        header_panel.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 14))
        header_panel.grid_columnconfigure(0, weight=1)

        self.panel_title = ctk.CTkLabel(
            header_panel,
            text="Tool Information",
            font=("Segoe UI", 20, "bold"),
            text_color="#F5F5F5"
        )
        self.panel_title.grid(row=0, column=0, sticky="w")

        self.close_button = ctk.CTkButton(
            header_panel,
            text="✕",
            width=36,
            height=32,
            corner_radius=10,
            fg_color="transparent",
            text_color="#F5F5F5",
            hover_color="#3A3A3A",
            command=self.hide_side_panel
        )
        self.close_button.grid(row=0, column=1, padx=(10, 0))

        self.form_container = ctk.CTkFrame(self.side_panel_frame, fg_color="transparent")
        self.form_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 6))
        self.form_container.grid_rowconfigure(0, weight=1)
        self.form_container.grid_columnconfigure(0, weight=1)

        self.form_scroll = ctk.CTkScrollableFrame(self.form_container, fg_color="transparent")
        self.form_scroll.grid(row=0, column=0, sticky="nsew")
        self.form_scroll.grid_remove()

        self.history_scroll = ctk.CTkScrollableFrame(self.form_container, fg_color="transparent")
        self.history_scroll.grid(row=0, column=0, sticky="nsew")
        self.history_scroll.grid_remove()

        self.field_entries = {}
        self.description_box = None

        self.create_form_field("RFID UID *", "rfid_uid")
        self.create_form_field("Part Number", "part_number")
        self.create_form_field("Serial Number", "serial_number")
        self.create_description_field("Description")
        self.create_form_field("Last Check", "last_check", placeholder="YYYY-MM-DD")
        self.create_form_field("Next Check", "next_check", placeholder="YYYY-MM-DD")

        status_label = ctk.CTkLabel(
            self.form_scroll,
            text="Status",
            anchor="w",
            text_color="#F5F5F5",
            font=("Segoe UI", 15, "bold")
        )
        status_label.pack(anchor="w", pady=(12, 5))

        self.status_menu = ctk.CTkComboBox(
            self.form_scroll,
            values=["AVAILABLE", "BORROWED", "MAINTENANCE", "CALIBRATION_DUE"],
            fg_color="#242424",
            border_color="#3B3B3B",
            button_color="#3B3B3B",
            button_hover_color="#4A4A4A",
            dropdown_fg_color="#242424",
            dropdown_text_color="#F5F5F5",
            font=("Segoe UI", 13)
        )
        self.status_menu.pack(fill="x", pady=(0, 16))
        self.status_menu.set("AVAILABLE")

        self.buttons_frame = ctk.CTkFrame(self.side_panel_frame, fg_color="transparent")
        self.buttons_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 18))
        self.buttons_frame.grid_remove()

        button_row = ctk.CTkFrame(self.buttons_frame, fg_color="transparent")
        button_row.pack(fill="x")

        self.cancel_button = ctk.CTkButton(
            button_row,
            text="Cancel",
            width=120,
            height=42,
            corner_radius=12,
            fg_color="#555555",
            hover_color="#666666",
            font=("Segoe UI", 13, "bold"),
            command=self.cancel_edit
        )
        self.cancel_button.pack(side="left", expand=True, padx=(0, 6))

        self.save_button = ctk.CTkButton(
            button_row,
            text="Save",
            width=120,
            height=42,
            corner_radius=12,
            fg_color="#C8102E",
            hover_color="#E11F3E",
            font=("Segoe UI", 13, "bold"),
            command=self.save_tool
        )
        self.save_button.pack(side="left", expand=True, padx=(6, 0))

        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=0, minsize=0)
        self.table_host.grid_configure(padx=(0, 0))

    def create_form_field(self, label_text, key, placeholder=None):
        label = ctk.CTkLabel(
            self.form_scroll,
            text=label_text,
            anchor="w",
            text_color="#F5F5F5",
            font=("Segoe UI", 14, "bold")
        )
        label.pack(anchor="w", pady=(12, 5))

        entry = ctk.CTkEntry(
            self.form_scroll,
            fg_color="#242424",
            border_color="#3B3B3B",
            text_color="#F5F5F5",
            placeholder_text=placeholder or "",
            font=("Segoe UI", 14)
        )
        entry.pack(fill="x", pady=(0, 16))
        self.field_entries[key] = entry

    def create_description_field(self, label_text):
        label = ctk.CTkLabel(
            self.form_scroll,
            text=label_text,
            anchor="w",
            text_color="#F5F5F5",
            font=("Segoe UI", 15, "bold")
        )
        label.pack(anchor="w", pady=(12, 5))

        textbox = ctk.CTkTextbox(
            self.form_scroll,
            height=110,
            fg_color="#242424",
            border_color="#3B3B3B",
            text_color="#F5F5F5",
            font=("Segoe UI", 14)
        )
        textbox.pack(fill="x", pady=(0, 16))
        self.description_box = textbox

    # Side panel actions

    def show_side_panel(self, mode="add", tool=None):
        permission_for_mode = {
            "add": "add_tool",
            "edit": "edit_tool",
            "history": "view_history",
        }.get(mode)
        if permission_for_mode and not self.require_permission(permission_for_mode):
            return

        self.current_mode = mode
        self.current_tool = tool
        self.history_tool_uid = tool.get("rfid_uid") if isinstance(tool, dict) and tool.get("rfid_uid") else None

        if mode == "history":
            self.panel_title.configure(text="Tool History")
            self.form_scroll.grid_remove()
            self.buttons_frame.grid_remove()
            self.history_scroll.grid(row=0, column=0, sticky="nsew")
            if tool:
                self.populate_history(tool)
        else:
            self.panel_title.configure(text="Tool Information")
            self.history_scroll.grid_remove()
            self.form_scroll.grid(row=0, column=0, sticky="nsew")
            self.buttons_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 18))

            if mode == "edit" and tool:
                self.populate_form(tool)
            else:
                self.clear_form()

        self.side_panel_frame.grid(row=0, column=1, sticky="nsew")
        self.side_panel_frame.configure(width=max(300, min(460, int(max(0, self.winfo_width() - 40) * 0.28))))
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=0, minsize=max(300, min(460, int(max(0, self.winfo_width() - 40) * 0.28))))
        self.table_host.grid_configure(padx=(0, 12))
        self.update_idletasks()
        self._apply_responsive_layout()

    def hide_side_panel(self):
        self.current_tool = None
        self.history_tool_uid = None
        self.clear_form()
        self.form_scroll.grid_remove()
        self.history_scroll.grid_remove()
        self.buttons_frame.grid_remove()
        self.side_panel_frame.grid_remove()
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=0, minsize=0)
        self.table_host.grid_configure(padx=(0, 0))
        self.update_idletasks()
        self._apply_responsive_layout()

    def populate_form(self, tool):
        self.clear_form()

        self.field_entries["rfid_uid"].insert(0, str(tool.get("rfid_uid", "")))
        self.field_entries["part_number"].insert(0, str(tool.get("part_number", "")))
        self.field_entries["serial_number"].insert(0, str(tool.get("serial_number", "")))
        self.field_entries["last_check"].insert(0, str(tool.get("last_check", "")))
        self.field_entries["next_check"].insert(0, str(tool.get("next_check", "")))
        self.description_box.delete("1.0", "end")
        self.description_box.insert("1.0", str(tool.get("description_tool", "")))
        self.status_menu.set(tool.get("status_", "AVAILABLE"))

        if self.current_mode == "edit":
            self.field_entries["rfid_uid"].configure(state="disabled")
        else:
            self.field_entries["rfid_uid"].configure(state="normal")

    def clear_form(self):
        for entry in self.field_entries.values():
            entry.delete(0, "end")
            entry.configure(state="normal")
        if self.description_box is not None:
            self.description_box.delete("1.0", "end")
        self.status_menu.set("AVAILABLE")

    def populate_history(self, tool):
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        if isinstance(tool, dict):
            uid = tool.get("rfid_uid")
        else:
            uid = tool

        if not uid:
            return

        if isinstance(tool, dict):
            tool_record = tool
        else:
            tool_record = {"rfid_uid": uid}

        self.history_tool_uid = uid
        self.current_tool = tool_record
        history_data = self.manager.get_tool_history(uid)

        if not history_data or not isinstance(history_data, list):
            lbl = ctk.CTkLabel(
                self.history_scroll,
                text="No history found for this tool.",
                font=("Segoe UI", 14, "italic"),
                text_color="#B7B7B7"
            )
            lbl.pack(pady=30)
            return

        for entry in history_data:
            frame = ctk.CTkFrame(
                self.history_scroll,
                fg_color="#242424",
                corner_radius=8,
                border_color="#3B3B3B",
                border_width=1
            )
            frame.pack(fill="x", pady=6, padx=4)

            # Action label and color
            action_raw = str(entry.get("actions", "UNKNOWN"))
            if action_raw == "CHECK_OUT":
                action_text = "↓ Borrowed"
                action_color = "#E53935"  # Red
            elif action_raw == "CHECK_IN":
                action_text = "↑ Returned"
                action_color = "#2E8B57"  # Green
            else:
                action_text = action_raw
                action_color = "#F5F5F5"

            act_lbl = ctk.CTkLabel(frame, text=action_text, font=("Segoe UI", 15, "bold"), text_color=action_color)
            act_lbl.pack(anchor="w", padx=12, pady=(10, 2))

            # Date format
            raw_date = str(entry.get("scan_time", ""))
            formatted_date = raw_date
            try:
                dt_obj = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
                formatted_date = dt_obj.strftime("%d %b %Y\n%H:%M:%S")
            except:
                pass

            dt_lbl = ctk.CTkLabel(frame, text=formatted_date, font=("Segoe UI", 13), text_color="#F5F5F5", justify="left")
            dt_lbl.pack(anchor="w", padx=12, pady=(2, 8))

            employee_name = " ".join(
                value for value in [
                    str(entry.get("first_name") or "").strip(),
                    str(entry.get("last_name") or "").strip()
                ]
                if value
            )
            employee_details = [
                f"Matricule : {entry.get('matricule') or '-'}",
                f"Employé : {employee_name or '-'}"
            ]
            if entry.get("department"):
                employee_details.append(f"Département : {entry.get('department')}")
            if entry.get("service"):
                employee_details.append(f"Service : {entry.get('service')}")

            employee_lbl = ctk.CTkLabel(
                frame,
                text="\n".join(employee_details),
                font=("Segoe UI", 13),
                text_color="#B7B7B7",
                justify="left"
            )
            employee_lbl.pack(anchor="w", padx=12, pady=(2, 8))

            sep = ctk.CTkFrame(frame, height=1, fg_color="#3B3B3B")
            sep.pack(fill="x", padx=12, pady=4)

            # Tool details
            details = (
                f"PN : {tool_record.get('part_number', '')}\n"
                f"SN : {tool_record.get('serial_number', '')}\n\n"
                f"{tool_record.get('description_tool', '')}"
            )
            det_lbl = ctk.CTkLabel(
                frame,
                text=details,
                font=("Segoe UI", 13),
                text_color="#B7B7B7",
                justify="left",
                wraplength=360
            )
            det_lbl.pack(anchor="w", padx=12, pady=(4, 10))

    # Form and button actions

    def show_history_action(self):
        if not self.require_permission("view_history"):
            return

        selected = self.tree.focus()

        if not selected:
            messagebox.showwarning(
                "No Selection",
                "Please select a tool first."
            )
            return

        values = self.tree.item(selected)["values"]

        tool = {
            "rfid_uid": values[0],
            "part_number": values[1],
            "serial_number": values[2],
            "description_tool": values[3],
        }

        self.show_side_panel("history", tool)

    def refresh_history(self, uid=None):
        if self.current_mode != "history":
            return

        tool = self.current_tool if isinstance(self.current_tool, dict) else None

        if uid:
            if tool and tool.get("rfid_uid") == uid:
                pass
            else:
                for candidate in self.manager.get_all_tools():
                    if str(candidate.get("rfid_uid", "")) == str(uid):
                        tool = candidate
                        break
                if tool is None:
                    tool = {"rfid_uid": uid}
        elif not tool:
            selected = self.tree.focus()
            if selected:
                values = self.tree.item(selected)["values"]
                tool = {
                    "rfid_uid": values[0],
                    "part_number": values[1],
                    "serial_number": values[2],
                    "description_tool": values[3],
                }

        if not tool:
            return

        self.current_tool = tool
        self.history_tool_uid = tool.get("rfid_uid")
        self.populate_history(tool)

    def refresh_all(self):
        selected_uid = None
        if self.current_mode == "history" and isinstance(self.current_tool, dict):
            selected_uid = self.current_tool.get("rfid_uid")

        self.load_tools(selected_uid=selected_uid)
        self.refresh_history(selected_uid)

    def save_tool(self):
        permission = "edit_tool" if self.current_mode == "edit" else "add_tool"
        if not self.require_permission(permission):
            return

        if self.current_mode == "edit" and self.current_tool:
            uid = self.current_tool.get("rfid_uid", "")
        else:
            uid = self.field_entries["rfid_uid"].get().strip()

        description_value = ""
        if self.description_box is not None:
            description_value = self.description_box.get("1.0", "end").strip()

        data = {
            "rfid_uid": uid,
            "part_number": self.field_entries["part_number"].get().strip(),
            "serial_number": self.field_entries["serial_number"].get().strip(),
            "description_tool": description_value,
            "last_check": self.field_entries["last_check"].get().strip(),
            "next_check": self.field_entries["next_check"].get().strip(),
            "status_": self.status_menu.get()
        }

        if self.current_mode == "edit":
            result = self.manager.update_tool(data)
        else:
            result = self.manager.add_tool(data)

        if result.get("success"):
            self.hide_side_panel()
            self.load_tools(data.get("rfid_uid"))
        else:
            messagebox.showerror(
                "Erreur",
                result.get("message", "Erreur inconnue.")
            )

    def cancel_edit(self):
        self.hide_side_panel()

    # Data loading

    def load_tools(self, selected_uid=None):
        tools = self.manager.get_all_tools()
        search = self.search_var.get().lower().strip()

        if search == "🔍 search tool...":
            search = ""

        for row in self.tree.get_children():
            self.tree.delete(row)

        item_to_select = None
        visible_tools = []

        for tool in tools:
            status = str(tool.get("status_", "")).strip()
            if self.active_filter and status != self.active_filter:
                continue

            text = " ".join([
                str(tool.get("rfid_uid", "")),
                str(tool.get("part_number", "")),
                str(tool.get("serial_number", "")),
                str(tool.get("description_tool", "")),
                str(tool.get("last_check", "")),
                str(tool.get("next_check", "")),
                str(tool.get("status_", ""))
            ]).lower()

            if search and search not in text:
                continue

            visible_tools.append(tool)

        for index, tool in enumerate(visible_tools):
            item = self.tree.insert(
                "",
                "end",
                values=(
                    tool.get("rfid_uid", ""),
                    tool.get("part_number", ""),
                    tool.get("serial_number", ""),
                    tool.get("description_tool", ""),
                    tool.get("last_check", ""),
                    tool.get("next_check", ""),
                    tool.get("status_", "")
                ),
                tags=("even" if index % 2 == 0 else "odd",)
            )

            if selected_uid and tool.get("rfid_uid") == selected_uid:
                item_to_select = item

        self.update_dashboard_stats(tools)

        if item_to_select:
            self.tree.selection_set(item_to_select)
            self.tree.focus(item_to_select)
            self.tree.see(item_to_select)
            self.after(2000, self.clear_selection)

    def update_dashboard_stats(self, tools):
        counts = {
            "Available": 0,
            "Borrowed": 0,
            "Maintenance": 0,
            "Calibration Due": 0
        }

        for tool in tools:
            status = str(tool.get("status_", "")).strip()
            if status == "BORROWED":
                counts["Borrowed"] += 1
            elif status == "MAINTENANCE":
                counts["Maintenance"] += 1
            elif status == "CALIBRATION_DUE":
                counts["Calibration Due"] += 1
            else:
                counts["Available"] += 1

        for card_info, key in zip(self.dashboard_cards[1:], ["Available", "Borrowed", "Maintenance", "Calibration Due"]):
            card_info["value_label"].configure(text=str(counts[key]))

        if self.dashboard_cards:
            self.dashboard_cards[0]["value_label"].configure(text=str(len(tools)))

    def _load_logo_image(self):
        if Image is None:
            self.logo.configure(text="[RAM]")
            return

        candidate_paths = [
            os.path.join(
                os.path.dirname(__file__),
                "assets_app_RAM",
                "IMG_2518.PNG",
            )
        ]

        for logo_path in candidate_paths:
            if not os.path.exists(logo_path):
                continue

            try:
                original_image = Image.open(logo_path).convert("RGBA")
                target_height = 85
                aspect_ratio = original_image.width / original_image.height
                target_width = int(target_height * aspect_ratio)

                logo_image = ctk.CTkImage(
                    light_image=original_image,
                    dark_image=original_image,
                    size=(target_width, target_height)
                )

                self.logo.configure(text="", image=logo_image, width=target_width, height=target_height)
                self.logo.image = logo_image
                return
            except Exception as e:
                print(f"Error loading image: {e}")
                continue

    def create_account_menu(self):
        # Keep this menu inside the app so it cannot cover another window.
        self.account_menu = ctk.CTkFrame(
            self,
            width=280,
            height=230,
            corner_radius=12,
            border_width=2,
            border_color="#3B3B3B",
            fg_color="#242424"
        )
        self.account_menu.pack_propagate(False)

        roles = [
            ("🧰 Storekeeper", "storekeeper"),
            ("👤 Supervisor", "supervisor"),
            ("🛠 Administrator", "administrator"),
        ]

        for label_text, role_value in roles:
            btn = ctk.CTkButton(
                self.account_menu,
                text=label_text,
                anchor="w",
                height=46,
                fg_color="transparent",
                hover_color="#3A3A3A",
                text_color="#F5F5F5",
                font=("Segoe UI", 16),
                command=lambda value=role_value: self.select_role(value)
            )
            btn.pack(fill="x", padx=10, pady=(4, 0))

        ctk.CTkFrame(
            self.account_menu,
            height=1,
            fg_color="#3B3B3B"
        ).pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkButton(
            self.account_menu,
            text="🚪 Logout",
            anchor="w",
            height=46,
            fg_color="transparent",
            hover_color="#3A3A3A",
            text_color="#F5F5F5",
            font=("Segoe UI", 16),
            command=self.logout,
        ).pack(fill="x", padx=10, pady=(0, 8))

        self.account_menu.place_forget()

    def toggle_account_menu(self):
        if self.role_menu_visible:
            self.close_account_menu()
        else:
            self._position_account_menu()
            self.account_menu.lift()
            self.role_menu_visible = True

    def select_role(self, role):
        self.close_account_menu()
        if role not in PROFILE_LABELS:
            return
        self.open_pin_dialog(role)

    def _position_account_menu(self):
        self.update_idletasks()
        x_pixels = self.status_button.winfo_rootx() - self.winfo_rootx()
        y_pixels = (
            self.status_button.winfo_rooty()
            - self.winfo_rooty()
            + self.status_button.winfo_height()
            + 5
        )
        menu_width_pixels = self.account_menu.winfo_reqwidth()
        x_pixels = max(
            8,
            min(x_pixels, max(8, self.winfo_width() - menu_width_pixels - 8)),
        )

        # Convert the position because Windows DPI changes the scale.
        x = self.account_menu._reverse_widget_scaling(x_pixels)
        y = self.account_menu._reverse_widget_scaling(y_pixels)
        self.account_menu.place(x=x, y=y)

    def close_account_menu(self):
        if self.account_menu is not None:
            self.account_menu.place_forget()
        self.role_menu_visible = False

    def _on_app_focus_out(self, _event=None):
        # Wait a little before checking if the user left the app.
        self.after(75, self._close_account_menu_if_app_unfocused)

    def _close_account_menu_if_app_unfocused(self):
        try:
            if self.focus_get() is None:
                self.close_account_menu()
        except Exception:
            self.close_account_menu()

    def open_pin_dialog(self, role):
        self.close_pin_dialog()

        dialog = ctk.CTkToplevel(self)
        self.pin_dialog = dialog
        dialog.title("Profile authentication")
        dialog.geometry("420x270")
        dialog.resizable(False, False)
        dialog.configure(fg_color="#1A1A1A")
        dialog.transient(self)
        dialog.protocol("WM_DELETE_WINDOW", self.close_pin_dialog)

        container = ctk.CTkFrame(dialog, fg_color="#242424", corner_radius=14)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            container,
            text=f"Sign in as {PROFILE_LABELS[role]}",
            font=("Segoe UI", 21, "bold"),
            text_color="#F5F5F5",
        ).pack(anchor="w", padx=20, pady=(20, 12))

        self.pin_entry = ctk.CTkEntry(
            container,
            placeholder_text="PIN",
            show="•",
            height=42,
            fg_color="#1A1A1A",
            border_color="#3B3B3B",
            text_color="#F5F5F5",
            font=("Segoe UI", 16),
        )
        self.pin_entry.pack(fill="x", padx=20)
        self.pin_entry.bind("<Return>", lambda _event: self.confirm_pin(role))

        self.pin_error_label = ctk.CTkLabel(
            container,
            text="",
            height=24,
            font=("Segoe UI", 13, "bold"),
            text_color="#E06B75",
        )
        self.pin_error_label.pack(anchor="w", padx=20, pady=(4, 4))

        actions = ctk.CTkFrame(container, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 18))
        actions.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            actions,
            text="Cancel",
            command=self.close_pin_dialog,
            fg_color="#4A4A4A",
            hover_color="#5A5A5A",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(
            actions,
            text="Confirm",
            command=lambda: self.confirm_pin(role),
            fg_color="#C8102E",
            hover_color="#E11F3E",
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        dialog.grab_set()
        dialog.after(50, self.pin_entry.focus_set)

    def confirm_pin(self, role):
        if self.pin_entry is None:
            return

        if self.pin_entry.get() != PROFILE_PINS.get(role):
            self.pin_entry.delete(0, "end")
            self.pin_error_label.configure(text="Incorrect PIN")
            self.pin_entry.focus_set()
            return

        self.close_pin_dialog()
        self.set_active_role(role)

    def close_pin_dialog(self):
        dialog = self.pin_dialog
        self.pin_dialog = None
        self.pin_entry = None
        self.pin_error_label = None
        if dialog is None:
            return

        try:
            if dialog.grab_current() == dialog:
                dialog.grab_release()
        except Exception:
            pass
        try:
            if dialog.winfo_exists():
                dialog.destroy()
        except Exception:
            pass

    def set_active_role(self, role):
        if role not in PROFILE_LABELS:
            return
        self.current_user_role = role
        label = PROFILE_LABELS[role]
        self.status_button.configure(text=f"Connected as {label} ▼")
        self.user_label.configure(text=label)
        self.apply_role_permissions()

        if self.has_permission("confirm_transaction") and self.deferred_scan is not None:
            scan = self.deferred_scan
            scan_id = self.deferred_scan_id
            self.deferred_scan = None
            self.deferred_scan_id = None
            self._handle_pending_scan(scan, scan_id)

    def logout(self):
        self.close_account_menu()
        self.close_pin_dialog()
        self.current_user_role = None
        self.status_button.configure(text="Not connected ▼")
        self.user_label.configure(text="Read-only mode")

        if self.current_mode in ("add", "edit", "history"):
            self.hide_side_panel()

        if self.transaction_dialog is not None:
            try:
                if self.transaction_dialog.winfo_exists():
                    self.transaction_dialog.cancel()
            except Exception:
                self.transaction_dialog = None

        self.apply_role_permissions()

    def has_permission(self, permission):
        permissions = ROLE_PERMISSIONS.get(
            self.current_user_role,
            READ_ONLY_PERMISSIONS,
        )
        return bool(permissions.get(permission, False))

    def require_permission(self, permission):
        if self.has_permission(permission):
            return True
        messagebox.showwarning(
            "Sign-in required",
            "Please sign in to perform this action.",
            parent=self,
        )
        return False

    def apply_role_permissions(self):
        permission_widgets = {
            "view_history": getattr(self, "history_button", None),
            "add_tool": getattr(self, "add_button", None),
            "edit_tool": getattr(self, "edit_button", None),
            "delete_tool": getattr(self, "delete_button", None),
        }
        for permission, widget in permission_widgets.items():
            if widget is not None:
                widget.configure(
                    state="normal" if self.has_permission(permission) else "disabled"
                )

        save_button = getattr(self, "save_button", None)
        if save_button is not None:
            save_permission = (
                "edit_tool" if self.current_mode == "edit" else "add_tool"
            )
            can_save = self.has_permission(save_permission)
            save_button.configure(state="normal" if can_save else "disabled")

    def apply_dashboard_filter(self, title):
        status_map = {
            "All": None,
            "Available": "AVAILABLE",
            "Borrowed": "BORROWED",
            "Maintenance": "MAINTENANCE",
            "Calibration Due": "CALIBRATION_DUE"
        }

        if title == "All":
            self.active_filter = None
        else:
            expected_status = status_map.get(title)
            if self.active_filter == expected_status:
                self.active_filter = None
            else:
                self.active_filter = expected_status

        self.update_dashboard_selection()
        self.load_tools()

    def _hover_dashboard_card(self, card, hovered):
        if self._is_selected_card(card):
            return
        card.configure(
            border_color="#FFFFFF" if hovered else card.cget("fg_color")
        )

    def _is_selected_card(self, card):
        for card_info in self.dashboard_cards:
            if card_info["card"] == card:
                return self.active_filter == self._status_for_title(card_info["title"])
        return False

    def _status_for_title(self, title):
        return {
            "All": None,
            "Available": "AVAILABLE",
            "Borrowed": "BORROWED",
            "Maintenance": "MAINTENANCE",
            "Calibration Due": "CALIBRATION_DUE"
        }.get(title)

    def update_dashboard_selection(self):
        for card_info in self.dashboard_cards:
            title = card_info["title"]
            card = card_info["card"]
            accent = card_info["accent"]
            selected = self.active_filter == self._status_for_title(title)
            if title == "All" and self.active_filter is None:
                selected = True

            if selected:
                card.configure(border_width=3, border_color="#FFFFFF")
            else:
                card.configure(border_width=2, border_color=accent)

    def edit_tool(self):
        if not self.require_permission("edit_tool"):
            return

        selected = self.tree.focus()

        if not selected:
            messagebox.showwarning(
                "Aucune sélection",
                "Veuillez sélectionner un outil."
            )
            return

        values = self.tree.item(selected)["values"]

        tool = {
            "rfid_uid": values[0],
            "part_number": values[1],
            "serial_number": values[2],
            "description_tool": values[3],
            "last_check": values[4],
            "next_check": values[5],
            "status_": values[6]
        }

        self.show_side_panel("edit", tool)

    def delete_tool(self):
        if not self.require_permission("delete_tool"):
            return

        selected = self.tree.focus()

        if not selected:
            messagebox.showwarning(
                "Aucune sélection",
                "Veuillez sélectionner un outil."
            )
            return

        values = self.tree.item(selected)["values"]

        confirm = messagebox.askyesno(
            "Confirmation",
            f"Voulez-vous vraiment supprimer l'outil\n\n{values[1]} ?"
        )

        if not confirm:
            return

        result = self.manager.delete_tool(values[0])

        if result.get("success"):
            self.load_tools()
            messagebox.showinfo(
                "Succès",
                "Outil supprimé avec succès."
            )
        else:
            messagebox.showerror(
                "Erreur",
                result.get("message", "Erreur inconnue.")
            )

    def clear_selection(self):
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

    def watch_scans(self):
        try:
            scan = self.manager.get_last_scan()
            if isinstance(scan, dict):
                scan_id = self._scan_identifier(scan)
                if scan_id:
                    is_initial_scan = not self.initial_scan_checked
                    self.initial_scan_checked = True
                    already_processed = scan_id == self.last_scan_uid
                    already_pending = scan_id == self.pending_scan_id
                    already_deferred = scan_id == self.deferred_scan_id

                    if not already_processed and not already_pending and not already_deferred:
                        action = str(scan.get("actions", "")).strip().upper()
                        if action == "SCAN":
                            self._handle_pending_scan(scan, scan_id)
                        elif action in ("CHECK_OUT", "CHECK_IN"):
                            if is_initial_scan:
                                # The latest confirmed transaction is baseline state,
                                # not a new event produced during this app session.
                                self._mark_scan_processed(scan_id)
                            else:
                                self._handle_legacy_scan(scan, scan_id, action)
                        else:
                            # Do not retry an action that the API does not know.
                            self._mark_scan_processed(scan_id)
        except Exception as e:
            print(e)

        self.after(1000, self.watch_scans)

    def _handle_legacy_scan(self, scan, scan_id, action):
        """Handle a scan that was already confirmed by the old API."""
        uid = str(scan.get("rfid_uid", "")).strip()

        # Refresh everything and highlight the scanned tool.
        self.load_tools(selected_uid=uid)

        if (
            self.current_mode == "history"
            and self.current_tool
            and str(self.current_tool.get("rfid_uid", "")).strip() == uid
        ):
            self.refresh_history(uid)

        self.show_notification(scan, action)

        # Save it last so the app can retry after a temporary error.
        self._mark_scan_processed(scan_id)

    def _scan_identifier(self, scan):
        log_id = scan.get("log_id")
        if log_id not in (None, ""):
            return str(log_id)
        return str(scan.get("scan_time", "")).strip()

    def _suggested_action(self, scan):
        action = str(scan.get("suggested_action") or "").upper()
        if action in ("CHECK_OUT", "CHECK_IN"):
            return action

        status = str(scan.get("status_", "")).upper()
        if status == "AVAILABLE":
            return "CHECK_OUT"
        if status == "BORROWED":
            return "CHECK_IN"
        return None

    def _handle_pending_scan(self, scan, scan_id):
        if not self.has_permission("confirm_transaction"):
            # Keep the API's pending SCAN available without warning every poll.
            self.deferred_scan = scan
            self.deferred_scan_id = scan_id
            return

        if self.transaction_dialog is not None:
            try:
                if self.transaction_dialog.winfo_exists():
                    return
            except Exception:
                pass
            self.transaction_dialog = None

        action = self._suggested_action(scan)
        if action is None:
            self._mark_scan_processed(scan_id)
            messagebox.showwarning(
                "Opération interdite",
                "Cet outil ne peut pas être prêté ou retourné dans son statut actuel."
            )
            return

        scan["suggested_action"] = action
        self.pending_scan_id = scan_id
        self.transaction_dialog = TransactionDialog(
            self,
            scan,
            self.manager,
            self._transaction_confirmed,
            self._transaction_cancelled
        )

    def _mark_scan_processed(self, scan_id):
        scan_id = str(scan_id)
        self.last_scan_uid = scan_id
        with open(LAST_SCAN_FILE, "w", encoding="utf-8") as file:
            file.write(scan_id)

    def _transaction_cancelled(self, scan):
        scan_id = self._scan_identifier(scan)
        if scan_id:
            self._mark_scan_processed(scan_id)
        self.pending_scan_id = None
        self.transaction_dialog = None

    def _transaction_confirmed(self, scan, action, result):
        scan_id = self._scan_identifier(scan)
        uid = str(scan.get("rfid_uid", ""))

        if scan_id:
            self._mark_scan_processed(scan_id)

        self.pending_scan_id = None
        self.transaction_dialog = None

        self.load_tools(selected_uid=uid)

        if (
            self.current_mode == "history"
            and self.current_tool
            and str(self.current_tool.get("rfid_uid", "")) == uid
        ):
            self.refresh_history(uid)

        tool = result.get("tool") if isinstance(result, dict) else None
        if not isinstance(tool, dict):
            tool = dict(scan)
            tool["status_"] = "BORROWED" if action == "CHECK_OUT" else "AVAILABLE"

        self.show_notification(tool, action)

    def show_notification(self, tool, action):
        title = "RFID Aircraft Tool Tracking"
        description = str(tool.get("description_tool", "Outil RFID"))
        part_number = str(tool.get("part_number", ""))

        if action == "CHECK_OUT":
            msg = (
                f"{description}\n"
                f"PN : {part_number}\n\n"
                "Status : BORROWED"
            )
        elif action == "CHECK_IN":
            msg = (
                f"{description}\n"
                f"PN : {part_number}\n\n"
                "Status : AVAILABLE"
            )
        else:
            return

        toast = Notification(
            app_id="RFID Aircraft Tool Tracking",
            title=title,
            msg=msg,
            duration="short"
        )
        toast.show()

if __name__ == "__main__":
    app = ToolTrackerApp()
    app.mainloop()
