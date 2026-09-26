import os

dirs = [
    'backend', 'backend/app', 'backend/app/core', 'backend/app/db', 
    'backend/app/schemas', 'backend/app/crypto', 'backend/app/detectors',
    'backend/app/correlation', 'backend/app/policies', 'backend/app/services',
    'backend/app/api', 'backend/app/api/routes', 'backend/app/fixtures'
]

for d in dirs:
    os.makedirs(d, exist_ok=True)
    init_path = os.path.join(d, '__init__.py')
    if not os.path.exists(init_path):
        with open(init_path, 'w', encoding='utf-8') as f:
            f.write('# DRISHTRA package init\n')

print("All package init files confirmed.")
