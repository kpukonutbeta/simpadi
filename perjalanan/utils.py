import re
from django.db.models import Max
from .models import PerjalananDinas

def get_next_spd_number(suffix):
    """
    Mencari nomor terakhir dengan suffix tertentu dan mengembalikan angka selanjutnya.
    Contoh: Jika terakhir adalah 123/KPU/2026, maka akan mengembalikan 124.
    """
    if not suffix.startswith('/'):
        suffix = '/' + suffix
        
    last_spd = PerjalananDinas.objects.filter(nomor_spd__endswith=suffix).order_by('-nomor_spd').first()
    
    if last_spd and last_spd.nomor_spd:
        # Mencari angka di awal string (sebelum slash pertama)
        match = re.match(r'^(\d+)', last_spd.nomor_spd)
        if match:
            return int(match.group(1)) + 1
            
    # Jika belum ada sama sekali, mulai dari 1
    return 1

def generate_full_spd_number(number, suffix):
    if not suffix.startswith('/'):
        suffix = '/' + suffix
    return f"{number}{suffix}"
