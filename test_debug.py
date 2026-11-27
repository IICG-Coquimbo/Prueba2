import os
import sys

print('Before:')
print('  sys.path[0]:', sys.path[0])
print('  CWD:', os.getcwd())

# Get the directory of the manage.py file
manage_dir = os.path.dirname(os.path.abspath(__file__))
print('  manage.py directory:', manage_dir)

# Add cafe_proyecto directory
cafe_proyecto_dir = os.path.join(manage_dir, 'cafe_proyecto')
print('  cafe_proyecto_dir:', cafe_proyecto_dir)
print('  exists:', os.path.exists(cafe_proyecto_dir))

sys.path.insert(0, cafe_proyecto_dir)

print('After:')
print('  sys.path[0]:', sys.path[0])

# Check if cafe_proyecto is findable
try:
    import cafe_proyecto
    print('  cafe_proyecto imported from:', cafe_proyecto.__file__)
    print('  cafe_proyecto.__path__:', cafe_proyecto.__path__)
except ModuleNotFoundError as e:
    print('  ModuleNotFoundError for cafe_proyecto:', e)

# Now try the settings
try:
    import cafe_proyecto.settings
    print('  cafe_proyecto.settings imported successfully')
except ModuleNotFoundError as e:
    print('  ModuleNotFoundError for cafe_proyecto.settings:', e)