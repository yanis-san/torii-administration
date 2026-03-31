# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, AcademicYear, Classroom, TeacherProfile

class CustomUserAdmin(UserAdmin):
    # On ajoute nos champs personnalisés à l'interface User existante
    fieldsets = UserAdmin.fieldsets + (
        ('Rôles École', {'fields': ('is_teacher', 'is_admin', 'phone')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_teacher', 'is_staff')
    list_filter = ('is_teacher', 'is_staff')

@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('label', 'start_date', 'end_date', 'is_current', 'registration_fee_amount')
    list_editable = ('is_current', 'registration_fee_amount')  # Pour changer l'année active et les frais rapidement

@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'preferred_payment_method', 'bank_details', 'tax_id')
    list_filter = ('preferred_payment_method',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'bank_details', 'tax_id')
    raw_id_fields = ('user',)

admin.site.register(User, CustomUserAdmin)
admin.site.register(Classroom)