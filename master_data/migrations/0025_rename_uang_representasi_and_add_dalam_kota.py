# Generated manually to split Uang Representasi into two fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('master_data', '0025_alter_standarbiaya_options_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='standarbiaya',
            old_name='uang_representasi',
            new_name='uang_representasi_luar_kota',
        ),
        migrations.AlterField(
            model_name='standarbiaya',
            name='uang_representasi_luar_kota',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='Uang Representasi Luar Kota'),
        ),
        migrations.AddField(
            model_name='standarbiaya',
            name='uang_representasi_dalam_kota',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='Uang Representasi Dalam Kota (> 8 Jam)'),
        ),
    ]
