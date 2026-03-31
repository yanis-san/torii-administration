# finance/admin.py
from django.contrib import admin
from .models import Tariff, Payment, Installment, Discount, TeacherPayment, TeacherCohortPayment

@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount')
    search_fields = ('name',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'amount', 'method', 'date', 'recorded_by')
    list_filter = ('method', 'date')
    search_fields = ('enrollment__student__last_name', 'transaction_id')

@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'due_date', 'amount', 'is_paid')
    list_filter = ('is_paid', 'due_date')
    list_editable = ('is_paid',) # Pour marquer payé rapidement depuis la liste

@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'type', 'is_active')
    list_filter = ('type', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('name',)

@admin.register(TeacherPayment)
class TeacherPaymentAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'payment_date', 'period_start', 'period_end', 'total_amount', 'payment_method', 'recorded_by')
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('teacher__first_name', 'teacher__last_name', 'proof_reference')
    date_hierarchy = 'payment_date'
    raw_id_fields = ('teacher', 'recorded_by')

@admin.register(TeacherCohortPayment)
class TeacherCohortPaymentAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'cohort', 'period_display', 'amount_due_display', 'amount_paid_display', 'balance_display', 'payment_method', 'is_fully_paid')
    list_filter = ('payment_method', 'payment_date', 'cohort')
    search_fields = ('teacher__first_name', 'teacher__last_name', 'cohort__name', 'notes')
    date_hierarchy = 'payment_date'
    raw_id_fields = ('teacher', 'cohort', 'recorded_by')
    readonly_fields = ('balance_due', 'is_fully_paid')
    fieldsets = (
        ('Informations', {
            'fields': ('teacher', 'cohort', 'period_start', 'period_end')
        }),
        ('Montants', {
            'fields': ('amount_due', 'amount_paid', 'balance_due', 'is_fully_paid')
        }),
        ('Paiement', {
            'fields': ('payment_date', 'payment_method', 'notes')
        }),
        ('Suivi', {
            'fields': ('recorded_by',)
        })
    )

    def period_display(self, obj):
        return f"{obj.period_start.strftime('%d/%m/%y')} - {obj.period_end.strftime('%d/%m/%y')}"
    period_display.short_description = 'Période'

    def amount_due_display(self, obj):
        return f"{obj.amount_due:.0f} DA"
    amount_due_display.short_description = 'Montant Dû'

    def amount_paid_display(self, obj):
        return f"{obj.amount_paid:.0f} DA"
    amount_paid_display.short_description = 'Montant Payé'

    def balance_display(self, obj):
        return f"{obj.balance_due:.0f} DA"
    balance_display.short_description = 'Reste'