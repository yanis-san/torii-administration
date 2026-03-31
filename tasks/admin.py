from django.contrib import admin
from .models import Task, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'description', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    ordering = ['name']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'priority', 'category', 'assigned_to', 'scheduled_date', 'deadline', 'is_completed', 'get_related_person_display', 'created_at', 'created_by']
    list_filter = ['is_completed', 'priority', 'category', 'assigned_to', 'scheduled_date', 'deadline', 'created_at']
    search_fields = ['title', 'description', 'external_person_name', 'external_person_phone']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'completed_at']
    
    fieldsets = (
        ('Informations de la tâche', {
            'fields': ('title', 'description', 'priority', 'category', 'assigned_to', 'scheduled_date', 'deadline', 'is_completed', 'completed_at')
        }),
        ('Personne associée', {
            'fields': ('student', 'prospect', 'external_person_name', 'external_person_phone')
        }),
        ('Notes et création', {
            'fields': ('notes', 'created_by', 'created_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si c'est une nouvelle tâche
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
