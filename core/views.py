from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from perjalanan.models import PerjalananDinas, BiayaPerjalanan, SuratTugas
from master_data.models import Anggaran

def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('core:dashboard')
        else:
            return render(request, 'core/login.html', {'error': 'Email atau password salah.'})
            
    return render(request, 'core/login.html')

def logout_view(request):
    logout(request)
    return redirect('core:login')

@login_required
def dashboard(request):
    is_admin = request.user.is_staff
    
    if is_admin:
        # Admin Stats
        total_perjalanan = PerjalananDinas.objects.count()
        total_biaya = BiayaPerjalanan.objects.aggregate(Sum('total_dibayarkan'))['total_dibayarkan__sum'] or 0
        anggaran_stats = Anggaran.objects.aggregate(Sum('pagu'), Sum('sisa_pagu'))
        total_pagu = anggaran_stats['pagu__sum'] or 0
        sisa_pagu = anggaran_stats['sisa_pagu__sum'] or 0
        penyerapan = (total_pagu - sisa_pagu) / total_pagu * 100 if total_pagu > 0 else 0
        recent_perjalanan = PerjalananDinas.objects.select_related('pegawai', 'tujuan_provinsi').order_by('-created_at')[:5]
    else:
        # Pegawai Stats
        try:
            pegawai = request.user.pegawai_profile
            user_perjalanan = PerjalananDinas.objects.filter(pegawai=pegawai)
            total_perjalanan = user_perjalanan.count()
            total_biaya = BiayaPerjalanan.objects.filter(perjalanan__pegawai=pegawai).aggregate(Sum('total_dibayarkan'))['total_dibayarkan__sum'] or 0
            
            # SPDs issued by admin but still in DRAFT status (need filling by pegawai)
            spd_perlu_dilengkapi = user_perjalanan.filter(status=PerjalananDinas.Status.DRAFT)
            
            # Surat Tugas assigned but SPD not yet issued by admin
            st_mendatang = SuratTugas.objects.filter(
                pegawai=pegawai,
                status=SuratTugas.Status.ACTIVE
            ).exclude(perjalanandinas__pegawai=pegawai)
            
            recent_perjalanan = user_perjalanan.order_by('-created_at')[:5]
        except AttributeError:
            total_perjalanan = 0
            total_biaya = 0
            spd_perlu_dilengkapi = []
            st_mendatang = []
            recent_perjalanan = []

    context = {
        'is_admin': is_admin,
        'total_perjalanan': total_perjalanan,
        'total_biaya': total_biaya,
        'recent_perjalanan': recent_perjalanan,
    }
    
    if is_admin:
        context.update({
            'total_pagu': total_pagu,
            'sisa_pagu': sisa_pagu,
            'penyerapan': round(penyerapan, 2),
        })
    else:
        context.update({
            'spd_perlu_dilengkapi': spd_perlu_dilengkapi,
            'st_mendatang': st_mendatang,
        })
        
    return render(request, 'core/dashboard.html', context)
