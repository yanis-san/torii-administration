from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('academics', '0009_ramadan_times'),
    ]

    operations = [
        migrations.AddField(
            model_name='cohort',
            name='substitute_teachers',
            field=models.ManyToManyField(
                blank=True,
                limit_choices_to={'is_teacher': True},
                related_name='substitute_in_cohorts',
                to='core.user',
                verbose_name='Professeurs Remplaçants Disponibles'
            ),
        ),
    ]
