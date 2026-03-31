# core/schedule_generator.py
"""
Génère un emploi du temps en PDF avec un design professionnel
"""

from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from django.db.models import Q
from academics.models import CourseSession, Cohort
from datetime import date

# Palette de couleurs pour chaque cohort
COLORS = [
    colors.HexColor("#3B82F6"),  # Bleu
    colors.HexColor("#10B981"),  # Vert
    colors.HexColor("#F59E0B"),  # Ambre
    colors.HexColor("#EF4444"),  # Rouge
    colors.HexColor("#8B5CF6"),  # Violet
    colors.HexColor("#EC4899"),  # Rose
    colors.HexColor("#06B6D4"),  # Cyan
    colors.HexColor("#F97316"),  # Orange
    colors.HexColor("#6366F1"),  # Indigo
    colors.HexColor("#14B8A6"),  # Teal
]


def get_cohort_color(cohort_index):
    """Retourne une couleur pour un cohort"""
    return COLORS[cohort_index % len(COLORS)]


def generate_schedule_pdf():
    """
    Génère un emploi du temps en PDF pour les 3 prochains mois
    """
    
    # Récupérer TOUTES les séances de l'année académique (pas juste les 3 prochains mois)
    # Récupérer les séances
    sessions = CourseSession.objects.select_related('cohort', 'teacher', 'classroom').order_by('date', 'start_time')
    
    if not sessions:
        return None
    
    # Créer un buffer PDF
    buffer = BytesIO()
    
    # Calculer la période à partir des sessions
    from django.db.models import Min, Max
    date_stats = sessions.aggregate(min_date=Min('date'), max_date=Max('date'))
    period_start = date_stats['min_date']
    period_end = date_stats['max_date']
    
    # Créer le document avec orientation PORTRAIT
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.8*cm,
        leftMargin=0.8*cm,
        topMargin=1*cm,
        bottomMargin=0.8*cm
    )
    
    # Conteneur pour les éléments
    elements = []
    
    # Titre
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    month_range = f"{period_start.strftime('%d/%m/%Y')} - {period_end.strftime('%d/%m/%Y')}"
    elements.append(Paragraph(f"📅 EMPLOI DU TEMPS - {month_range}", title_style))
    elements.append(Spacer(1, 0.3*cm))
    
    # Grouper les sessions par sujet, puis par enseignant, puis par cohort
    subjects_dict = {}
    for session in sessions:
        subject_id = session.cohort.subject.id
        subject_name = session.cohort.subject.name
        teacher_id = session.teacher.id if session.teacher else 0
        teacher_name = session.teacher.get_full_name() if session.teacher else "Non assigné"
        cohort_id = session.cohort.id
        
        # Créer la structure pour le sujet s'il n'existe pas
        if subject_id not in subjects_dict:
            subjects_dict[subject_id] = {
                'subject_name': subject_name,
                'teachers': {}
            }
        
        # Créer la structure pour l'enseignant s'il n'existe pas
        if teacher_id not in subjects_dict[subject_id]['teachers']:
            subjects_dict[subject_id]['teachers'][teacher_id] = {
                'teacher_name': teacher_name,
                'cohorts': {}
            }
        
        # Créer la structure pour le cohort s'il n'existe pas
        if cohort_id not in subjects_dict[subject_id]['teachers'][teacher_id]['cohorts']:
            subjects_dict[subject_id]['teachers'][teacher_id]['cohorts'][cohort_id] = {
                'cohort': session.cohort,
                'sessions': []
            }
        
        subjects_dict[subject_id]['teachers'][teacher_id]['cohorts'][cohort_id]['sessions'].append(session)
    
    # Trier les sujets alphabétiquement
    sorted_subjects = sorted(subjects_dict.items(), key=lambda x: x[1]['subject_name'])
    
    # Global cohort counter for colors
    global_cohort_idx = 0
    
    # Créer une table pour chaque cohort, groupé par sujet et enseignant
    for subject_idx, (subject_id, subject_data) in enumerate(sorted_subjects):
        subject_name = subject_data['subject_name']
        
        # Ajouter un titre pour le sujet
        subject_title_style = ParagraphStyle(
            'SubjectTitle',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=4,
            spaceBefore=4,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            borderColor=colors.HexColor("#D1D5DB"),
            borderWidth=1,
            borderPadding=8
        )
        elements.append(Spacer(1, 0.2*cm))
        elements.append(Paragraph(f"📚 {subject_name}", subject_title_style))
        elements.append(Spacer(1, 0.1*cm))
        
        # Trier les enseignants par nom
        teachers_dict = subject_data['teachers']
        sorted_teachers = sorted(teachers_dict.items(), key=lambda x: x[1]['teacher_name'])
        
        # Traiter chaque enseignant de ce sujet
        for teacher_idx, (teacher_id, teacher_data) in enumerate(sorted_teachers):
            teacher_name = teacher_data['teacher_name']
            
            # Ajouter un sous-titre pour l'enseignant
            teacher_title_style = ParagraphStyle(
                'TeacherTitle',
                parent=styles['Heading2'],
                fontSize=11,
                textColor=colors.HexColor("#4B5563"),
                spaceAfter=2,
                spaceBefore=2,
                alignment=TA_LEFT,
                fontName='Helvetica-Bold',
                borderColor=colors.HexColor("#E5E7EB"),
                borderWidth=0.5,
                borderPadding=4
            )
            elements.append(Spacer(1, 0.12*cm))
            elements.append(Paragraph(f"👨‍🏫 {teacher_name}", teacher_title_style))
            elements.append(Spacer(1, 0.08*cm))
            
            # Traiter chaque cohort de cet enseignant
            cohorts_dict = teacher_data['cohorts']
            for cohort_idx, (cohort_id, data) in enumerate(cohorts_dict.items()):
                cohort = data['cohort']
                cohort_sessions = data['sessions']
                
                # Couleur du cohort (utiliser l'index global pour maintenir les couleurs cohérentes)
                cohort_color = get_cohort_color(global_cohort_idx)
                global_cohort_idx += 1
                
                # Titre du cohort
                cohort_title = f"🎓 {cohort.abbreviation} - {cohort.name} ({len(cohort_sessions)} séances)"
                cohort_style = ParagraphStyle(
                    'CohortTitle',
                    parent=styles['Heading2'],
                    fontSize=11,
                    textColor=colors.white,
                    spaceAfter=2,
                    spaceBefore=2,
                    alignment=TA_CENTER,
                    fontName='Helvetica-Bold',
                    backgroundColor=cohort_color
                )
                elements.append(Spacer(1, 0.15*cm))
                elements.append(Paragraph(f"<b>{cohort_title}</b>", cohort_style))
                elements.append(Spacer(1, 0.05*cm))
                
                # Créer la table des séances (Format PORTRAIT - colonnes adaptées)
                # PREMIÈRE LIGNE: EN-TÊTE FUSIONNÉ AVEC NOM DU COHORT
                table_data = [
                    [
                        Paragraph(f"<b>{cohort.abbreviation} - {cohort.name}</b>", ParagraphStyle('', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, textColor=colors.white, fontName='Helvetica-Bold', spaceAfter=8, backgroundColor=cohort_color))
                    ]
                ]
                
                # DEUXIÈME LIGNE: EN-TÊTES DES COLONNES
                table_data.append([
                    Paragraph("<b>Date</b>", ParagraphStyle('', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, textColor=colors.white, spaceAfter=8)),
                    Paragraph("<b>Horaire</b>", ParagraphStyle('', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, textColor=colors.white, spaceAfter=8)),
                    Paragraph("<b>Salle</b>", ParagraphStyle('', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, textColor=colors.white, spaceAfter=8)),
                    Paragraph("<b>Professeur</b>", ParagraphStyle('', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, textColor=colors.white, spaceAfter=8)),
                    Paragraph("<b>Statut</b>", ParagraphStyle('', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, textColor=colors.white, spaceAfter=8)),
                ])
                
                # Ajouter les séances
                for session in cohort_sessions:
                    date_str = session.date.strftime('%d/%m')  # Format court
                    day_name = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'][session.date.weekday()]
                    time_str = f"{session.start_time.strftime('%H:%M')} - {session.end_time.strftime('%H:%M')}"
                    room = session.classroom.name if session.classroom else "N/A"
                    teacher_name = session.teacher.first_name if session.teacher else "N/A"
                    status = session.status or "PLANIFIÉE"
                    
                    # Couleur du statut
                    status_color = colors.HexColor("#10B981") if status == "COMPLETED" else colors.HexColor("#F59E0B")
                    
                    # Créer la date avec le jour en gris plus petit
                    date_cell = Paragraph(
                        f"<b>{date_str}</b><br/><font size='7' color='#6B7280'>{day_name}</font>",
                        ParagraphStyle('', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, spaceAfter=10, leading=12)
                    )
                    
                    row = [
                        date_cell,
                        Paragraph(time_str, ParagraphStyle('', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, fontName='Helvetica-Bold', spaceAfter=10)),
                        Paragraph(room, ParagraphStyle('', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, spaceAfter=10)),
                        Paragraph(teacher_name, ParagraphStyle('', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, fontName='Helvetica-Bold', spaceAfter=10)),
                        Paragraph(status, ParagraphStyle('', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, textColor=status_color, fontName='Helvetica-Bold', spaceAfter=10)),
                    ]
                    table_data.append(row)
                
                # Créer la table avec largeurs adaptées au format PORTRAIT
                # Colonne Statut plus large pour éviter le retour à la ligne
                table = Table(table_data, colWidths=[2.0*cm, 2.8*cm, 1.8*cm, 2.2*cm, 2.4*cm])
                
                # Style de la table avec meilleur espacement pour le PORTRAIT
                table.setStyle(TableStyle([
                    # PREMIÈRE LIGNE: EN-TÊTE FUSIONNÉ (NOM DU COHORT)
                    ('SPAN', (0, 0), (-1, 0)),  # Fusionner les 5 colonnes
                    ('BACKGROUND', (0, 0), (-1, 0), cohort_color),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('ROWHEIGHTS', (0, 0), (0, 0), 0.5*cm),
                    
                    # DEUXIÈME LIGNE: EN-TÊTES DES COLONNES
                    ('BACKGROUND', (0, 1), (-1, 1), cohort_color),
                    ('TEXTCOLOR', (0, 1), (-1, 1), colors.whitesmoke),
                    ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 1), (-1, 1), 9),
                    ('ROWHEIGHTS', (0, 1), (-1, 1), 0.4*cm),
                    
                    # DONNÉES (lignes 2+)
                    ('FONTSIZE', (0, 2), (-1, -1), 8),
                    ('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.whitesmoke, colors.white]),
                    
                    # Alignement global
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    
                    # Bordures
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#D1D5DB")),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('ROWHEIGHTS', (0, 2), (-1, -1), 1.2*cm),  # Espacement vertical des lignes
                ]))
                
                elements.append(table)
                elements.append(Spacer(1, 0.3*cm))
    
    # Ajouter pied de page
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.HexColor("#9CA3AF"),
        alignment=TA_CENTER,
        spaceAfter=5
    )
    elements.append(Spacer(1, 0.4*cm))
    elements.append(Paragraph(
        f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} | Institut Torii",
        footer_style
    ))
    
    # Générer le PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer


def generate_weekly_schedule_pdf():
    """
    Génère un emploi du temps HEBDOMADAIRE en PDF
    Format: grille horaire classique
    - LIGNES: créneaux horaires (9h-11h, 11h-13h, etc.)
    - COLONNES: jours (Dimanche à Samedi)
    - CONTENU: Professeur + Cohort pour chaque cours
    """
    
    # Récupérer toutes les séances des 3 prochains mois
    today = date.today()
    end_date = today + timedelta(days=90)
    
    all_sessions = CourseSession.objects.filter(
        date__gte=today,
        date__lte=end_date
    ).select_related('cohort', 'teacher', 'classroom').order_by('date', 'start_time')
    
    if not all_sessions:
        return None
    
    # 1. Récupérer tous les créneaux horaires UNIQUES
    creneaux_set = set()
    for session in all_sessions:
        creneaux_set.add((session.start_time, session.end_time))
    
    creneaux_sorted = sorted(creneaux_set)
    
    # 2. Grouper sessions par jour de la semaine et par créneau
    # Jour: 0=Dimanche, 1=Lundi, ..., 6=Samedi
    # sessions_grille[jour][(start_time, end_time)] = [list of sessions]
    sessions_grille = {}
    for day_idx in range(7):
        sessions_grille[day_idx] = {}
        for creneau in creneaux_sorted:
            sessions_grille[day_idx][creneau] = []
    
    # Remplir la grille
    for session in all_sessions:
        day_of_week = session.date.weekday()  # Python: 0=Lun, ..., 6=Dim
        our_day = (day_of_week + 1) % 7  # Convertir pour avoir 0=Dim
        creneau = (session.start_time, session.end_time)
        sessions_grille[our_day][creneau].append(session)
    
    # Créer un buffer PDF
    buffer = BytesIO()
    
    # Créer le document - landscape
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=0.4*cm,
        leftMargin=0.4*cm,
        topMargin=0.6*cm,
        bottomMargin=0.6*cm
    )
    
    # Conteneur
    elements = []
    
    # Titre
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=11,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=1,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    elements.append(Paragraph(f"📅 EMPLOI DU TEMPS HEBDOMADAIRE", title_style))
    elements.append(Spacer(1, 0.05*cm))
    
    # Noms des jours
    jours = ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
    
    # Créer la table
    # En-tête: Heure | Dimanche | Lundi | Mardi | Mercredi | Jeudi | Vendredi | Samedi
    header_style = ParagraphStyle('', parent=styles['Normal'], alignment=TA_CENTER, fontSize=6, textColor=colors.white, fontName='Helvetica-Bold')
    
    table_data = [
        [Paragraph("<b>Horaire</b>", header_style)] + [Paragraph(f"<b>{jour}</b>", header_style) for jour in jours]
    ]
    
    # Ajouter les lignes de créneaux
    content_style = ParagraphStyle('', parent=styles['Normal'], alignment=TA_CENTER, fontSize=4, fontName='Helvetica')
    
    for creneau_idx, (start_time, end_time) in enumerate(creneaux_sorted):
        time_str = f"{start_time.strftime('%H:%M')}\n{end_time.strftime('%H:%M')}"
        row = [Paragraph(time_str, ParagraphStyle('', parent=styles['Normal'], alignment=TA_CENTER, fontSize=5, fontName='Helvetica-Bold'))]
        
        # Pour chaque jour
        for day_idx in range(7):
            creneau = (start_time, end_time)
            sessions_at_slot = sessions_grille[day_idx][creneau]
            
            if sessions_at_slot:
                # Afficher tous les cours de ce créneau ce jour-là
                course_lines = []
                for session in sessions_at_slot:
                    prof_name = session.teacher.first_name if session.teacher else "?"
                    cohort_abbrev = session.cohort.abbreviation
                    line = f"{prof_name}\n{cohort_abbrev}"
                    course_lines.append(line)
                
                cell_text = "\n---\n".join(course_lines)
                row.append(Paragraph(cell_text, content_style))
            else:
                row.append(Paragraph("", content_style))
        
        table_data.append(row)
    
    # Créer la table
    col_widths = [0.9*cm] + [1.6*cm] * 7  # Heure + 7 jours
    table = Table(table_data, colWidths=col_widths)
    
    # Style
    table.setStyle(TableStyle([
        # En-tête
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3B82F6")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ROWHEIGHTS', (0, 0), (0, 0), 0.3*cm),
        
        # Colonne Heure
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor("#E5E7EB")),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        
        # Contenu
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, 0), 6),
        ('FONTSIZE', (1, 1), (-1, -1), 4),
        
        # Padding minimal
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        
        # Bordures
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ('ROWHEIGHTS', (0, 1), (-1, -1), 1.0*cm),
    ]))
    
    elements.append(table)
    
    # Pied de page
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=4,
        textColor=colors.HexColor("#9CA3AF"),
        alignment=TA_CENTER
    )
    elements.append(Spacer(1, 0.05*cm))
    elements.append(Paragraph(
        f"{datetime.now().strftime('%d/%m/%Y')} | Institut Torii",
        footer_style
    ))
    
    # Générer le PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer

