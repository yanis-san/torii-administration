# students/admin.py
from django.contrib import admin
from .models import Student, Enrollment, StudentAnnualFee
from core.models import AcademicYear
from django.utils import timezone
from finance.models import Installment, Payment

class InstallmentInline(admin.TabularInline):
    model = Installment
    extra = 1
    fields = ('due_date', 'amount', 'is_paid', 'payment')
    # Permettre la création/modification d'échéances directement depuis l'inscription
    readonly_fields = ()
    can_delete = True
    show_change_link = True
    classes = ['collapse'] # Replié par défaut pour gagner de la place

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    classes = ['collapse']

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'phone', 'phone_2', 'email', 'student_code', 'registration_fee_paid_current')
    search_fields = ('last_name', 'first_name', 'phone', 'student_code')
    actions = ['mark_registration_fee_paid']

    class AnnualFeeInline(admin.TabularInline):
        model = StudentAnnualFee
        extra = 0
        fields = ('academic_year', 'amount', 'is_paid', 'paid_at', 'note')

    inlines = [AnnualFeeInline]

    @admin.display(boolean=True, description="Frais (Année Active)")
    def registration_fee_paid_current(self, obj: Student):
        year = AcademicYear.get_current()
        return obj.has_paid_registration_fee(year)

    def mark_registration_fee_paid(self, request, queryset):
        current = AcademicYear.get_current()
        if not current:
            self.message_user(request, "Aucune année académique active définie.", level='error')
            return
        created = 0
        updated = 0
        for student in queryset:
            fee, was_created = StudentAnnualFee.objects.get_or_create(student=student, academic_year=current, defaults={'amount': 1000})
            fee.is_paid = True
            fee.paid_at = timezone.now()
            fee.save()
            if was_created:
                created += 1
            else:
                updated += 1
        self.message_user(request, f"Frais marqués comme payés pour {created} créé(s) et {updated} mis à jour.")
    mark_registration_fee_paid.short_description = "Marquer frais d'inscription PAYÉS (année active)"

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'cohort', 'payment_plan', 'tariff', 'balance_due_display', 'is_active')
    list_filter = ('payment_plan', 'is_active', 'cohort')
    search_fields = ('student__last_name', 'student__first_name')
    inlines = [InstallmentInline, PaymentInline] # Tout voir sur une seule page !
    
    def balance_due_display(self, obj):
        # Affiche le reste à payer en rouge si > 0
        balance = obj.balance_due
        if balance > 0:
            return f"{balance} DA (Dû)"
        return "Soldé"
    balance_due_display.short_description = "Reste à payer"