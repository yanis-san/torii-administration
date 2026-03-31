from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from .models import CashCategory, CashTransaction


def update_total_category():
    """
    Met à jour automatiquement la catégorie TOTAL avec la somme de toutes les autres catégories
    """
    total_category, created = CashCategory.objects.get_or_create(
        name="TOTAL",
        defaults={
            'description': 'Total automatique de toutes les catégories',
            'is_total': True,
            'current_amount': 0
        }
    )
    
    # Si elle existe déjà, s'assurer qu'elle est marquée comme is_total
    if not created and not total_category.is_total:
        total_category.is_total = True
        total_category.save()
    
    # Calculer le total de toutes les autres catégories
    other_categories = CashCategory.objects.filter(is_total=False)
    new_total = sum(cat.current_amount for cat in other_categories)
    
    # Mettre à jour seulement si le montant a changé
    if total_category.current_amount != new_total:
        old_amount = total_category.current_amount
        total_category.current_amount = new_total
        total_category.save()
        
        # Enregistrer une transaction automatique
        CashTransaction.objects.create(
            category=total_category,
            transaction_type='SET',
            amount=new_total,
            note=f"Mise à jour automatique du total",
            created_by=None,  # Système
            amount_before=old_amount,
            amount_after=new_total
        )


def cash_dashboard(request):
    """
    Page principale de gestion de caisse avec toutes les catégories
    """
    # S'assurer que la catégorie TOTAL existe et est à jour
    update_total_category()
    
    categories = CashCategory.objects.all()
    
    # Total général (optionnel)
    total_cash = sum(cat.current_amount for cat in categories.filter(is_total=False))
    
    context = {
        'categories': categories,
        'total_cash': total_cash,
    }
    return render(request, 'cash/dashboard.html', context)


def create_category(request):
    """
    Créer une nouvelle catégorie de caisse
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        initial_amount = int(request.POST.get('initial_amount', 0))
        
        try:
            category = CashCategory.objects.create(
                name=name,
                description=description,
                current_amount=initial_amount
            )
            
            # Enregistrer la transaction initiale si montant > 0
            if initial_amount != 0:
                CashTransaction.objects.create(
                    category=category,
                    transaction_type='SET',
                    amount=initial_amount,
                    note="Montant initial",
                    created_by=request.user,
                    amount_before=0,
                    amount_after=initial_amount
                )
            
            # Mettre à jour le TOTAL
            update_total_category()
            
            messages.success(request, f"Catégorie '{name}' créée avec succès !")
        except Exception as e:
            messages.error(request, f"Erreur : {str(e)}")
        
        return redirect('cash:dashboard')
    
    return render(request, 'cash/create_category.html')


def category_detail(request, pk):
    """
    Détail d'une catégorie avec historique des transactions
    """
    category = get_object_or_404(CashCategory, pk=pk)
    
    # Si c'est la catégorie TOTAL, afficher toutes les transactions de toutes les catégories
    if category.is_total:
        transactions = CashTransaction.objects.all().order_by('-created_at')[:100]  # 100 dernières transactions
    else:
        transactions = category.transactions.all()[:50]  # 50 dernières transactions
    
    context = {
        'category': category,
        'transactions': transactions,
    }
    return render(request, 'cash/category_detail.html', context)


def add_transaction(request, pk):
    """
    Ajouter une transaction (ajout/retrait/définir)
    """
    if request.method != 'POST':
        return redirect('cash:dashboard')
    
    category = get_object_or_404(CashCategory, pk=pk)
    
    # Empêcher les transactions sur la catégorie TOTAL
    if category.is_total:
        messages.error(request, "Impossible d'ajouter une transaction sur la catégorie TOTAL (calculée automatiquement).")
        return redirect('cash:category_detail', pk=pk)
    
    transaction_type = request.POST.get('transaction_type')
    amount = int(request.POST.get('amount', 0))
    note = request.POST.get('note', '')
    
    amount_before = category.current_amount
    
    if transaction_type == 'ADD':
        category.current_amount += amount
    elif transaction_type == 'REMOVE':
        category.current_amount -= amount
    elif transaction_type == 'SET':
        category.current_amount = amount
    
    category.save()
    
    # Enregistrer la transaction
    CashTransaction.objects.create(
        category=category,
        transaction_type=transaction_type,
        amount=amount,
        note=note,
        created_by=request.user,
        amount_before=amount_before,
        amount_after=category.current_amount
    )
    
    # Mettre à jour le TOTAL
    update_total_category()
    
    messages.success(request, f"Transaction enregistrée : {category.name}")
    return redirect('cash:category_detail', pk=pk)


def reset_category(request, pk):
    """
    Remettre une catégorie à 0 et enregistrer la date de reset
    """
    if request.method != 'POST':
        return redirect('cash:dashboard')
    
    category = get_object_or_404(CashCategory, pk=pk)
    
    # Empêcher le reset de la catégorie TOTAL
    if category.is_total:
        messages.error(request, "Impossible de reset la catégorie TOTAL (calculée automatiquement).")
        return redirect('cash:category_detail', pk=pk)
    
    amount_before = category.current_amount
    
    # Reset
    category.current_amount = 0
    category.last_reset = timezone.now()
    category.save()
    
    # Enregistrer la transaction de reset
    CashTransaction.objects.create(
        category=category,
        transaction_type='RESET',
        amount=0,
        note="RESET à 0",
        created_by=request.user,
        amount_before=amount_before,
        amount_after=0
    )
    
    # Mettre à jour le TOTAL
    update_total_category()
    
    messages.success(request, f"Catégorie '{category.name}' remise à 0.")
    return redirect('cash:category_detail', pk=pk)


def delete_category(request, pk):
    """
    Supprimer une catégorie et toutes ses transactions
    """
    if request.method != 'POST':
        return redirect('cash:dashboard')
    
    category = get_object_or_404(CashCategory, pk=pk)
    
    # Empêcher la suppression de la catégorie TOTAL
    if category.is_total:
        messages.error(request, "Impossible de supprimer la catégorie TOTAL (calculée automatiquement).")
        return redirect('cash:dashboard')
    
    category_name = category.name
    category.delete()
    
    # Mettre à jour le TOTAL
    update_total_category()
    
    messages.success(request, f"Catégorie '{category_name}' supprimée.")
    return redirect('cash:dashboard')


def custom_reset(request, pk):
    """
    Reset personnalisé : définir un montant spécifique avec une note
    """
    if request.method != 'POST':
        return redirect('cash:dashboard')
    
    category = get_object_or_404(CashCategory, pk=pk)
    
    # Empêcher le reset de la catégorie TOTAL
    if category.is_total:
        messages.error(request, "Impossible de reset la catégorie TOTAL (calculée automatiquement).")
        return redirect('cash:category_detail', pk=pk)
    
    amount_before = category.current_amount
    
    new_amount = int(request.POST.get('new_amount', 0))
    note = request.POST.get('reset_note', 'Reset personnalisé')
    
    # Définir le nouveau montant
    category.current_amount = new_amount
    category.last_reset = timezone.now()
    category.save()
    
    # Enregistrer la transaction
    CashTransaction.objects.create(
        category=category,
        transaction_type='RESET',
        amount=new_amount,
        note=f"RESET PERSONNALISÉ : {note}",
        created_by=request.user,
        amount_before=amount_before,
        amount_after=new_amount
    )
    
    # Mettre à jour le TOTAL
    update_total_category()
    
    messages.success(request, f"Catégorie '{category.name}' mise à {new_amount:,} DA.".replace(',', ' '))
    return redirect('cash:category_detail', pk=pk)


def cancel_transaction(request, transaction_id):
    """
    Annuler une transaction : inverse l'opération
    """
    if request.method != 'POST':
        return redirect('cash:dashboard')
    
    transaction = get_object_or_404(CashTransaction, id=transaction_id)
    category = transaction.category
    
    # Calculer le montant à inverser
    amount_before = category.current_amount
    
    if transaction.transaction_type == 'ADD':
        # Annuler un ajout = retirer le montant
        category.current_amount -= transaction.amount
    elif transaction.transaction_type == 'REMOVE':
        # Annuler un retrait = rajouter le montant
        category.current_amount += transaction.amount
    elif transaction.transaction_type == 'SET':
        # Annuler un SET = revenir à l'état avant
        category.current_amount = transaction.amount_before
    
    category.save()
    
    # Créer une transaction d'annulation
    CashTransaction.objects.create(
        category=category,
        transaction_type='SET' if transaction.transaction_type == 'SET' else ('REMOVE' if transaction.transaction_type == 'ADD' else 'ADD'),
        amount=transaction.amount,
        note=f"ANNULATION de la transaction du {transaction.created_at.strftime('%d/%m/%Y %H:%M')} : {transaction.note}",
        created_by=request.user,
        amount_before=amount_before,
        amount_after=category.current_amount
    )
    
    # Mettre à jour le TOTAL
    update_total_category()
    
    messages.success(request, f"Transaction annulée. Montant restauré : {category.current_amount:,} DA".replace(',', ' '))
    return redirect('cash:category_detail', pk=category.id)


def export_transactions_pdf(request, pk):
    """
    Exporter l'historique des transactions en PDF
    """
    category = get_object_or_404(CashCategory, pk=pk)
    
    # Récupérer les transactions
    if category.is_total:
        transactions = CashTransaction.objects.all().order_by('-created_at')[:100]
    else:
        transactions = category.transactions.all().order_by('-created_at')[:100]
    
    # Créer le PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="transactions_{category.name}_{timezone.now().strftime("%d-%m-%Y")}.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=A4,
                           rightMargin=1*cm, leftMargin=1*cm,
                           topMargin=1.5*cm, bottomMargin=1.5*cm)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Styles personnalisés
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=18,
        textColor=colors.HexColor('#4F46E5'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.grey,
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    # Titre
    elements.append(Paragraph(f"Historique des Transactions - {category.name}", title_style))
    elements.append(Paragraph(f"Généré le {timezone.now().strftime('%d/%m/%Y à %H:%M')}", header_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Info catégorie
    info_data = [
        ['Catégorie:', category.name],
        ['Montant actuel:', f"{category.current_amount:,} DA".replace(',', ' ')],
        ['Nombre de transactions:', str(transactions.count())],
    ]
    
    if category.last_reset:
        info_data.append(['Dernier reset:', category.last_reset.strftime('%d/%m/%Y à %H:%M')])
    
    info_table = Table(info_data, colWidths=[5*cm, 10*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 1*cm))
    
    # Tableau des transactions
    if transactions:
        # En-têtes
        if category.is_total:
            table_data = [['Date', 'Catégorie', 'Type', 'Montant', 'Avant', 'Après', 'Note']]
        else:
            table_data = [['Date', 'Type', 'Montant', 'Avant', 'Après', 'Note']]
        
        # Lignes de transactions
        for transaction in transactions:
            type_map = {
                'ADD': 'Ajout',
                'REMOVE': 'Retrait',
                'SET': 'Définir',
                'RESET': 'Reset'
            }
            
            montant_str = ""
            if transaction.transaction_type == 'ADD':
                montant_str = f"+{transaction.amount:,}".replace(',', ' ')
            elif transaction.transaction_type == 'REMOVE':
                montant_str = f"-{transaction.amount:,}".replace(',', ' ')
            else:
                montant_str = f"{transaction.amount:,}".replace(',', ' ')
            
            row = [
                transaction.created_at.strftime('%d/%m/%Y\n%H:%M'),
            ]
            
            if category.is_total:
                row.append(transaction.category.name)
            
            row.extend([
                type_map.get(transaction.transaction_type, '?'),
                montant_str + ' DA',
                f"{transaction.amount_before:,} DA".replace(',', ' '),
                f"{transaction.amount_after:,} DA".replace(',', ' '),
                transaction.note[:40] + ('...' if len(transaction.note) > 40 else '')
            ])
            
            table_data.append(row)
        
        # Définir les largeurs de colonnes
        if category.is_total:
            col_widths = [2.5*cm, 2.5*cm, 1.5*cm, 2.2*cm, 2.2*cm, 2.2*cm, 5*cm]
        else:
            col_widths = [2.5*cm, 1.8*cm, 2.2*cm, 2.2*cm, 2.2*cm, 6*cm]
        
        transactions_table = Table(table_data, colWidths=col_widths)
        transactions_table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            
            # Corps du tableau
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Date
            ('ALIGN', (-3, 1), (-2, -1), 'RIGHT'),  # Montants
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(transactions_table)
    else:
        elements.append(Paragraph("Aucune transaction pour cette catégorie.", styles['Normal']))
    
    # Construire le PDF
    doc.build(elements)
    
    return response
