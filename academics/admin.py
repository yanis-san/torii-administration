# academics/admin.py
from django.contrib import admin
from .models import Subject, Level, Cohort, WeeklySchedule, CourseSession

class WeeklyScheduleInline(admin.TabularInline):
    model = WeeklySchedule
    extra = 1 # Affiche une ligne vide par défaut

class CourseSessionInline(admin.TabularInline):
    model = CourseSession
    fields = ('date', 'start_time', 'end_time', 'status', 'teacher', 'classroom', 'teacher_hourly_rate_override')
    readonly_fields = ('date', 'start_time', 'end_time') # Pour éviter les erreurs manuelles ici
    extra = 0
    show_change_link = True # Permet de cliquer pour modifier une séance spécifique
    can_delete = False
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('date')

@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation', 'subject', 'level', 'teacher', 'modality', 'is_individual', 'start_date', 'end_date', 'schedule_generated')
    list_filter = ('academic_year', 'subject', 'level', 'teacher', 'modality', 'is_individual')
    search_fields = ('abbreviation', 'name', 'subject__name')
    inlines = [WeeklyScheduleInline, CourseSessionInline]
    actions = ['force_schedule_generation']
    
    fieldsets = (
        ('ℹ️ Informations Générales', {
            'fields': ('abbreviation', 'subject', 'level', 'teacher', 'academic_year', 'substitute_teachers')
        }),
        ('📅 Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('💰 Tarifs', {
            'fields': ('standard_price', 'teacher_hourly_rate')
        }),
        ('🎯 Modalité & Format', {
            'fields': ('modality', 'is_individual'),
            'description': 'Choisissez la modalité (Présentiel/En ligne) et si le groupe est individuel. Le nom s\'adaptera automatiquement.'
        }),
        ('⚙️ Ramadan (Optionnel)', {
            'fields': ('ramadan_start', 'ramadan_end', 'ramadan_start_time', 'ramadan_end_time', 'ramadan_teacher_hourly_rate'),
            'classes': ('collapse',),
        }),
        ('📊 État', {
            'fields': ('schedule_generated',),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('abbreviation',)

    def force_schedule_generation(self, request, queryset):
        # Action manuelle au cas où
        for cohort in queryset:
            cohort.schedule_generated = True
            cohort.save()
        self.message_user(request, "Génération du planning lancée.")
    force_schedule_generation.short_description = "Générer les séances pour les groupes sélectionnés"

@admin.register(CourseSession)
class CourseSessionAdmin(admin.ModelAdmin):
    list_display = ('date', 'cohort', 'start_time', 'status', 'teacher', 'display_hourly_rate')
    list_filter = ('status', 'date', 'cohort__teacher')
    date_hierarchy = 'date' # Ajoute une navigation par date en haut
    search_fields = ('cohort__name', 'teacher__username')
    
    fieldsets = (
        ('📅 Informations de Séance', {
            'fields': ('cohort', 'date', 'start_time', 'end_time', 'status', 'teacher', 'classroom')
        }),
        ('⏱️ Durée', {
            'fields': ('duration_override_minutes', 'planned_duration_minutes'),
            'classes': ('collapse',),
        }),
        ('💰 Rémunération', {
            'fields': ('teacher_hourly_rate_override',),
            'description': 'Laissez vide pour utiliser le taux du cohort. Remplissez pour surcharger le taux pour cette séance uniquement.',
        }),
        ('📝 Notes', {
            'fields': ('note',),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('planned_duration_minutes',)
    
    def display_hourly_rate(self, obj):
        """Affiche le taux horaire utilisé (override ou défaut)"""
        if obj.teacher_hourly_rate_override:
            return f"🔄 {obj.teacher_hourly_rate_override} DA/h (surcharge)"
        return f"{obj.cohort.teacher_hourly_rate} DA/h"
    display_hourly_rate.short_description = "Taux Horaire"

admin.site.register(Subject)
admin.site.register(Level)