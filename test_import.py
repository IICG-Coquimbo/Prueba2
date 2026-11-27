import os
import sys

# Add the current directory to sys.path
cwd = os.getcwd()
sys.path.insert(0, cwd)

print('sys.path[0]:', sys.path[0])
print('CWD:', cwd)

# Check if cafe_proyecto is findable
try:
    import cafe_proyecto
    print('cafe_proyecto imported from:', cafe_proyecto.__file__)
except ModuleNotFoundError as e:
    print('ModuleNotFoundError for cafe_proyecto:', e)

# Now try the settings
try:
    import cafe_proyecto.settings
    print('cafe_proyecto.settings imported successfully')
except ModuleNotFoundError as e:
    print('ModuleNotFoundError for cafe_proyecto.settings:', e)