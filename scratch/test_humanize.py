import os
import sys
import django

sys.path.append('/Users/muhakbaryasin/Desktop/master/kpukonut/simpadi')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simpadi_core.settings')
django.setup()

from django.template import Template, Context
from django.utils.translation import activate

activate('id')

t = Template("{% load humanize %}{{ val|intcomma }}")
c = Context({'val': 5225000})
print("Formatted:", t.render(c))
