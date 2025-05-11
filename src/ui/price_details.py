import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from src.database import Database
from src.services.currency import get_current_rate
from src.services.logger import get_logger

logger = get_logger(__name__)

class PriceDetailsWindow:
    def __init__(self, parent, part_code):
        self.window = tk.Toplevel(parent)
        self.window.title(f"Fiyat Detayları - {part_code}")
        self.window.geometry("1280x1024")
        
        self.part_code = part_code
        self.db = Database()
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(expand=True, fill="both")
        
        # Part details
        self.show_part_details(main_frame)
        
        # Price history graph
        self.show_price_history(main_frame)
        
    def show_part_details(self, parent):
        details_frame = ttk.LabelFrame(
            parent,
            text="Parça Bilgileri",
            padding="10"
        )
        details_frame.pack(fill="x", pady=10)
        
        # Get part details
        part = self.db.get_part_details(self.part_code)
        rate = get_current_rate()
        
        if part and rate:
            part_code, name, price_eur, last_updated = part
            price_try = price_eur * rate
            
            # Create labels
            labels = [
                ("Parça Kodu:", part_code),
                ("Parça Adı:", name),
                ("Fiyat (EUR):", f"{price_eur:.2f} €"),
                ("Fiyat (TRY):", f"{price_try:.2f} ₺"),
                ("Son Güncelleme:", last_updated)
            ]
            
            for row, (label, value) in enumerate(labels):
                ttk.Label(
                    details_frame,
                    text=label,
                    font=("Helvetica", 12, "bold")
                ).grid(row=row, column=0, padx=5, pady=5, sticky="e")
                
                ttk.Label(
                    details_frame,
                    text=value,
                    font=("Helvetica", 12)
                ).grid(row=row, column=1, padx=5, pady=5, sticky="w")
                
    def show_price_history(self, parent):
        history_frame = ttk.LabelFrame(
            parent,
            text="Fiyat Geçmişi",
            padding="10"
        )
        history_frame.pack(fill="both", expand=True, pady=10)
        
        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Get price history
        with self.db.db_path as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT date, price_try
                FROM price_history
                WHERE part_code = ?
                ORDER BY date
            ''', (self.part_code,))
            
            history = cursor.fetchall()
            
            if history:
                dates, prices = zip(*history)
                ax.plot(dates, prices, marker='o')
                ax.set_xlabel('Tarih')
                ax.set_ylabel('Fiyat (TRY)')
                ax.set_title('Fiyat Değişim Grafiği')
                plt.xticks(rotation=45)
                
                # Embed plot in tkinter
                canvas = FigureCanvasTkAgg(fig, master=history_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)
            else:
                ttk.Label(
                    history_frame,
                    text="Fiyat geçmişi bulunamadı",
                    font=("Helvetica", 12)
                ).pack(pady=20)
