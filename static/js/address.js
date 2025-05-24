
const cities = {
    "Adana": [],
    "Adıyaman": [],
    "Afyonkarahisar": [],
    "Ağrı": [],
    "Amasya": [],
    "Ankara": [],
    "Antalya": [],
    "Artvin": [],
    "Aydın": [],
    "Balıkesir": [],
    "Bilecik": [],
    "Bingöl": [],
    "Bitlis": [],
    "Bolu": [],
    "Burdur": [],
    "Bursa": [],
    "Çanakkale": [],
    "Çankırı": [],
    "Çorum": [],
    "Denizli": [],
    "Diyarbakır": [],
    "Edirne": [],
    "Elazığ": [],
    "Erzincan": [],
    "Erzurum": [],
    "Eskişehir": [],
    "Gaziantep": [],
    "Giresun": [],
    "Gümüşhane": [],
    "Hakkari": [],
    "Hatay": [],
    "Isparta": [],
    "Mersin": [],
    "İstanbul": [],
    "İzmir": [],
    "Kars": [],
    "Kastamonu": [],
    "Kayseri": [],
    "Kırklareli": [],
    "Kırşehir": [],
    "Kocaeli": [],
    "Konya": [],
    "Kütahya": [],
    "Malatya": [],
    "Manisa": [],
    "Kahramanmaraş": [],
    "Mardin": [],
    "Muğla": [],
    "Muş": [],
    "Nevşehir": [],
    "Niğde": [],
    "Ordu": [],
    "Rize": [],
    "Sakarya": [],
    "Samsun": [],
    "Siirt": [],
    "Sinop": [],
    "Sivas": [],
    "Tekirdağ": [],
    "Tokat": [],
    "Trabzon": [],
    "Tunceli": [],
    "Şanlıurfa": [],
    "Uşak": [],
    "Van": [],
    "Yozgat": [],
    "Zonguldak": [],
    "Aksaray": [],
    "Bayburt": [],
    "Karaman": [],
    "Kırıkkale": [],
    "Batman": [],
    "Şırnak": [],
    "Bartın": [],
    "Ardahan": [],
    "Iğdır": [],
    "Yalova": [],
    "Karabük": [],
    "Kilis": [],
    "Osmaniye": [],
    "Düzce": []
};

document.addEventListener('DOMContentLoaded', function() {
    const citySelect = document.getElementById('city');
    const addressInput = document.getElementById('address');
    const phoneInput = document.getElementById('phone_number');
    
    // Load cities
    Object.keys(cities).sort().forEach(city => {
        const option = document.createElement('option');
        option.value = city;
        option.textContent = city;
        citySelect.appendChild(option);
    });

    // Update address when city changes
    citySelect.addEventListener('change', function() {
        const selectedCity = this.value;
        addressInput.value = selectedCity + ' ';
    });
});
