from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0005_studentannualfee'),
    ]

    operations = [
        migrations.AddField(
            model_name='enrollment',
            name='contract_code',
            field=models.CharField(blank=True, null=True, max_length=40, unique=True),
        ),
    ]
