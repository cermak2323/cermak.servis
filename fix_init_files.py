import os

modules = [
    'auth',
    'parts',
    'catalogs',
    'faults',
    'contact',
    'maintenance',
    'periodic_maintenance',
    'offers',
    'machines'
]

for module in modules:
    init_path = os.path.join(module, '__init__.py')
    # Önce dosyayı sil
    if os.path.exists(init_path):
        os.remove(init_path)
    # Yeni dosya oluştur
    with open(init_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('')  # Boş dosya 