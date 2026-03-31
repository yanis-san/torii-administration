from django.db import migrations, models
import datetime


def populate_planned_duration(apps, schema_editor):
    CourseSession = apps.get_model('academics', 'CourseSession')
    for session in CourseSession.objects.all():
        if session.planned_duration_minutes is None:
            # compute from start/end
            start_dt = datetime.datetime.combine(datetime.date.today(), session.start_time)
            end_dt = datetime.datetime.combine(datetime.date.today(), session.end_time)
            minutes = int((end_dt - start_dt).total_seconds() // 60)
            if minutes < 0:
                minutes = 0
            session.planned_duration_minutes = minutes
            session.save(update_fields=['planned_duration_minutes'])


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0007_alter_cohort_academic_year'),
    ]

    operations = [
        migrations.AddField(
            model_name='cohort',
            name='ramadan_start',
            field=models.DateField(blank=True, help_text='Date de début du Ramadan (inclusif)', null=True),
        ),
        migrations.AddField(
            model_name='cohort',
            name='ramadan_end',
            field=models.DateField(blank=True, help_text='Date de fin du Ramadan (inclusif)', null=True),
        ),
        migrations.AddField(
            model_name='cohort',
            name='ramadan_actual_minutes',
            field=models.PositiveIntegerField(blank=True, help_text="Durée réelle d'une séance pendant le Ramadan (en minutes), ex: 90", null=True),
        ),
        migrations.AddField(
            model_name='cohort',
            name='ramadan_teacher_hourly_rate',
            field=models.IntegerField(blank=True, help_text='Tarif horaire spécifique pour le Ramadan. Laisser vide pour garder le tarif standard.', null=True),
        ),
        migrations.AddField(
            model_name='coursesession',
            name='planned_duration_minutes',
            field=models.PositiveIntegerField(blank=True, help_text='Durée planifiée au moment de la création (minutes)', null=True),
        ),
        migrations.RunPython(populate_planned_duration, migrations.RunPython.noop),
    ]
