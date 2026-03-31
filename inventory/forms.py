from django import forms
from .models import InventoryItem, ShoppingList, ShoppingListItem, ItemCategory


class ItemCategoryForm(forms.ModelForm):
    class Meta:
        model = ItemCategory
        fields = ['name', 'description', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom de la catégorie'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
        }


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['name', 'description', 'category', 'quantity_current', 'quantity_min', 'unit', 'is_mandatory']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom de l\'article'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'quantity_current': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'min': '0'}),
            'quantity_min': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'min': '0'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ex: pcs, kg, liters'}),
            'is_mandatory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ShoppingListForm(forms.ModelForm):
    class Meta:
        model = ShoppingList
        fields = ['title', 'description', 'event_date', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titre de la liste'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description optionnelle'}),
            'event_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class ShoppingListItemForm(forms.ModelForm):
    class Meta:
        model = ShoppingListItem
        fields = ['item', 'custom_item_name', 'quantity_needed', 'unit', 'unit_price', 'priority', 'supplier', 'notes', 'is_purchased']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-control'}),
            'custom_item_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Si article personnalisé'}),
            'quantity_needed': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1', 'min': '0.1', 'step': '0.1'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ex: pcs, kg, liters'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'min': '0', 'step': '0.01'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'supplier': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Fournisseur optionnel'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Notes optionnelles'}),
            'is_purchased': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
