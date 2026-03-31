from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from datetime import datetime
import io

from .models import ItemCategory, InventoryItem, ShoppingList, ShoppingListItem


def is_admin(user):
    """Vérifier si l'utilisateur est admin"""
    return user.is_authenticated and not user.is_teacher


@login_required
@user_passes_test(is_admin)
def inventory_dashboard(request):
    """Dashboard principal d'inventaire"""
    # Statistiques
    total_items = InventoryItem.objects.count()
    out_of_stock = InventoryItem.objects.filter(status='out_of_stock').count()
    low_stock = InventoryItem.objects.filter(status='low_stock').count()
    mandatory_items = InventoryItem.objects.filter(is_mandatory=True).count()
    
    # Items critiques (obligatoires et rupture)
    critical_items = InventoryItem.objects.filter(
        is_mandatory=True,
        status__in=['out_of_stock', 'low_stock']
    ).select_related('category')[:10]
    
    # Listes d'achat récentes
    recent_lists = ShoppingList.objects.select_related('created_by').prefetch_related('items')[:5]
    
    # Articles à surveiller
    low_stock_items = InventoryItem.objects.filter(status='low_stock').select_related('category')[:5]
    
    # Stock normal (ni en rupture, ni faible)
    in_stock = total_items - out_of_stock - low_stock
    
    context = {
        'total_items': total_items,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'in_stock': in_stock,
        'mandatory_items': mandatory_items,
        'critical_items': critical_items,
        'recent_lists': recent_lists,
        'low_stock_items': low_stock_items,
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def inventory_list(request):
    """Liste complète des articles en inventaire"""
    items = InventoryItem.objects.select_related('category').all()
    
    # Filtres
    category_id = request.GET.get('category')
    if category_id:
        items = items.filter(category_id=category_id)
    
    status_filter = request.GET.get('status')
    if status_filter:
        items = items.filter(status=status_filter)
    
    is_mandatory = request.GET.get('mandatory')
    if is_mandatory == 'true':
        items = items.filter(is_mandatory=True)
    
    search = request.GET.get('search')
    if search:
        items = items.filter(Q(name__icontains=search) | Q(description__icontains=search))
    
    # Tri
    sort_by = request.GET.get('sort', '-quantity_current')
    items = items.order_by(sort_by)
    
    categories = ItemCategory.objects.all()
    
    context = {
        'items': items,
        'categories': categories,
        'current_category': category_id,
        'current_status': status_filter,
        'current_mandatory': is_mandatory,
        'current_search': search,
    }
    return render(request, 'inventory/inventory_list.html', context)


@login_required
@user_passes_test(is_admin)
def shopping_lists(request):
    """Liste de toutes les listes d'achat"""
    lists = ShoppingList.objects.select_related('created_by').prefetch_related('items').all()
    
    # Filtres
    status_filter = request.GET.get('status')
    if status_filter:
        lists = lists.filter(status=status_filter)
    
    search = request.GET.get('search')
    if search:
        lists = lists.filter(Q(title__icontains=search) | Q(description__icontains=search))
    
    # Tri
    sort_by = request.GET.get('sort', '-date_created')
    lists = lists.order_by(sort_by)
    
    context = {
        'lists': lists,
        'current_status': status_filter,
        'current_search': search,
    }
    return render(request, 'inventory/shopping_lists.html', context)


@login_required
@user_passes_test(is_admin)
def shopping_list_detail(request, list_id):
    """Détail d'une liste d'achat avec édition"""
    shopping_list = get_object_or_404(ShoppingList, id=list_id)
    items = shopping_list.items.all().select_related('item')
    
    # Statistiques
    total_purchased = items.filter(is_purchased=True).count()
    total_items = items.count()
    remaining_items = total_items - total_purchased
    progress_percentage = int((total_purchased / total_items * 100)) if total_items > 0 else 0
    
    context = {
        'shopping_list': shopping_list,
        'items': items,
        'total_purchased': total_purchased,
        'total_items': total_items,
        'remaining_items': remaining_items,
        'progress_percentage': progress_percentage,
    }
    return render(request, 'inventory/shopping_list_detail.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def toggle_item_purchased(request, item_id):
    """Basculer le statut "acheté" d'un article"""
    item = get_object_or_404(ShoppingListItem, id=item_id)
    item.is_purchased = not item.is_purchased
    if item.is_purchased:
        item.purchase_date = timezone.now().date()
    else:
        item.purchase_date = None
    item.save()
    
    # Mettre à jour le coût total de la liste
    item.shopping_list.update_total_cost()
    
    return JsonResponse({
        'success': True,
        'is_purchased': item.is_purchased,
        'purchase_date': item.purchase_date.strftime('%d/%m/%Y') if item.purchase_date else None
    })


@login_required
@user_passes_test(is_admin)
def generate_shopping_list_pdf(request, list_id):
    """Générer un PDF de la liste d'achat"""
    shopping_list = get_object_or_404(ShoppingList, id=list_id)
    items = shopping_list.items.all()
    
    # Créer le PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    # En-tête
    elements.append(Paragraph(f"📋 {shopping_list.title}", title_style))
    if shopping_list.event_date:
        elements.append(Paragraph(f"<b>Date d'événement:</b> {shopping_list.event_date.strftime('%d/%m/%Y')}", styles['Normal']))
    if shopping_list.description:
        elements.append(Paragraph(f"<b>Description:</b> {shopping_list.description}", styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Tableau
    data = [[
        Paragraph("<b>#</b>", styles['Normal']),
        Paragraph("<b>Article</b>", styles['Normal']),
        Paragraph("<b>Qté</b>", styles['Normal']),
        Paragraph("<b>Unité</b>", styles['Normal']),
        Paragraph("<b>Prix U.</b>", styles['Normal']),
        Paragraph("<b>Total</b>", styles['Normal']),
        Paragraph("<b>✓</b>", styles['Normal']),
        Paragraph("<b>Fournisseur</b>", styles['Normal']),
        Paragraph("<b>Priorité</b>", styles['Normal']),
    ]]
    
    for idx, item in enumerate(items, 1):
        item_name = item.get_item_name()
        unit_price = f"€{item.unit_price:.2f}" if item.unit_price else "-"
        total_price = f"€{item.get_total_price():.2f}" if item.unit_price else "-"
        purchased = "✅" if item.is_purchased else "⬜"
        priority = item.get_priority_display()
        
        data.append([
            str(idx),
            item_name,
            str(item.quantity_needed),
            item.unit,
            unit_price,
            total_price,
            purchased,
            item.supplier or "-",
            priority,
        ])
    
    table = Table(data, colWidths=[0.4*inch, 2.2*inch, 0.6*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.5*inch, 1.5*inch, 1.2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(table)
    
    # Résumé
    elements.append(Spacer(1, 0.3*inch))
    purchased_count = items.filter(is_purchased=True).count()
    elements.append(Paragraph(
        f"<b>Résumé:</b> {purchased_count}/{items.count()} articles achetés | <b>Coût total:</b> €{shopping_list.total_cost:.2f}",
        styles['Normal']
    ))
    
    # Construire le PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Liste_Achat_{shopping_list.title}.pdf"'
    return response


@login_required
@user_passes_test(is_admin)
def shopping_list_text_export(request, list_id):
    """Exporter une liste d'achat en texte pour copier"""
    shopping_list = get_object_or_404(ShoppingList, id=list_id)
    items = shopping_list.items.all()
    
    text = f"📋 {shopping_list.title}\n"
    text += f"{'='*60}\n\n"
    
    if shopping_list.event_date:
        text += f"📅 Date: {shopping_list.event_date.strftime('%d/%m/%Y')}\n"
    text += f"📝 Statut: {shopping_list.get_status_display()}\n"
    text += f"💰 Coût total: €{shopping_list.total_cost:.2f}\n\n"
    
    if shopping_list.description:
        text += f"Description:\n{shopping_list.description}\n\n"
    
    text += "Articles:\n"
    text += "-"*60 + "\n"
    
    for idx, item in enumerate(items, 1):
        item_name = item.get_item_name()
        status = "✅" if item.is_purchased else "⬜"
        unit_price = f"€{item.unit_price:.2f}" if item.unit_price else "-"
        total = f"€{item.get_total_price():.2f}" if item.unit_price else "-"
        
        text += f"{idx}. {status} {item_name}\n"
        text += f"   Qté: {item.quantity_needed} {item.unit} | Prix U.: {unit_price} | Total: {total}\n"
        text += f"   Priorité: {item.get_priority_display()}\n"
        if item.supplier:
            text += f"   Fournisseur: {item.supplier}\n"
        if item.notes:
            text += f"   Notes: {item.notes}\n"
        text += "\n"
    
    text += "-"*60 + "\n"
    text += f"Achetés: {items.filter(is_purchased=True).count()}/{items.count()}\n"
    
    return JsonResponse({
        'success': True,
        'text': text,
        'filename': f"Liste_Achat_{shopping_list.title}.txt"
    })
