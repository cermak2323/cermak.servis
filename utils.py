import requests
import xml.etree.ElementTree as ET
import logging
from apscheduler.schedulers.background import BackgroundScheduler

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Döviz kuru saklama
exchange_rates = {'EUR': 0.0}
TCMB_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"

# TCMB'den döviz kuru çekme
def fetch_exchange_rates():
    try:
        response = requests.get(TCMB_URL)
        if response.status_code == 200:
            tree = ET.fromstring(response.content)
            found = False
            for currency in tree.findall('Currency'):
                if currency.attrib.get('CurrencyCode') == 'EUR':
                    forex_selling = currency.find('ForexSelling').text
                    if forex_selling:
                        eur_rate = float(forex_selling.replace(',', '.'))
                        exchange_rates['EUR'] = eur_rate
                        logger.info(f"Güncel EUR döviz satış kuru alındı: {eur_rate}")
                        found = True
                        break
            if not found:
                logger.error("EUR döviz satış verisi bulunamadı!")
                exchange_rates['EUR'] = 42.0  # Varsayılan kur
        else:
            logger.error(f"Döviz kuru verisine erişilemedi. HTTP Kodu: {response.status_code}")
            exchange_rates['EUR'] = 42.0  # Varsayılan kur
    except Exception as e:
        logger.error(f"Döviz kuru alınırken hata: {e}")
        exchange_rates['EUR'] = 42.0  # Varsayılan kur

def get_latest_exchange_rate():
    """Son döviz kurlarını döndür"""
    return exchange_rates

# İlk döviz kuru çekimini hemen yap
fetch_exchange_rates()

# Arka plan görevi için zamanlayıcı (start() çağrısını kaldırıyoruz)
scheduler = BackgroundScheduler()
scheduler.add_job(func=fetch_exchange_rates, trigger="interval", hours=1)  # Saat başı güncelle
# scheduler.start() # Bu satırı kaldırdık, başlatma main.py içinde yapılacak
import subprocess
import sys
import pkg_resources
import logging

def check_and_install_requirements():
    """Check and install missing packages from requirements.txt"""
    try:
        # requirements.txt dosyasını oku
        requirements = pkg_resources.parse_requirements(open('requirements.txt'))
        
        # Eksik paketleri bul
        missing = []
        for requirement in requirements:
            try:
                pkg_resources.require(str(requirement))
            except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict):
                missing.append(str(requirement))
        
        # Eksik paketleri kur
        if missing:
            logging.info(f"Installing missing packages: {', '.join(missing)}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
            logging.info("All required packages installed successfully")
            return True
    except Exception as e:
        logging.error(f"Error installing packages: {str(e)}")
        return False
    
    return True

def get_current_exchange_rate():
    """Güncel EUR/TRY kurunu döndürür"""
    try:
        return get_latest_exchange_rate()["EUR"]
    except:
        # Varsayılan kur (API'den alınamazsa)
        return 35.0  # Varsayılan EUR/TRY kuru

# Dosya yükleme için izin verilen uzantılar
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    """
    Yüklenen dosyanın izin verilen bir uzantıya sahip olup olmadığını kontrol eder.
    
    Args:
        filename (str): Kontrol edilecek dosya adı
        
    Returns:
        bool: Dosya uzantısı izin veriliyorsa True, değilse False
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS