from django.urls import path
from . import views

app_name = 'cash'

urlpatterns = [
    path('', views.cash_dashboard, name='dashboard'),
    path('create/', views.create_category, name='create_category'),
    path('category/<int:pk>/', views.category_detail, name='category_detail'),
    path('category/<int:pk>/transaction/', views.add_transaction, name='add_transaction'),
    path('category/<int:pk>/reset/', views.reset_category, name='reset_category'),
    path('category/<int:pk>/custom-reset/', views.custom_reset, name='custom_reset'),
    path('category/<int:pk>/delete/', views.delete_category, name='delete_category'),
    path('category/<int:pk>/export-pdf/', views.export_transactions_pdf, name='export_transactions_pdf'),
    path('transaction/<int:transaction_id>/cancel/', views.cancel_transaction, name='cancel_transaction'),
]
