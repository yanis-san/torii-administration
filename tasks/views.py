from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Task, Category
from students.models import Student
from prospects.models import Prospect
from django.contrib import messages
import calendar
from datetime import datetime, timedelta

User = get_user_model()


@staff_member_required
def task_list(request):
    """
    Vue principale : affiche toutes les tâches actives
    """
    # Filtrer les tâches selon le statut
    filter_status = request.GET.get('status', 'active')
    search_query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')
    
    if filter_status == 'completed':
        tasks = Task.objects.filter(is_completed=True)
    else:
        tasks = Task.objects.filter(is_completed=False)
    
    # Filtre par catégorie
    if category_filter:
        tasks = tasks.filter(category__id=category_filter)
    
    # Recherche
    if search_query:
        tasks = tasks.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(external_person_name__icontains=search_query) |
            Q(external_person_phone__icontains=search_query) |
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(prospect__first_name__icontains=search_query) |
            Q(prospect__last_name__icontains=search_query)
        )
    
    # Trier par priorité puis par deadline
    tasks = tasks.order_by('-priority', 'deadline', '-created_at')
    
    context = {
        'tasks': tasks,
        'filter_status': filter_status,
        'search_query': search_query,
        'category_filter': category_filter,
        'categories': Category.objects.all(),
        'active_count': Task.objects.filter(is_completed=False).count(),
        'completed_count': Task.objects.filter(is_completed=True).count(),
    }
    
    # Si requête HTMX, retourner la section entière avec filtres + liste
    if request.headers.get('HX-Request'):
        return render(request, 'tasks/_tasks_section.html', context)
    
    return render(request, 'tasks/task_list.html', context)


@staff_member_required
def task_create(request):
    """
    Créer une nouvelle tâche
    """
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        priority = request.POST.get('priority', 'MEDIUM')
        scheduled_date = request.POST.get('scheduled_date') or None
        deadline = request.POST.get('deadline') or None
        notes = request.POST.get('notes', '')
        
        # Récupération de la personne liée
        person_type = request.POST.get('person_type')  # 'student', 'prospect', 'external', 'none'
        person_id = request.POST.get('person_id')
        phone_number = request.POST.get('phone_number', '')
        external_name = request.POST.get('external_name', '')
        category_id = request.POST.get('category', '')
        assigned_to_id = request.POST.get('assigned_to', '')
        
        # Créer la tâche (par défaut assignée à l'utilisateur connecté)
        task = Task.objects.create(
            title=title,
            description=description,
            priority=priority,
            scheduled_date=scheduled_date,
            deadline=deadline,
            notes=notes,
            created_by=request.user,
            assigned_to_id=assigned_to_id if assigned_to_id else request.user.id,
            category_id=category_id if category_id else None
        )
        
        # Lier à une personne si spécifié
        if person_type == 'student' and person_id:
            task.student = Student.objects.get(id=person_id)
            task.save()
        elif person_type == 'prospect' and person_id:
            task.prospect = Prospect.objects.get(id=person_id)
            task.save()
        elif person_type == 'external':
            # Si seulement un numéro est fourni, créer un prospect "Unknown"
            if phone_number and not external_name:
                # Vérifier si un prospect avec ce numéro existe déjà
                existing_prospect = Prospect.objects.filter(phone=phone_number).first()
                if existing_prospect:
                    task.prospect = existing_prospect
                else:
                    # Créer un nouveau prospect avec nom "Unknown"
                    new_prospect = Prospect.objects.create(
                        first_name="Unknown",
                        last_name="",
                        phone=phone_number,
                        source="TASK_AUTO"
                    )
                    task.prospect = new_prospect
                task.save()
            else:
                # Stocker comme personne externe
                task.external_person_name = external_name
                task.external_person_phone = phone_number
                task.save()
        
        messages.success(request, f"✅ Tâche '{title}' créée avec succès!")
        
        # Si requête HTMX, retourner la liste mise à jour
        if request.headers.get('HX-Request'):
            return redirect('tasks:list')
        
        return redirect('tasks:list')
    
    # GET - Afficher le formulaire
    # Récupérer la date planifiée depuis l'URL si présente
    initial_scheduled_date = request.GET.get('scheduled_date', '')
    
    context = {
        'students': Student.objects.all().order_by('last_name', 'first_name'),
        'prospects': Prospect.objects.all().order_by('last_name', 'first_name'),
        'categories': Category.objects.all().order_by('name'),
        'users': User.objects.filter(is_active=True).order_by('username'),
        'current_user': request.user,
        'initial_scheduled_date': initial_scheduled_date,
    }
    
    return render(request, 'tasks/task_create.html', context)


@staff_member_required
def task_toggle_complete(request, task_id):
    """
    Marquer une tâche comme terminée/non terminée (HTMX)
    """
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        
        if task.is_completed:
            task.mark_incomplete()
            messages.success(request, f"Tâche '{task.title}' marquée comme non terminée.")
        else:
            task.mark_completed()
            messages.success(request, f"✅ Tâche '{task.title}' terminée!")
        
        # Retourner la liste mise à jour
        if request.headers.get('HX-Request'):
            # Récupérer le contexte actualisé
            filter_status = request.GET.get('status', 'active')
            search_query = request.GET.get('q', '')
            category_filter = request.GET.get('category', '')
            
            if filter_status == 'completed':
                tasks = Task.objects.filter(is_completed=True)
            else:
                tasks = Task.objects.filter(is_completed=False)
            
            if search_query:
                tasks = tasks.filter(
                    Q(title__icontains=search_query) |
                    Q(description__icontains=search_query) |
                    Q(external_person_name__icontains=search_query) |
                    Q(external_person_phone__icontains=search_query) |
                    Q(student__first_name__icontains=search_query) |
                    Q(student__last_name__icontains=search_query) |
                    Q(prospect__first_name__icontains=search_query) |
                    Q(prospect__last_name__icontains=search_query)
                )
            
            if category_filter:
                tasks = tasks.filter(category__id=category_filter)
            
            tasks = tasks.order_by('-priority', 'deadline', '-created_at')
            
            context = {
                'tasks': tasks,
                'filter_status': filter_status,
                'search_query': search_query,
                'active_count': Task.objects.filter(is_completed=False).count(),
                'completed_count': Task.objects.filter(is_completed=True).count(),
                'categories': Category.objects.all().order_by('name'),
            }
            
            # Retourner avec les stats (OOB update)
            return render(request, 'tasks/_tasks_with_stats.html', context)
        
        return redirect('tasks:list')
    
    return HttpResponse(status=405)


@staff_member_required
def task_delete(request, task_id):
    """
    Supprimer une tâche
    """
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        title = task.title
        task.delete()
        messages.success(request, f"🗑️ Tâche '{title}' supprimée.")
        
        if request.headers.get('HX-Request'):
            # Récupérer le contexte actualisé
            filter_status = request.GET.get('status', 'active')
            search_query = request.GET.get('q', '')
            category_filter = request.GET.get('category', '')
            
            if filter_status == 'completed':
                tasks = Task.objects.filter(is_completed=True)
            else:
                tasks = Task.objects.filter(is_completed=False)
            
            if search_query:
                tasks = tasks.filter(
                    Q(title__icontains=search_query) |
                    Q(description__icontains=search_query) |
                    Q(external_person_name__icontains=search_query) |
                    Q(external_person_phone__icontains=search_query) |
                    Q(student__first_name__icontains=search_query) |
                    Q(student__last_name__icontains=search_query) |
                    Q(prospect__first_name__icontains=search_query) |
                    Q(prospect__last_name__icontains=search_query)
                )
            
            if category_filter:
                tasks = tasks.filter(category__id=category_filter)
            
            tasks = tasks.order_by('-priority', 'deadline', '-created_at')
            
            context = {
                'tasks': tasks,
                'filter_status': filter_status,
                'search_query': search_query,
                'active_count': Task.objects.filter(is_completed=False).count(),
                'completed_count': Task.objects.filter(is_completed=True).count(),
                'categories': Category.objects.all().order_by('name'),
            }
            
            # Retourner avec les stats (OOB update)
            return render(request, 'tasks/_tasks_with_stats.html', context)
        
        return redirect('tasks:list')
    
    return HttpResponse(status=405)


@staff_member_required
def task_edit(request, task_id):
    """
    Modifier une tâche existante
    """
    task = get_object_or_404(Task, id=task_id)
    
    if request.method == 'POST':
        task.title = request.POST.get('title')
        task.description = request.POST.get('description', '')
        task.priority = request.POST.get('priority', 'MEDIUM')
        task.scheduled_date = request.POST.get('scheduled_date') or None
        task.deadline = request.POST.get('deadline') or None
        task.notes = request.POST.get('notes', '')
        category_id = request.POST.get('category', '')
        task.category_id = category_id if category_id else None
        assigned_to_id = request.POST.get('assigned_to', '')
        task.assigned_to_id = assigned_to_id if assigned_to_id else None
        task.save()
        
        messages.success(request, f"✏️ Tâche '{task.title}' mise à jour!")
        return redirect('tasks:list')
    
    context = {
        'task': task,
        'students': Student.objects.all().order_by('last_name', 'first_name'),
        'prospects': Prospect.objects.all().order_by('last_name', 'first_name'),
        'categories': Category.objects.all().order_by('name'),
        'users': User.objects.filter(is_active=True).order_by('username'),
    }
    
    return render(request, 'tasks/task_edit.html', context)


@staff_member_required
def search_person(request):
    """
    API pour rechercher un étudiant ou prospect (utilisé dans le formulaire)
    Retourne du JSON pour Alpine.js
    """
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # Chercher dans les étudiants
    students = Student.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(phone__icontains=query) |
        Q(email__icontains=query)
    )[:10]
    
    # Chercher dans les prospects
    prospects = Prospect.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(phone__icontains=query) |
        Q(email__icontains=query)
    )[:10]
    
    results = []
    
    for student in students:
        full_name = f"{student.first_name} {student.last_name}".strip()
        results.append({
            'id': student.id,
            'type': 'student',
            'name': full_name,
            'phone': student.phone or '',
            'email': student.email or '',
            'label': f"👤 {full_name} ({student.phone or 'Pas de tél'})"
        })
    
    for prospect in prospects:
        full_name = f"{prospect.first_name} {prospect.last_name}".strip()
        results.append({
            'id': prospect.id,
            'type': 'prospect',
            'name': full_name,
            'phone': prospect.phone or '',
            'email': prospect.email or '',
            'label': f"🎯 {full_name} ({prospect.phone or 'Pas de tél'})"
        })
    
    return JsonResponse({'results': results})


@staff_member_required
def task_calendar(request):
    """
    Vue calendrier des tâches avec navigation par mois
    """
    # Récupérer le mois/année demandé ou utiliser le mois actuel
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # Calculer le mois précédent et suivant
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year
    
    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year
    
    # Créer le calendrier
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    # Récupérer toutes les tâches du mois (deadline ou created_at)
    first_day = datetime(year, month, 1).date()
    if month == 12:
        last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    # Tâches avec deadline dans le mois
    tasks_with_deadline = Task.objects.filter(
        deadline__gte=first_day,
        deadline__lte=last_day
    ).select_related('student', 'prospect', 'category', 'created_by')
    
    # Tâches planifiées dans le mois
    tasks_scheduled = Task.objects.filter(
        scheduled_date__gte=first_day,
        scheduled_date__lte=last_day
    ).select_related('student', 'prospect', 'category', 'created_by')
    
    # Tâches créées dans le mois (sans deadline ni date planifiée)
    tasks_created = Task.objects.filter(
        created_at__date__gte=first_day,
        created_at__date__lte=last_day,
        deadline__isnull=True,
        scheduled_date__isnull=True
    ).select_related('student', 'prospect', 'category', 'created_by')
    
    # Organiser les tâches par date
    tasks_by_date = {}
    
    # Tâches planifiées (priorité 1)
    for task in tasks_scheduled:
        date_key = task.scheduled_date.strftime('%Y-%m-%d')
        if date_key not in tasks_by_date:
            tasks_by_date[date_key] = []
        tasks_by_date[date_key].append({
            'task': task,
            'type': 'scheduled'
        })
    
    # Tâches avec deadline (priorité 2)
    for task in tasks_with_deadline:
        date_key = task.deadline.strftime('%Y-%m-%d')
        if date_key not in tasks_by_date:
            tasks_by_date[date_key] = []
        tasks_by_date[date_key].append({
            'task': task,
            'type': 'deadline'
        })
    
    # Tâches créées (priorité 3)
    for task in tasks_created:
        date_key = task.created_at.date().strftime('%Y-%m-%d')
        if date_key not in tasks_by_date:
            tasks_by_date[date_key] = []
        tasks_by_date[date_key].append({
            'task': task,
            'type': 'created'
        })
    
    # Créer une liste de semaines avec les jours et leurs tâches
    calendar_weeks = []
    for week in cal:
        week_days = []
        for day in week:
            if day == 0:
                week_days.append({'day': 0, 'tasks': []})
            else:
                date_key = f"{year:04d}-{month:02d}-{day:02d}"
                week_days.append({
                    'day': day,
                    'date_str': date_key,
                    'tasks': tasks_by_date.get(date_key, []),
                    'is_today': date_key == today.strftime('%Y-%m-%d')
                })
        calendar_weeks.append(week_days)
    
    # Statistiques
    total_tasks = Task.objects.filter(is_completed=False).count()
    urgent_tasks = Task.objects.filter(is_completed=False, priority='URGENT').count()
    today_tasks = Task.objects.filter(deadline=today).count()
    
    context = {
        'calendar_weeks': calendar_weeks,
        'year': year,
        'month': month,
        'month_name': month_name,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'today': today,
        'total_tasks': total_tasks,
        'urgent_tasks': urgent_tasks,
        'today_tasks': today_tasks,
        'categories': Category.objects.all().order_by('name'),
    }
    
    return render(request, 'tasks/calendar.html', context)


@staff_member_required
def tasks_by_day(request, year, month, day):
    """
    Afficher toutes les tâches d'une date spécifique
    """
    from datetime import date as date_class, timedelta
    
    selected_date = date_class(year, month, day)
    today = timezone.now().date()
    
    # Récupérer toutes les tâches de ce jour (planifiées et deadline uniquement)
    tasks_scheduled = Task.objects.filter(scheduled_date=selected_date).select_related('student', 'prospect', 'category', 'created_by')
    tasks_deadline = Task.objects.filter(deadline=selected_date).exclude(scheduled_date=selected_date).select_related('student', 'prospect', 'category', 'created_by')
    
    # Statistiques pour ce jour
    scheduled_count = tasks_scheduled.count()
    deadline_count = tasks_deadline.count()
    total_tasks = scheduled_count + deadline_count
    
    # Dates de navigation
    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)
    
    context = {
        'date': selected_date,
        'year': year,
        'month': month,
        'day': day,
        'prev_date': prev_date,
        'next_date': next_date,
        'today': today,
        'tasks_scheduled': tasks_scheduled.order_by('-priority', 'created_at'),
        'tasks_deadline': tasks_deadline.order_by('-priority', 'created_at'),
        'scheduled_count': scheduled_count,
        'deadline_count': deadline_count,
        'total_tasks': total_tasks,
        'categories': Category.objects.all().order_by('name'),
    }
    
    return render(request, 'tasks/day_detail.html', context)
