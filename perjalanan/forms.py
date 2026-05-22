from django import forms
from django.forms import inlineformset_factory
from .models import PerjalananDinas, BiayaPerjalanan, BerkasPerjalanan

class PerjalananDinasForm(forms.ModelForm):
    class Meta:
        model = PerjalananDinas
        fields = []
        widgets = {}

    def __init__(self, *args, **kwargs):
        kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

class BiayaPerjalananForm(forms.ModelForm):
    class Meta:
        model = BiayaPerjalanan
        fields = []

BiayaPerjalananFormSet = inlineformset_factory(
    PerjalananDinas, BiayaPerjalanan,
    form=BiayaPerjalananForm,
    can_delete=False,
    extra=1,
    max_num=1
)

class BerkasPerjalananForm(forms.ModelForm):
    class Meta:
        model = BerkasPerjalanan
        fields = ['jenis_berkas', 'nominal', 'keterangan', 'file', 'malam_menginap']
        widgets = {
            'jenis_berkas': forms.Select(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'nominal': forms.NumberInput(attrs={'class': 'form-control nominal-input-field', 'placeholder': 'Rp 0', 'min': '0'}),
            'keterangan': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Keterangan tambahan (opsional)'}),
            'malam_menginap': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Jml Hari', 'min': '1'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['malam_menginap'].initial = 1

from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError

class BaseBerkasPerjalananFormSet(BaseInlineFormSet):
    def get_queryset(self):
        return super().get_queryset().filter(jenis_berkas__isnull=False)

    def clean(self):
        super().clean()
        
        total_malam_hotel = 0
        total_malam_lumpsum = 0
        total_malam_fb_luar = 0
        total_malam_fb_dalam = 0
        
        parent = self.instance
        durasi = parent.durasi_hari
        total_malam_perjalanan = max(0, durasi - 1)
        
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            if not form.is_valid():
                continue
                
            jenis_berkas = form.cleaned_data.get('jenis_berkas')
            if jenis_berkas:
                kategori = jenis_berkas.kategori_biaya
                if kategori in ['penginapan', 'penginapan_30', 'penginapan_fb_luar', 'penginapan_fb_dalam']:
                    malam = form.cleaned_data.get('malam_menginap') or 1
                    if kategori == 'penginapan':
                        total_malam_hotel += malam
                    elif kategori == 'penginapan_30':
                        total_malam_lumpsum += malam
                    elif kategori == 'penginapan_fb_luar':
                        total_malam_fb_luar += malam
                    elif kategori == 'penginapan_fb_dalam':
                        total_malam_fb_dalam += malam
                        
        total_malam_claimed = total_malam_hotel + total_malam_lumpsum + total_malam_fb_luar + total_malam_fb_dalam
        if total_malam_claimed > total_malam_perjalanan:
            raise ValidationError(
                f"Total klaim penginapan ({total_malam_hotel} malam hotel + {total_malam_lumpsum} malam lumpsum + "
                f"{total_malam_fb_luar} malam FB luar + {total_malam_fb_dalam} malam FB dalam = {total_malam_claimed} malam) "
                f"melebihi batas malam perjalanan ({total_malam_perjalanan} malam)."
            )

BerkasPerjalananFormSet = inlineformset_factory(
    PerjalananDinas, BerkasPerjalanan,
    form=BerkasPerjalananForm,
    formset=BaseBerkasPerjalananFormSet,
    can_delete=True,
    extra=0,
)
