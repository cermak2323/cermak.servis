import tkinter as tk
from src.ui.login import LoginWindow
from src.database import initialize_database
from src.services.logger import setup_logger

def main():
    # Initialize logging
    setup_logger()
    
    # Initialize database
    initialize_database()
    
    # Create root window
    root = tk.Tk()
    root.withdraw()  # Hide main window initially
    
    # Start with login window
    login_window = LoginWindow(root)
    
    # Start main event loop
    root.mainloop()

if __name__ == "__main__":
    main()
