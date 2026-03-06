# Configuration file for the Sphinx documentation builder.

import os
import sys
from pathlib import Path

#Rutas del proyecto
ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "HealthAndHouse"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(APP))

# Configurar el entorno Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "HealthAndHouse.settings")

import django
django.setup()

#Información del proyecto
project = "HealthAndHouse"
author = "William"
release = "1.0"

#Extensiones Sphinx
extensions = [
    "sphinx.ext.autodoc",       # Documenta clases y funciones automáticamente
    "sphinx.ext.autosummary",   # Genera resúmenes automáticos
    "sphinx.ext.napoleon",      # Soporta docstrings estilo Google y NumPy
    "sphinx.ext.viewcode",      # Enlaza el código fuente
]

# Generar automáticamente las páginas de resumen
autosummary_generate = True

# Mostrar anotaciones de tipo dentro de la descripción
autodoc_typehints = "description"

# Opciones por defecto para autodoc
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}

# Evitar documentar migraciones o tests
exclude_patterns = ["**/migrations/**", "**/tests/**"]

#Configuración HTML
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
language = "es"

#PDF (LaTeX)

latex_engine = 'xelatex'
latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '11pt',
    'preamble': r'''
\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
''',
}
