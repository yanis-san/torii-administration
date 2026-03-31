from django.db import migrations, models
import datetime

def backfill_planned(apps, schema_editor):
    CourseSession = apps.get_model('academics', 'CourseSession')
    for session in CourseSession.objects.all():
        if session.planned_duration_minutes is None:
            start_dt = datetime.datetime.combine(datetime.date.today(), session.start_time)
            end_dt = datetime.datetime.combine(datetime.date.today(), session.end_time)
            minutes = int((end_dt - start_dt).total_seconds() // 60)
            if minutes < 0:
                minutes = 0
            session.planned_duration_minutes = minutes
            session.save(update_fields=['planned_duration_minutes'])

class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0008_ramadan_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='cohort',
            name='ramadan_end_time',
            field=models.TimeField(blank=True, help_text='Heure de fin pendant le Ramadan (optionnel)', null=True),
        ),
        migrations.AddField(
            model_name='cohort',
            name='ramadan_start_time',
            field=models.TimeField(blank=True, help_text='Heure de début pendant le Ramadan (optionnel)', null=True),
        ),
        migrations.RunPython(backfill_planned, migrations.RunPython.noop),
    ]
