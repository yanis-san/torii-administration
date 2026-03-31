from django.contrib import admin
from .models import CashCategory, CashTransaction


@admin.register(CashCategory)
class CashCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'current_amount', 'last_reset', 'created_at')
    search_fields = ('name',)


@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    list_display = ('category', 'transaction_type', 'amount', 'amount_before', 'amount_after', 'created_at', 'created_by')
    list_filter = ('category', 'transaction_type', 'created_at')
    search_fields = ('note',)
    readonly_fields = ('amount_before', 'amount_after', 'created_at')
