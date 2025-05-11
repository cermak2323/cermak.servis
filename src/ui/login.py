import tkinter as tk
from tkinter import ttk, messagebox
import hashlib
from src.ui.styles import apply_style
from src.ui.main_menu import MainMenu
from src.services.logger import get_logger

logger = get_logger(__name__)

class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel()
        self.window.title("Giriş - Parça Yönetim Sistemi")
        self.window.geometry("1280x1024")
        
        # Apply styles
        apply_style(self.window)
        
        self.create_widgets()
        
    def create_widgets(self):
        # Create main frame
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(expand=True, fill="both")
        
        # Logo
        self.logo_label = ttk.Label(
            main_frame, 
            text="TAKEUCHI", 
            font=("Helvetica", 48, "bold")
        )
        self.logo_label.pack(pady=40)
        
        # Login frame
        login_frame = ttk.Frame(main_frame, padding="20")
        login_frame.pack(expand=True)
        
        # Username
        ttk.Label(
            login_frame, 
            text="Kullanıcı Adı:", 
            font=("Helvetica", 14)
        ).pack(pady=5)
        
        self.username_entry = ttk.Entry(
            login_frame, 
            font=("Helvetica", 12),
            width=30
        )
        self.username_entry.pack(pady=5)
        
        # Password
        ttk.Label(
            login_frame, 
            text="Şifre:", 
            font=("Helvetica", 14)
        ).pack(pady=5)
        
        self.password_entry = ttk.Entry(
            login_frame, 
            show="*", 
            font=("Helvetica", 12),
            width=30
        )
        self.password_entry.pack(pady=5)
        
        # Login button
        login_button = ttk.Button(
            login_frame,
            text="Giriş Yap",
            command=self.login,
            style="Accent.TButton"
        )
        login_button.pack(pady=20)
        
        # Bind enter key
        self.window.bind("<Return>", lambda e: self.login())
        
    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Validate credentials (replace with database check in production)
        if username == "Cermak" and password == "Cermak2025":
            logger.info(f"Successful login: {username}")
            self.window.destroy()
            MainMenu(self.root)
        else:
            logger.warning(f"Failed login attempt: {username}")
            messagebox.showerror(
                "Hata",
                "Geçersiz kullanıcı adı veya şifre!"
            )
