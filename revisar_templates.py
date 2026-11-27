import glob

from django.template.loader import get_template

for path in glob.glob('**/templates/**/*.html', recursive=True):
    get_template(path.split('templates/', 1)[1])

print('templates OK')
