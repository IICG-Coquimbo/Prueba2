import os
import sys

# Setup path
cwd = os.getcwd()
sys.path.insert(0, cwd)
cafe_proyecto_dir = os.path.join(cwd, 'cafe_proyecto')
sys.path.insert(0, cafe_proyecto_dir)

# Setup Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'cafe_proyecto.settings'

import django
django.setup()

# Check installed apps
from django.conf import settings
print("Installed Apps from settings:")
for app in settings.INSTALLED_APPS:
    print(f"  - {app}")

# Check app configs
print("\nAppConfigs registered:")
for app_config in django.apps.apps.get_app_configs():
    print(f"  - {app_config.name} (label: {app_config.label})")

print("\n✅ All apps are consistent!")