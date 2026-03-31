"""
Générateur de certificats et attestations pour les étudiants.
- Certificats PNG personnalisés selon la langue (Chinois, Coréen, Japonais)
- Attestations Word générées avec docxtpl
"""
import os
from PIL import Image, ImageDraw, ImageFont
from datetime import date
from typing import Literal
from docxtpl import DocxTemplate

# --- CONFIGURATION DES CHEMINS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(BASE_DIR, 'fonts')
CERT_DIR = os.path.join(BASE_DIR, 'certificate')
ATTESTATION_DIR = os.path.join(BASE_DIR, 'attestation')
ATTESTATION_TEMPLATE = os.path.join(ATTESTATION_DIR, 'attestation.docx')


def get_font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    """Charge une police avec fallback sur la police par défaut."""
    path = os.path.join(FONTS_DIR, filename)
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def detect_language_from_subject(subject_name: str) -> str | None:
    """
    Détecte le code langue à partir du nom du sujet.
    Retourne 'cn', 'kr', 'jp' ou None si non supporté.
    """
    name_lower = subject_name.lower()
    
    if any(x in name_lower for x in ['chinois', 'chinese', 'mandarin', '中文']):
        return 'cn'
    elif any(x in name_lower for x in ['coréen', 'coreen', 'corée', 'coree', 'korean', '한국어']):
        return 'kr'
    elif any(x in name_lower for x in ['japonais', 'japanese', 'japon', '日本語']):
        return 'jp'
    
    return None


def extract_level_number(level_name: str) -> int:
    """
    Extrait le numéro de niveau depuis le nom du niveau.
    Ex: "Niveau 3" -> 3, "Level 1" -> 1, "N2" -> 2
    """
    import re
    numbers = re.findall(r'\d+', level_name)
    if numbers:
        return int(numbers[0])
    return 1  # Défaut


def generate_certificate(
    language: Literal['cn', 'kr', 'jp'],
    student_name: str,
    level_number: int,
    output_dir: str | None = None,
    generation_date: date | None = None
) -> str | None:
    """
    Génère un certificat pour un étudiant.
    
    Args:
        language: Code langue ('cn', 'kr', 'jp')
        student_name: Nom complet de l'étudiant
        level_number: Numéro du niveau (1-6)
        output_dir: Dossier de sortie (optionnel)
        generation_date: Date de génération (optionnel, défaut: aujourd'hui)
    
    Returns:
        Chemin du fichier généré ou None en cas d'erreur
    """
    today = generation_date or date.today()
    
    if output_dir is None:
        output_dir = os.path.join(CERT_DIR, 'generated')
    
    os.makedirs(output_dir, exist_ok=True)

    # --- POLICES GÉNÉRALES ---
    font_latin_name = 'GreatVibes-Regular.ttf'
    font_date_latin = 'TS-Safaa-Medium.otf'
    font_level_en = 'TS-Safaa-Medium.otf'  # Safaa pour le niveau en anglais

    # --- CONFIGURATION PAR LANGUE ---
    config = {
        # === CHINOIS ===
        'cn': {
            'template': 'chinese.png',
            'font_native': 'MaShanZheng-Regular.ttf',
            'level_map': {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六"},
            
            # Options de Style
            'english_stroke_width': 1,
            'native_stroke_width': 1,
            'date_nat_size': 55,
            
            'level_en_txt': f"Level: Chinese Level {level_number}",
            'level_nat_fmt': "级别：中文{}级",
            'date_nat_txt': f"阿尔及尔，{today.year}年 {today.month}月 {today.day}日",
            
            # --- POSITIONS ---
            'y_name': 750,        
            'y_level_en': 1038,
            'y_level_nat': 1098,
            'pos_date': (201, 1210), 
            'color': 'black'
        },
        
        # === CORÉEN ===
        'kr': {
            'template': 'korean.png',
            'font_native': 'NanumMyeongjo-Bold.ttf',
            'level_map': None,
            'english_stroke_width': 1,
            'native_stroke_width': 1,
            'date_nat_size': 40,
            
            'level_en_txt': f"Level: Korean Level {level_number}",
            'level_nat_fmt': f"급수: 한국어 {level_number}급",
            'date_nat_txt': f"알제, {today.year}년 {today.month}월 {today.day}일",
            
            'y_name': 750, 
            'y_level_en': 1065,
            'y_level_nat': 1125,
            'pos_date': (220, 1221),
            'color': 'black'
        },
        
        # === JAPONAIS ===
        'jp': {
            'template': 'japanese.png',
            'font_native': 'YujiSyuku-Regular.ttf',
            'level_map': None,
            'english_stroke_width': 1,
            'native_stroke_width': 1,
            'date_nat_size': 41,
            
            'level_en_txt': f"Level: Japanese Level {level_number}",
            'level_nat_fmt': f"レベル：日本語 {level_number}級",
            'date_nat_txt': f"アルジェ、{today.year}年 {today.month}月 {today.day}日",
            
            'y_name': 750,
            'y_level_en': 1020,
            'y_level_nat': 1075,
            'pos_date': (202, 1196),
            'color': 'black'
        }
    }

    if language not in config:
        return None

    conf = config[language]
    template_path = os.path.join(CERT_DIR, conf['template'])
    
    # --- CHARGEMENT ---
    try:
        img = Image.open(template_path).convert("RGB")
    except FileNotFoundError:
        print(f"❌ Image introuvable : {template_path}")
        return None

    draw = ImageDraw.Draw(img)
    W, H = img.size
    center_x = W / 2

    # --- CHARGEMENT POLICES ---
    font_name = get_font(font_latin_name, 160)     
    font_lvl_en = get_font(font_level_en, 45)      
    font_lvl_nat = get_font(conf['font_native'], 60) 
    font_date_en = get_font(font_date_latin, 42)
    font_date_nat = get_font(conf['font_native'], conf.get('date_nat_size', 40))

    # --- DESSIN ---

    # 1. NOM
    draw.text((center_x, conf['y_name']), student_name, font=font_name, fill="black", anchor="mm")

    # 2. NIVEAU
    draw.text(
        (center_x, conf['y_level_en']), 
        conf['level_en_txt'], 
        font=font_lvl_en, 
        fill="black", 
        anchor="mm",
        stroke_width=conf.get('english_stroke_width', 0),
        stroke_fill="black"
    )
    
    if language == 'cn':
        cn_num = conf['level_map'].get(level_number, str(level_number))
        txt_nat = conf['level_nat_fmt'].format(cn_num)
    else:
        txt_nat = conf['level_nat_fmt']
    
    draw.text(
        (center_x, conf['y_level_nat']), 
        txt_nat, 
        font=font_lvl_nat, 
        fill="black", 
        anchor="mm", 
        stroke_width=conf.get('native_stroke_width', 0),
        stroke_fill="black"
    )

    # 3. DATE
    x_date, y_date_base = conf['pos_date']
    date_en_str = today.strftime("Algiers, %B %d, %Y")
    draw.text((x_date, y_date_base), date_en_str, font=font_date_en, fill="black", anchor="ls")
    
    draw.text(
        (x_date, y_date_base + 55),
        conf['date_nat_txt'], 
        font=font_date_nat, 
        fill="black", 
        anchor="ls",
        stroke_width=conf.get('native_stroke_width', 0),
        stroke_fill="black"
    )

    # --- SAVE ---
    clean_name = student_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    filename = f"certificat_{language}_{clean_name}.png"
    path_out = os.path.join(output_dir, filename)
    
    img.save(path_out)
    return path_out


def generate_attestation(
    student,
    cohort,
    output_dir: str,
    start_date: date,
    end_date: date
) -> str | None:
    """
    Génère une attestation Word pour un étudiant.
    
    Args:
        student: Instance du modèle Student
        cohort: Instance du modèle Cohort
        output_dir: Dossier de sortie
        start_date: Date de début (première séance)
        end_date: Date de fin (dernière séance)
    
    Returns:
        Chemin du fichier généré ou None en cas d'erreur
    """
    if not os.path.exists(ATTESTATION_TEMPLATE):
        print(f"❌ Template attestation introuvable: {ATTESTATION_TEMPLATE}")
        return None
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Déterminer Mr ou Mme selon le sexe
    if student.sex == 'F':
        ms_or_mr = "Mme"
    else:
        ms_or_mr = "Mr"
    
    # Nom complet
    full_name = f"{student.first_name} {student.last_name}"
    
    # Formater les dates (ex: "du 15 janvier 2026 au 10 février 2026")
    from datetime import datetime as dt, date as date_type
    
    # Debug: afficher le type des dates reçues
    print(f"DEBUG start_date: {start_date} (type: {type(start_date)})")
    print(f"DEBUG end_date: {end_date} (type: {type(end_date)})")
    
    # Conversion robuste des dates
    def ensure_date(d):
        if d is None:
            return date_type.today()
        if hasattr(d, 'month'):
            # C'est déjà un objet date-like
            if hasattr(d, 'date'):
                return d.date()  # datetime -> date
            return d
        # Sinon c'est une string
        try:
            return dt.strptime(str(d), '%Y-%m-%d').date()
        except:
            return date_type.today()
    
    start_date = ensure_date(start_date)
    end_date = ensure_date(end_date)
    
    # Sujet en anglais
    subject_translations = {
        'chinois': 'Chinese',
        'mandarin': 'Chinese',
        'japonais': 'Japanese',
        'coréen': 'Korean',
        'coreen': 'Korean',
    }
    subject_name_lower = cohort.subject.name.lower()
    subject_name = subject_translations.get(subject_name_lower, cohort.subject.name)
    
    # Niveau en anglais (Niveau 1 -> Level 1, etc.)
    level_name_raw = cohort.level.name
    import re
    level_match = re.search(r'(\d+)', level_name_raw)
    if level_match:
        level_name = f"Level {level_match.group(1)}"
    else:
        # Fallback: remplacer "Niveau" par "Level"
        level_name = level_name_raw.replace('Niveau', 'Level').replace('niveau', 'Level')
    
    # Mois en anglais pour l'attestation
    months_en = {
        1: 'January', 2: 'February', 3: 'March', 4: 'April', 
        5: 'May', 6: 'June', 7: 'July', 8: 'August',
        9: 'September', 10: 'October', 11: 'November', 12: 'December'
    }
    
    # Titre en anglais (Ms pour femme, Mr pour homme)
    title_en = 'Ms' if ms_or_mr == 'Mme' else 'Mr'
    
    # Structure date attendue par le template:
    # date.month.begin, date.day.begin, date.year.begin
    # date.month.end, date.day.end, date.year.end
    # date.today
    from datetime import date as date_type
    today = date_type.today()
    date_context = {
        'month': {
            'begin': months_en[start_date.month],
            'end': months_en[end_date.month],
        },
        'day': {
            'begin': start_date.day,
            'end': end_date.day,
        },
        'year': {
            'begin': start_date.year,
            'end': end_date.year,
        },
        'today': f"{months_en[today.month]} {today.day}, {today.year}",
    }
    
    # Contexte pour le template
    context = {
        'MsorMr': title_en,
        'full_name': full_name,
        'subject': subject_name,
        'level': level_name,
        'date': date_context,
    }
    
    print(f"DEBUG context: MsorMr={title_en}, full_name={full_name}, subject={subject_name}")
    
    try:
        # Charger et rendre le template
        tpl = DocxTemplate(ATTESTATION_TEMPLATE)
        tpl.render(context)
        
        # Sauvegarder
        clean_name = full_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        filename = f"attestation_{clean_name}.docx"
        path_out = os.path.join(output_dir, filename)
        tpl.save(path_out)
        
        return path_out
    except Exception as e:
        import traceback
        print(f"❌ Erreur génération attestation: {e}")
        traceback.print_exc()
        return None


def generate_documents_for_cohort(cohort, min_attendance_ratio: float = 0.5) -> dict:
    """
    Génère les certificats ET attestations pour tous les étudiants éligibles d'un cohort.
    
    Critères d'éligibilité:
    - Présent à plus de 50% des séances VALIDÉES (status='COMPLETED')
    - Le cohort doit être dans une langue supportée (Chinois, Coréen, Japonais)
    
    Args:
        cohort: Instance du modèle Cohort
        min_attendance_ratio: Ratio minimum de présence (défaut: 0.5 = 50%)
    
    Returns:
        dict avec:
            - 'output_dir': Dossier de sortie principal
            - 'generated': Liste des documents générés [(student, cert_path, attest_path, presences, total), ...]
            - 'skipped': Liste des étudiants non éligibles [(student, reason), ...]
            - 'language': Code langue détecté
            - 'level': Numéro du niveau
            - 'total_sessions': Nombre total de séances validées
            - 'start_date': Date de la première séance
            - 'end_date': Date de la dernière séance
    """
    from students.models import Enrollment, Attendance
    from academics.models import CourseSession
    
    result = {
        'output_dir': None,
        'generated': [],
        'skipped': [],
        'language': None,
        'level': None,
        'total_sessions': 0,
        'cohort_name': cohort.name,
        'cohort_abbreviation': cohort.abbreviation,
        'start_date': None,
        'end_date': None,
    }
    
    # Détecter la langue
    language = detect_language_from_subject(cohort.subject.name)
    if not language:
        result['skipped'].append((None, f"Langue non supportée: {cohort.subject.name}"))
        return result
    
    result['language'] = language
    
    # Extraire le niveau
    level_number = extract_level_number(cohort.level.name)
    result['level'] = level_number
    
    # Compter les séances validées (COMPLETED)
    completed_sessions = CourseSession.objects.filter(
        cohort=cohort,
        status='COMPLETED'
    ).order_by('date')
    
    total_sessions = completed_sessions.count()
    result['total_sessions'] = total_sessions
    
    if total_sessions == 0:
        result['skipped'].append((None, "Aucune séance validée (COMPLETED)"))
        return result
    
    # Récupérer les dates de début et fin (première et dernière séance)
    first_session = completed_sessions.first()
    last_session = completed_sessions.last()
    result['start_date'] = first_session.date
    result['end_date'] = last_session.date
    
    # Seuil minimum de présences requises
    min_presences = int(total_sessions * min_attendance_ratio)
    if min_presences == 0:
        min_presences = 1  # Au moins 1 présence requise
    
    # Créer le dossier de sortie par cohort
    safe_cohort_name = cohort.abbreviation or f"cohort_{cohort.id}"
    output_dir = os.path.join(CERT_DIR, 'generated', safe_cohort_name)
    os.makedirs(output_dir, exist_ok=True)
    result['output_dir'] = output_dir
    
    # Récupérer tous les étudiants inscrits et actifs
    enrollments = Enrollment.objects.filter(
        cohort=cohort,
        is_active=True
    ).select_related('student')
    
    for enrollment in enrollments:
        student = enrollment.student
        
        # Compter les présences (PRESENT ou LATE)
        presences_count = Attendance.objects.filter(
            enrollment=enrollment,
            session__in=completed_sessions,
            status__in=['PRESENT', 'LATE']
        ).count()
        
        attendance_ratio = presences_count / total_sessions if total_sessions > 0 else 0
        
        if presences_count < min_presences:
            reason = f"Présences insuffisantes: {presences_count}/{total_sessions} ({attendance_ratio*100:.1f}% < {min_attendance_ratio*100:.0f}%)"
            result['skipped'].append((student, reason))
            continue
        
        # Créer un sous-dossier pour cet étudiant
        student_folder_name = f"{student.first_name}_{student.last_name}".replace(' ', '_').replace('/', '_').replace('\\', '_')
        student_output_dir = os.path.join(output_dir, student_folder_name)
        os.makedirs(student_output_dir, exist_ok=True)
        
        # Générer le certificat PNG
        student_full_name = f"{student.first_name} {student.last_name}"
        cert_path = generate_certificate(
            language=language,
            student_name=student_full_name,
            level_number=level_number,
            output_dir=student_output_dir
        )
        
        # Générer l'attestation Word
        attest_path = generate_attestation(
            student=student,
            cohort=cohort,
            output_dir=student_output_dir,
            start_date=result['start_date'],
            end_date=result['end_date']
        )
        
        if cert_path or attest_path:
            result['generated'].append((student, cert_path, attest_path, presences_count, total_sessions))
        else:
            result['skipped'].append((student, "Erreur lors de la génération des documents"))
    
    return result


# Fonction de compatibilité (alias)
def generate_certificates_for_cohort(cohort, min_attendance_ratio: float = 0.5) -> dict:
    """Alias pour generate_documents_for_cohort pour compatibilité."""
    return generate_documents_for_cohort(cohort, min_attendance_ratio)
