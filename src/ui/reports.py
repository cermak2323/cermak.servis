import tkinter as tk
from tkinter import ttk, messagebox
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import pandas as pd
from src.database import Database
from src.services.logger import get_logger

logger = get_logger(__name__)

class ReportsWindow:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Raporlar")
        self.window.geometry("1280x1024")
        
        self.db = Database()
        self.create_widgets()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(expand=True, fill="both")
        
        # Report type selection
        self.create_report_selection(main_frame)
        
        # Date range selection
        self.create_date_selection(main_frame)
        
        # Generate button
        ttk.Button(
            main_frame,
            text="Rapor Oluştur",
            command=self.generate_report,
            style="Accent.TButton"
        ).pack(pady=20)
        
    def create_report_selection(self, parent):
        report_frame = ttk.LabelFrame(
            parent,
            text="Rapor Türü",
            padding="10"
        )
        report_frame.pack(fill="x", pady=10)
        
        self.report_type = tk.StringVar(value="price_history")
        
        reports = [
            ("Fiyat Geçmişi", "price_history"),
            ("Arama Geçmişi", "search_history"),
            ("Stok Durumu", "stock_status")
        ]
        
        for text, value in reports:
            ttk.Radiobutton(
                report_frame,
                text=text,
                value=value,
                variable=self.report_type
            ).pack(anchor="w", pady=5)
            
    def create_date_selection(self, parent):
        date_frame = ttk.LabelFrame(
            parent,
            text="Tarih Aralığı",
            padding="10"
        )
        date_frame.pack(fill="x", pady=10)
        
        # Start date
        ttk.Label(
            date_frame,
            text="Başlangıç Tarihi:"
        ).pack(anchor="w")
        
        self.start_date = ttk.Entry(date_frame)
        self.start_date.pack(fill="x", pady=5)
        
        # End date
        ttk.Label(
            date_frame,
            text="Bitiş Tarihi:"
        ).pack(anchor="w")
        
        self.end_date = ttk.Entry(date_frame)
        self.end_date.pack(fill="x", pady=5)
        
    def generate_report(self):
        try:
            report_type = self.report_type.get()
            start_date = self.start_date.get()
            end_date = self.end_date.get()
            
            if report_type == "price_history":
                self.generate_price_history_report(start_date, end_date)
            elif report_type == "search_history":
                self.generate_search_history_report(start_date, end_date)
            elif report_type == "stock_status":
                self.generate_stock_status_report()
                
        except Exception as e:
            logger.error(f"Report generation error: {e}")
            messagebox.showerror("Hata", "Rapor oluşturulurken bir hata oluştu!")
            
    def generate_price_history_report(self, start_date, end_date):
        # Get data from database
        with self.db.db_path as conn:
            query = '''
                SELECT part_code, date, price_eur, price_try, exchange_rate
                FROM price_history
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC
            '''
            
            df = pd.read_sql_query(query, conn, params=(start_date, end_date))
            
        # Generate PDF
        doc = SimpleDocTemplate(
            "fiyat_raporu.pdf",
            pagesize=letter
        )
        
        # Create table data
        table_data = [df.columns.tolist()] + df.values.tolist()
        
        # Create table
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        # Build PDF
        doc.build([table])
        
        messagebox.showinfo(
            "Başarılı",
            "Rapor başarıyla oluşturuldu: fiyat_raporu.pdf"
        )
