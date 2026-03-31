from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0003_enrollment_discount'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='id_card_front',
            field=models.ImageField(blank=True, null=True, upload_to='profiles/students/id_cards/', verbose_name="Carte d'identité - recto"),
        ),
        migrations.AddField(
            model_name='student',
            name='id_card_back',
            field=models.ImageField(blank=True, null=True, upload_to='profiles/students/id_cards/', verbose_name="Carte d'identité - verso"),
        ),
    ]
