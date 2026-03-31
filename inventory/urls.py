from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Dashboard et listes
    path('', views.inventory_dashboard, name='dashboard'),
    path('items/', views.inventory_list, name='inventory_list'),
    path('shopping-lists/', views.shopping_lists, name='shopping_lists'),
    
    # Détails et actions
    path('shopping-list/<int:list_id>/', views.shopping_list_detail, name='shopping_list_detail'),
    path('api/toggle-purchased/<int:item_id>/', views.toggle_item_purchased, name='toggle_purchased'),
    
    # Export
    path('shopping-list/<int:list_id>/pdf/', views.generate_shopping_list_pdf, name='shopping_list_pdf'),
    path('shopping-list/<int:list_id>/export-text/', views.shopping_list_text_export, name='shopping_list_text_export'),
]
