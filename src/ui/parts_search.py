import tkinter as tk
from tkinter import ttk
from src.database import Database
from src.ui.price_details import PriceDetailsWindow
from src.services.currency import get_current_rate
from src.services.logger import get_logger

logger = get_logger(__name__)

class PartsSearchWindow:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Parça Arama")
        self.window.geometry("1280x1024")
        
        self.db = Database()
        self.create_widgets()
        
    def create_widgets(self):
        # Search frame
        search_frame = ttk.Frame(self.window, padding="20")
        search_frame.pack(fill="x")
        
        # Search entry
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=("Helvetica", 12),
            width=40
        )
        self.search_entry.pack(side="left", padx=5)
        
        # Search button
        ttk.Button(
            search_frame,
            text="Ara",
            command=self.search_parts,
            style="Accent.TButton"
        ).pack(side="left", padx=5)
        
        # Results treeview
        self.create_results_treeview()
        
    def create_results_treeview(self):
        columns = ("part_code", "name", "price_eur", "price_try")
        
        self.tree = ttk.Treeview(
            self.window,
            columns=columns,
            show="headings",
            height=20
        )
        
        # Define columns
        self.tree.heading("part_code", text="Parça Kodu")
        self.tree.heading("name", text="Parça Adı")
        self.tree.heading("price_eur", text="Fiyat (EUR)")
        self.tree.heading("price_try", text="Fiyat (TRY)")
        
        # Column widths
        self.tree.column("part_code", width=150)
        self.tree.column("name", width=300)
        self.tree.column("price_eur", width=150)
        self.tree.column("price_try", width=150)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(
            self.window,
            orient="vertical",
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.tree.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        scrollbar.pack(side="right", fill="y", pady=20)
        
        # Bind double-click
        self.tree.bind("<Double-1>", self.show_part_details)
        
    def search_parts(self):
        search_term = self.search_var.get().strip().upper()
        
        # Clear current results
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        try:
            # Get current exchange rate
            rate = get_current_rate()
            
            # Search in database
            with self.db.db_path as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT part_code, name, price_eur
                    FROM parts
                    WHERE part_code LIKE ? OR name LIKE ?
                ''', (f'%{search_term}%', f'%{search_term}%'))
                
                results = cursor.fetchall()
                
                for part in results:
                    part_code, name, price_eur = part
                    price_try = price_eur * rate if rate else 0
                    
                    self.tree.insert('', 'end', values=(
                        part_code,
                        name,
                        f"{price_eur:.2f}",
                        f"{price_try:.2f}"
                    ))
                    
            logger.info(f"Search completed for term: {search_term}")
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            tk.messagebox.showerror("Hata", "Arama sırasında bir hata oluştu!")
            
    def show_part_details(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            return
            
        part_code = self.tree.item(selected_item[0])['values'][0]
        PriceDetailsWindow(self.window, part_code)
