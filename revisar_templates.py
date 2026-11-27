import glob
from django.template.loader import get_template
[get_template(p.split('templates/', 1)[1]) for p in glob.glob('**/templates/**/*.html', recursive=True)]
print('templates OK')