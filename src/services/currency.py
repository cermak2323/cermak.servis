import requests
import xml.etree.ElementTree as ET
import time
from datetime import datetime
import os
from src.services.logger import get_logger

logger = get_logger(__name__)

# Cache settings
_cache = {
    'rates': {},
    'timestamp': None
}
CACHE_DURATION = 3600  # 1 hour in seconds

def get_exchange_rates():
    """
    Fetches current EUR/TRY and JPY/TRY exchange rates from TCMB
    Returns dict with rates or None on failure
    """
    # Check cache
    if _cache['rates'] and _cache['timestamp']:
        if time.time() - _cache['timestamp'] < CACHE_DURATION:
            return _cache['rates']

    try:
        url = "https://www.tcmb.gov.tr/kurlar/today.xml"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        tree = ET.ElementTree(ET.fromstring(response.content))
        root = tree.getroot()

        rates = {}
        for currency in root.findall(".//Currency"):
            code = currency.get("Kod")
            if code in ["EUR", "JPY"]:
                rate = float(currency.find("ForexSelling").text)
                rates[code] = rate

        if "EUR" in rates and "JPY" in rates:
            # Update cache
            _cache['rates'] = rates
            _cache['timestamp'] = time.time()

            logger.info(f"Exchange rates updated: 1 EUR = {rates['EUR']} TRY, 1 JPY = {rates['JPY']} TRY")
            return rates

        logger.error("Required currency rates not found in TCMB response")
        return None

    except requests.RequestException as e:
        logger.error(f"Failed to fetch exchange rates: {e}")
        return None
    except (ValueError, ET.ParseError) as e:
        logger.error(f"Failed to parse exchange rate data: {e}")
        return None

def convert_jpy_to_eur(amount_jpy):
    """
    Converts JPY amount to EUR using current rates
    Returns tuple (amount_eur, rates_used) or (None, None) on failure
    """
    rates = get_exchange_rates()
    if not rates:
        return None, None

    # Calculate JPY/EUR cross rate
    jpy_eur_rate = rates['JPY'] / rates['EUR']
    amount_eur = amount_jpy * jpy_eur_rate

    return amount_eur, rates

def format_currency(amount, currency="TRY"):
    """
    Formats amount with currency symbol
    """
    if currency == "TRY":
        return f"{amount:.2f} ₺"
    elif currency == "EUR":
        return f"{amount:.2f} €"
    elif currency == "JPY":
        return f"{amount:.2f} ¥"
    else:
        return f"{amount:.2f}"