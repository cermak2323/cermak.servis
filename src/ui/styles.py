import tkinter as tk
from tkinter import ttk
import json
import os

def load_theme():
    theme_path = os.path.join(
        os.path.dirname(__file__),
        '../assets/theme.json'
    )
    
    with open(theme_path, 'r') as f:
        return json.load(f)

def apply_style(root):
    theme = load_theme()
    
    style = ttk.Style(root)
    
    # Configure main theme
    style.configure(
        ".",
        background=theme["background"],
        foreground=theme["foreground"],
        font=("Helvetica", 12)
    )
    
    # Configure Treeview
    style.configure(
        "Treeview",
        background=theme["treeview"]["background"],
        foreground=theme["treeview"]["foreground"],
        fieldbackground=theme["treeview"]["fieldbackground"],
        rowheight=30
    )
    
    style.configure(
        "Treeview.Heading",
        background=theme["treeview"]["header_background"],
        foreground=theme["treeview"]["header_foreground"],
        font=("Helvetica", 12, "bold")
    )
    
    # Configure Buttons
    style.configure(
        "TButton",
        padding=10,
        background=theme["button"]["background"],
        foreground=theme["button"]["foreground"]
    )
    
    style.configure(
        "Accent.TButton",
        background=theme["button"]["accent_background"],
        foreground=theme["button"]["accent_foreground"]
    )
    
    style.configure(
        "Danger.TButton",
        background=theme["button"]["danger_background"],
        foreground=theme["button"]["danger_foreground"]
    )
    
    # Configure Entry
    style.configure(
        "TEntry",
        padding=5,
        background=theme["entry"]["background"],
        foreground=theme["entry"]["foreground"]
    )
    
    # Configure Frame
    style.configure(
        "TFrame",
        background=theme["background"]
    )
    
    # Configure LabelFrame
    style.configure(
        "TLabelframe",
        background=theme["background"],
        foreground=theme["foreground"]
    )
    
    style.configure(
        "TLabelframe.Label",
        font=("Helvetica", 12, "bold")
    )
