from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True, verbose_name="Alamat Email")
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Status Operator",
        help_text="Menentukan apakah pengguna dapat masuk ke situs admin/operator."
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

class GlobalConfig(models.Model):
    key = models.CharField(max_length=50, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.key

    class Meta:
        verbose_name = "Pengaturan Global"
        verbose_name_plural = "Pengaturan Global"
