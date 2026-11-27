import glob

from django.template.loader import get_template


plantillas = glob.glob("**/templates/**/*.html", recursive=True)
for ruta in plantillas:
    get_template(ruta.split("templates/", 1)[1])
print("templates OK")
