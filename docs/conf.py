# docs/conf.py
import os
import sys
sys.path.insert(0, os.path.abspath('..'))

os.environ['DJANGO_SETTINGS_MODULE'] = 'app.settings'
import django
django.setup()

project = 'saleor-django-frontend'
copyright = '2026, serhii.kruhlikov@gmail.com'
author = 'serhii.kruhlikov@gmail.com'
version = release = '1'

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon',]
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'en'
locale_dirs = ['locale/']
gettext_compact = False
html_theme_options = {}

master_doc = 'index'
source_suffix = '.rst'

html_theme = 'furo'
html_static_path = ['_static']
