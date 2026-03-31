from django.contrib import admin
from .models import EmailCampaign


@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient_type', 'cohort', 'subject', 'total_recipients', 'success_count', 'failure_count', 'sent_at', 'sent_by')
    list_filter = ('recipient_type', 'sent_at', 'sent_by')
    search_fields = ('title', 'subject', 'message')
    readonly_fields = ('sent_at', 'total_recipients', 'success_count', 'failure_count', 'recipient_emails')
    
    fieldsets = (
        ('Campagne', {
            'fields': ('title', 'recipient_type', 'cohort')
        }),
        ('Contenu', {
            'fields': ('subject', 'message', 'attachment')
        }),
        ('Métadonnées', {
            'fields': ('sent_by', 'sent_at')
        }),
        ('Statistiques', {
            'fields': ('total_recipients', 'success_count', 'failure_count', 'recipient_emails')
        }),
    )
