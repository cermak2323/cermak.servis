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
    with open(init_path, 'w', encoding='utf-8') as f:
        f.write(f'"""\\n{module.title()} module initialization\\n"""\n\n') 