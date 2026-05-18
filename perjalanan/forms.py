from django import forms
from django.forms import inlineformset_factory
from .models import PerjalananDinas, BiayaPerjalanan, BerkasPerjalanan

class PerjalananDinasForm(forms.ModelForm):
    class Meta:
        model = PerjalananDinas
        fields = [
            'tempat_berangkat', 'tempat_tujuan', 'tujuan_provinsi',
            'maksud_perjalanan', 'tanggal_berangkat', 'tanggal_kembali',
            'jenis_perjalanan', 'jenis_transportasi', 'tidak_menginap', 'anggaran', 'tahun_sbm'
        ]
        widgets = {
            'tanggal_berangkat': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'tanggal_kembali': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'tempat_berangkat': forms.TextInput(attrs={'class': 'form-control'}),
            'tempat_tujuan': forms.TextInput(attrs={'class': 'form-control'}),
            'tujuan_provinsi': forms.Select(attrs={'class': 'form-control'}),
            'maksud_perjalanan': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'jenis_perjalanan': forms.Select(attrs={'class': 'form-control'}),
            'jenis_transportasi': forms.Select(attrs={'class': 'form-control'}),
            'tidak_menginap': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'anggaran': forms.Select(attrs={'class': 'form-control'}),
            'tahun_sbm': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Jika bukan admin, nonaktifkan field anggaran
        if user and not user.is_staff:
            if 'anggaran' in self.fields:
                self.fields['anggaran'].disabled = True
                self.fields['anggaran'].required = False
                self.fields['anggaran'].help_text = "Sumber anggaran telah dikunci oleh Admin."

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
        fields = ['jenis_berkas', 'nominal', 'keterangan', 'file']
        widgets = {
            'jenis_berkas': forms.Select(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'nominal': forms.NumberInput(attrs={'class': 'form-control nominal-input-field', 'placeholder': 'Rp 0', 'min': '0'}),
            'keterangan': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Keterangan tambahan (opsional)'}),
        }

BerkasPerjalananFormSet = inlineformset_factory(
    PerjalananDinas, BerkasPerjalanan,
    form=BerkasPerjalananForm,
    can_delete=True,
    extra=0,
)
