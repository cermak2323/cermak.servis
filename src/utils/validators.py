import re
from datetime import datetime
import locale

# Set Turkish locale for currency formatting
locale.setlocale(locale.LC_ALL, 'tr_TR.UTF-8')

def validate_part_code(code):
    """
    Validates part code format
    Rules:
    - Only letters, numbers, hyphen and underscore
    - Length between 3 and 20 characters
    """
    if not code:
        return False, "Parça kodu boş olamaz"
        
    pattern = r'^[A-Za-z0-9_-]{3,20}$'
    if not re.match(pattern, code):
        return False, "Geçersiz parça kodu formatı"
        
    return True, None

def validate_price(price):
    """
    Validates price value
    Rules:
    - Must be positive number
    - Maximum 2 decimal places
    """
    try:
        price = float(price)
        if price < 0:
            return False, "Fiyat negatif olamaz"
            
        # Check decimal places
        if len(str(price).split('.')[-1]) > 2:
            return False, "En fazla 2 ondalık basamak kullanılabilir"
            
        return True, None
    except ValueError:
        return False, "Geçersiz fiyat formatı"

def validate_date(date_str):
    """
    Validates date string format (DD.MM.YYYY)
    """
    try:
        datetime.strptime(date_str, '%d.%m.%Y')
        return True, None
    except ValueError:
        return False, "Geçersiz tarih formatı (GG.AA.YYYY)"

def format_price(amount, currency="TRY"):
    """
    Formats price according to Turkish locale
    """
    try:
        formatted = locale.currency(amount, symbol=False, grouping=True)
        if currency == "TRY":
            return f"{formatted} ₺"
        elif currency == "EUR":
            return f"{formatted} €"
        return formatted
    except:
        return f"{amount:.2f}"

def sanitize_input(text):
    """
    Sanitizes user input by removing dangerous characters
    """
    if not text:
        return ""
        
    # Remove special characters that could be used for injection
    text = re.sub(r'[<>&;]', '', text)
    
    # Limit length
    return text[:100]
