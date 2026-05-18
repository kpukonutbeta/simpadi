from django.contrib import admin
from .models import User, GlobalConfig

admin.site.register(User)
admin.site.register(GlobalConfig)
