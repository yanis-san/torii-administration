from django.contrib import admin
from .models import ItemCategory, InventoryItem, ShoppingList, ShoppingListItem


@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'quantity_current', 'quantity_min', 'status', 'is_mandatory', 'last_updated')
    list_filter = ('category', 'status', 'is_mandatory', 'last_updated')
    search_fields = ('name', 'description', 'location')
    readonly_fields = ('last_updated', 'created_at', 'status')
    fieldsets = (
        ('Information', {
            'fields': ('name', 'category', 'description')
        }),
        ('Quantités', {
            'fields': ('quantity_current', 'quantity_min', 'unit')
        }),
        ('Détails', {
            'fields': ('purchase_price', 'location', 'is_mandatory', 'notes')
        }),
        ('Statut', {
            'fields': ('status', 'last_updated', 'created_at'),
            'classes': ('collapse',)
        }),
    )


class ShoppingListItemInline(admin.TabularInline):
    model = ShoppingListItem
    extra = 1
    fields = ('item', 'custom_item_name', 'quantity_needed', 'unit', 'unit_price', 'is_purchased', 'priority', 'notes')


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'event_date', 'total_cost', 'created_by', 'date_created')
    list_filter = ('status', 'event_date', 'date_created')
    search_fields = ('title', 'description', 'notes')
    readonly_fields = ('total_cost', 'date_created', 'created_by')
    inlines = [ShoppingListItemInline]
    fieldsets = (
        ('Information', {
            'fields': ('title', 'description', 'event_date')
        }),
        ('Statut', {
            'fields': ('status', 'total_cost')
        }),
        ('Tracking', {
            'fields': ('created_by', 'date_created', 'notes'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ShoppingListItem)
class ShoppingListItemAdmin(admin.ModelAdmin):
    list_display = ('get_item_name', 'shopping_list', 'quantity_needed', 'unit_price', 'get_total_price', 'is_purchased', 'priority')
    list_filter = ('shopping_list', 'is_purchased', 'priority', 'created_at')
    search_fields = ('custom_item_name', 'item__name', 'supplier')
    fieldsets = (
        ('Article', {
            'fields': ('shopping_list', 'item', 'custom_item_name')
        }),
        ('Quantité & Prix', {
            'fields': ('quantity_needed', 'unit', 'unit_price')
        }),
        ('Achat', {
            'fields': ('is_purchased', 'purchase_date', 'supplier')
        }),
        ('Détails', {
            'fields': ('priority', 'notes'),
        }),
    )
