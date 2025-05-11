import tkinter as tk
from tkinter import ttk
from src.ui.parts_search import PartsSearchWindow
from src.ui.reports import ReportsWindow
from src.services.currency import get_current_rate
from src.ui.styles import apply_style
from src.services.logger import get_logger

logger = get_logger(__name__)

class MainMenu:
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel()
        self.window.title("Ana Menü - Parça Yönetim Sistemi")
        self.window.geometry("1280x1024")
        
        apply_style(self.window)
        self.create_widgets()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(expand=True, fill="both")
        
        # Header with exchange rate
        self.create_header(main_frame)
        
        # Menu buttons
        self.create_menu_buttons(main_frame)
        
    def create_header(self, parent):
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x", pady=20)
        
        # Company name
        ttk.Label(
            header_frame,
            text="TAKEUCHI",
            font=("Helvetica", 36, "bold")
        ).pack()
        
        # Exchange rate
        rate = get_current_rate()
        if rate:
            rate_text = f"Güncel Euro Kuru: {rate:.2f} ₺"
        else:
            rate_text = "Döviz kuru alınamadı"
            
        ttk.Label(
            header_frame,
            text=rate_text,
            font=("Helvetica", 14)
        ).pack(pady=10)
        
    def create_menu_buttons(self, parent):
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(expand=True)
        
        # Parts search button
        ttk.Button(
            buttons_frame,
            text="Parça Arama",
            command=self.open_parts_search,
            style="Accent.TButton",
            width=30
        ).pack(pady=10)
        
        # Reports button
        ttk.Button(
            buttons_frame,
            text="Raporlar",
            command=self.open_reports,
            style="Accent.TButton",
            width=30
        ).pack(pady=10)
        
        # Exit button
        ttk.Button(
            buttons_frame,
            text="Çıkış",
            command=self.window.destroy,
            style="Danger.TButton",
            width=30
        ).pack(pady=10)
        
    def open_parts_search(self):
        logger.info("Opening parts search window")
        PartsSearchWindow(self.window)
        
    def open_reports(self):
        logger.info("Opening reports window")
        ReportsWindow(self.window)
