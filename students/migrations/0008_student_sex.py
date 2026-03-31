from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0007_backfill_contract_codes'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='sex',
            field=models.CharField(blank=True, choices=[('H', 'Homme'), ('F', 'Femme')], default='', max_length=1, verbose_name='Sexe'),
        ),
    ]
