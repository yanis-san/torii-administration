# academics/models.py
from django.db import models
from core.models import User, Classroom, AcademicYear
from datetime import timedelta, date

# ============================================================================
# DICTIONNAIRE CENTRAL DES CODES DE LANGUES/ATELIERS
# Format: 'nom_exact': 'code_abbreviation'
# Facile à étendre : il suffit d'ajouter une nouvelle clé-valeur
# ============================================================================
LANGUAGE_CODES = {
    # Langues principales
    'Chinois': 'CHN',
    'Mandarin': 'CHN',
    'Cantonais': 'CAN',
    'Japonais': 'JPN',
    'Coréen': 'KR',
    'Allemand': 'DEU',
    'Français': 'FRA',
    'Anglais': 'ENG',
    'Espagnol': 'ESP',
    'Portugais': 'PORT',
    'Italien': 'ITA',
    'Russe': 'RUS',
    'Arabe': 'ARA',
    'Turc': 'TUR',
    'Grec': 'GRE',
    'Suédois': 'SWE',
    'Norvégien': 'NOR',
    'Danois': 'DAN',
    'Néerlandais': 'NED',
    'Polonais': 'POL',
    'Roumain': 'ROM',
    'Ukrainien': 'UKR',
    'Vietnamien': 'VIE',
    'Thaï': 'THA',
    'Khmer': 'KHM',
    'Hindi': 'HIN',
    'Bengali': 'BEN',
    'Ourdou': 'URD',
    'Persan': 'PER',
    'Hébreu': 'HEB',
    'Swahili': 'SWA',
    'Indonésien': 'IND',
    'Malais': 'MAL',
    'Tagalog': 'TAG',
    'Coréen': 'KOR',
    # Ateliers et cours spécialisés
    'Calligraphie': 'CALL',
    'Peinture': 'PAINT',
    'Danse': 'DANCE',
    'Musique': 'MUS',
    'Théâtre': 'THEA',
    'Cuisine': 'COOK',
    'Informatique': 'IT',
    'Math': 'MATH',
    'Science': 'SCI',
    'Histoire': 'HIST',
    'Littérature': 'LIT',
}

# Modality mapping (pour plus de flexibilité)
MODALITY_CODES = {
    ('IN_PERSON', False): 'P',       # Présentiel (groupe)
    ('ONLINE', False): 'O',          # Online (groupe)
    ('IN_PERSON', True): 'IP',       # Individuel Présentiel
    ('ONLINE', True): 'IO',          # Individuel Online
}


class Subject(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self): return self.name

class Level(models.Model):
    name = models.CharField(max_length=50)
    def __str__(self): return self.name

class Cohort(models.Model):
    """
    Le Groupe (La Classe).
    """
    name = models.CharField(max_length=150, editable=False, help_text="Généré automatiquement")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    level = models.ForeignKey(Level, on_delete=models.PROTECT)
    
    # Période globale
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name='cohorts',
        null=True,
        blank=True,
        help_text="Par défaut: Année académique active"
    )
    start_date = models.DateField()
    end_date = models.DateField()

    # --- ENSEIGNANTS & PAIE ---
    # Prof Titulaire
    teacher = models.ForeignKey(User, on_delete=models.PROTECT, limit_choices_to={'is_teacher': True}, related_name='assigned_cohorts')
    
    # Prof Suppléant (kept for backward compatibility)
    substitute_teacher = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        limit_choices_to={'is_teacher': True}, 
        related_name='substitute_cohorts', 
        verbose_name="Professeur Suppléant (Legacy)"
    )

    # Profs remplaçants disponibles pour ce cohort (Many-to-Many)
    substitute_teachers = models.ManyToManyField(
        User,
        blank=True,
        limit_choices_to={'is_teacher': True},
        related_name='substitute_in_cohorts',
        verbose_name="Professeurs Remplaçants Disponibles"
    )

    # Tarif Horaire (Pour la paie)
    teacher_hourly_rate = models.IntegerField(
        default=0,
        verbose_name="Tarif Horaire Prof (DA/h)",
        help_text="Tarif appliqué pour chaque heure de cours de ce groupe"
    )

    # --- Ramadan ---
    ramadan_start = models.DateField(null=True, blank=True, help_text="Date de début du Ramadan (inclusif)")
    ramadan_end = models.DateField(null=True, blank=True, help_text="Date de fin du Ramadan (inclusif)")
    ramadan_start_time = models.TimeField(null=True, blank=True, help_text="Heure de début pendant le Ramadan")
    ramadan_end_time = models.TimeField(null=True, blank=True, help_text="Heure de fin pendant le Ramadan")
    ramadan_teacher_hourly_rate = models.IntegerField(
        null=True,
        blank=True,
        help_text="Tarif horaire spécifique pour le Ramadan. Laisser vide pour garder le tarif standard."
    )


    # NOUVEAU : Le prix standard pour TOUT LE MONDE dans ce groupe
    standard_price = models.IntegerField(
        default=0,
        verbose_name="Prix Standard (DA)"
    )

    # Flag pour déclencher la génération automatique via Signal
    schedule_generated = models.BooleanField(default=False, help_text="Cochez pour générer les séances")

    # Modalité et type
    MODALITY_CHOICES = [
        ('ONLINE', 'En ligne'),
        ('IN_PERSON', 'Présentiel'),
    ]
    modality = models.CharField(max_length=10, choices=MODALITY_CHOICES, default='IN_PERSON', verbose_name="Modalité")
    is_individual = models.BooleanField(default=False, verbose_name="Individuel")

    # Abréviation unique (générée automatiquement)
    abbreviation = models.CharField(
        max_length=20,
        blank=True,
        editable=False,
        db_index=True,
        unique=True,
        help_text="Abréviation unique du cohort (générée automatiquement)"
    )

    # Cache pour l'abréviation
    _abbreviation_cache = None

    def generate_name(self):
        """Génère automatiquement le nom du cohort selon le format standardisé."""
        # Format: [Langue] [Niveau] (modalité) - [Mois Année]
        # Exemple: Japonais Niveau 1 (individuel présentiel) - Sept 2025
        
        # Partie de base: Langue + Niveau
        base = f"{self.subject.name} {self.level.name}"
        
        # Modalité entre parenthèses
        modality_text = ""
        if self.is_individual:
            if self.modality == 'ONLINE':
                modality_text = " (individuel en ligne)"
            else:
                modality_text = " (individuel présentiel)"
        else:
            if self.modality == 'ONLINE':
                modality_text = " (en ligne)"
            else:
                modality_text = " (présentiel)"
        
        # Date de début (mois en français)
        months_fr = {
            1: 'Jan', 2: 'Fév', 3: 'Mars', 4: 'Avr', 5: 'Mai', 6: 'Juin',
            7: 'Juil', 8: 'Août', 9: 'Sept', 10: 'Oct', 11: 'Nov', 12: 'Déc'
        }
        month_name = months_fr.get(self.start_date.month, str(self.start_date.month))
        date_text = f" - {month_name} {self.start_date.year}"
        
        return f"{base}{modality_text}{date_text}"
    
    def get_abbreviation(self):
        """
        Génère une abréviation compacte du cohort.
        
        Format: [CODE_LANGUE][NIVEAU][MODALITE][ANNEE_MOIS]
        
        Exemples:
        - "Chinois Niveau 3 (présentiel) - Jan 2026" → "CHN3P0126"
        - "Japonais Niveau 6 (en ligne) - Jan 2026" → "JPN6O0126"
        - "Japonais Niveau 6 (individuel en ligne) - Jan 2026" → "JPN6IO0126"
        - "Coréen Niveau 1 (présentiel) - Jan 2026" → "KR1P0126"
        """
        # Vérifier le cache pour éviter les recalculs
        if self._abbreviation_cache:
            return self._abbreviation_cache
        
        try:
            # 1. Récupérer le code de langue
            subject_name = self.subject.name.strip()
            language_code = LANGUAGE_CODES.get(subject_name)
            
            if not language_code:
                # Si pas trouvé, créer un code par défaut (première 3 lettres + 1ère lettre)
                if len(subject_name) >= 3:
                    language_code = subject_name[:3].upper()
                else:
                    language_code = subject_name[:2].upper() + 'X'
            
            # 2. Récupérer le niveau (numéro seulement)
            level_name = self.level.name.strip()
            level_number = ''.join(c for c in level_name if c.isdigit())
            if not level_number:
                level_number = '0'  # Fallback si pas de chiffre trouvé
            
            # 3. Récupérer le code de modalité
            modality_key = (self.modality, self.is_individual)
            modality_code = MODALITY_CODES.get(modality_key, 'X')
            
            # 4. Récupérer l'année et le mois
            year_short = str(self.start_date.year)[-2:]  # "26" pour 2026
            month_zero = f"{self.start_date.month:02d}"   # "01" pour janvier
            date_code = month_zero + year_short  # MMYY format (01 pour janvier, 26 pour 2026)
            
            # Construire l'abréviation
            abbreviation = f"{language_code}{level_number}{modality_code}{date_code}"
            
            # Mettre en cache
            self._abbreviation_cache = abbreviation
            return abbreviation
            
        except Exception as e:
            # En cas d'erreur, retourner un code par défaut
            return f"UNKNOWN_{self.id or 'N/A'}"
    
    def save(self, *args, **kwargs):
        """Affecte l'année active par défaut et génère le nom et l'abréviation avant la sauvegarde."""
        # Réinitialiser le cache en cas de modification
        self._abbreviation_cache = None
        
        # Assigner l'année académique active si non fournie
        if self.academic_year is None:
            current = AcademicYear.get_current()
            if current is not None:
                self.academic_year = current
        
        # Générer le nom normalisé
        self.name = self.generate_name()
        
        # Générer l'abréviation (toujours, ou seulement si vide)
        # On génère TOUJOURS pour s'assurer que c'est à jour
        self.abbreviation = self.get_abbreviation()
        
        super().save(*args, **kwargs)

    def __str__(self): return self.name

    # --- Etat & progression (calculés) ---
    @property
    def last_session(self):
        return self.sessions.order_by('-date', '-start_time').first()

    @property
    def remaining_sessions_count(self):
        return self.sessions.filter(status__in=['SCHEDULED', 'POSTPONED']).count()

    @property
    def completed_sessions_count(self):
        return self.sessions.filter(status='COMPLETED').count()

    def get_next_scheduled_session_time(self):
        """
        Calcule la prochaine séance en suivant le planning hebdomadaire (WeeklySchedule).
        Retourne un dict avec 'date', 'start_time', 'end_time', 'classroom'
        ou None si pas de planning défini.
        """
        from datetime import datetime, timedelta
        
        schedules = self.weekly_schedules.all()
        if not schedules:
            return None
        
        today = date.today()
        
        # Cherche la prochaine occurrence dans le planning
        # On regarde les 365 prochains jours
        for i in range(365):
            check_date = today + timedelta(days=i)
            
            # Sauter si avant la date de début du cohort
            if check_date < self.start_date:
                continue
            # Sauter si après la date de fin du cohort
            if check_date > self.end_date:
                break
            
            weekday = check_date.weekday()  # 0=Lundi, 6=Dimanche
            
            # Chercher un créneau pour ce jour de la semaine
            for sched in schedules:
                if sched.day_of_week == weekday:
                    # Vérifier si une séance existe déjà pour ce créneau
                    existing = self.sessions.filter(
                        date=check_date,
                        start_time=sched.start_time,
                        end_time=sched.end_time,
                        classroom=sched.classroom
                    ).exists()
                    
                    if not existing:
                        # Trouvé ! Retourner les infos
                        return {
                            'date': check_date,
                            'start_time': sched.start_time,
                            'end_time': sched.end_time,
                            'classroom': sched.classroom,
                            'day_name': check_date.strftime('%A'),
                        }
        
        return None


    @property
    def is_finished(self):
        """Vrai si aucune séance restante (SCHEDULED/POSTPONED). Les reports créent des séances et repoussent end_date via signal, donc ce calcul reste fiable."""
        if not self.sessions.exists():
            return False
        return self.remaining_sessions_count == 0

class WeeklySchedule(models.Model):
    """Le 'Patron' (Template) Hebdomadaire."""
    DAYS = [
        (0, 'Lundi'), (1, 'Mardi'), (2, 'Mercredi'), (3, 'Jeudi'), 
        (4, 'Vendredi'), (5, 'Samedi'), (6, 'Dimanche')
    ]
    cohort = models.ForeignKey(Cohort, related_name='weekly_schedules', on_delete=models.CASCADE)
    day_of_week = models.IntegerField(choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    classroom = models.ForeignKey(Classroom, on_delete=models.PROTECT)

class CourseSession(models.Model):
    """La Séance Réelle."""
    STATUS_CHOICES = [
        ('SCHEDULED', 'Prévu'),
        ('COMPLETED', 'Réalisé'),
        ('CANCELLED', 'Annulé'),   # Ne compte pas, pas de rattrapage
        ('POSTPONED', 'Reporté'),  # Doit générer un rattrapage
    ]

    cohort = models.ForeignKey(Cohort, related_name='sessions', on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # On peut changer le prof ou la salle juste pour CETTE séance
    teacher = models.ForeignKey(User, on_delete=models.PROTECT)
    classroom = models.ForeignKey(Classroom, on_delete=models.PROTECT)
    
    # Surcharge facultative de la durée (en minutes). Si vide => calcul start/end
    duration_override_minutes = models.PositiveIntegerField(null=True, blank=True)
    planned_duration_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Durée planifiée au moment de la création (minutes)")

    # Surcharge facultative du taux horaire (pour cette séance uniquement)
    teacher_hourly_rate_override = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Taux Horaire Spécifique (DA/h)",
        help_text="Laissez vide pour utiliser le taux standard du cohort. Remplissez pour surcharger pour cette séance uniquement."
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.cohort} - {self.date} ({self.get_status_display()})"

    @property
    def duration_hours(self) -> float:
        """Durée en heures décimales, avec override si défini."""
        return round(self.actual_minutes / 60.0, 4)

    @property
    def planned_duration_hours(self) -> float:
        minutes = self.planned_duration_minutes
        if minutes is None:
            minutes = self._compute_default_minutes()
        return round(minutes / 60.0, 4)

    @property
    def is_ramadan(self) -> bool:
        if not self.cohort.ramadan_start or not self.cohort.ramadan_end:
            return False
        return self.cohort.ramadan_start <= self.date <= self.cohort.ramadan_end

    @property
    def actual_minutes(self) -> int:
        """Durée réelle affichée et utilisée pour l'override/présence."""
        if self.duration_override_minutes is not None:
            return self.duration_override_minutes
        if self.is_ramadan and self.cohort.ramadan_start_time and self.cohort.ramadan_end_time:
            return self._compute_minutes(self.cohort.ramadan_start_time, self.cohort.ramadan_end_time)
        return self._compute_default_minutes()

    @property
    def pay_hourly_rate(self) -> int:
        """Tarif horaire utilisé pour la paie (surcharge > Ramadan > standard)."""
        # Priorité 1: Surcharge spécifique à cette séance
        if self.teacher_hourly_rate_override is not None:
            return self.teacher_hourly_rate_override
        # Priorité 2: Tarif spécifique Ramadan
        if self.is_ramadan and self.cohort.ramadan_teacher_hourly_rate:
            return self.cohort.ramadan_teacher_hourly_rate
        # Priorité 3: Tarif standard du cohort
        return self.cohort.teacher_hourly_rate

    @property
    def pay_hours(self) -> float:
        """Heures rémunérées (basées sur la durée réelle)."""
        return round(self.actual_minutes / 60.0, 4)

    @property
    def pay_amount(self) -> float:
        return round(self.pay_hours * self.pay_hourly_rate, 2)

    @property
    def display_start_time(self):
        """Heure à afficher (horaire Ramadan si défini)."""
        if self.is_ramadan and self.cohort.ramadan_start_time:
            return self.cohort.ramadan_start_time
        return self.start_time

    @property
    def display_end_time(self):
        """Heure à afficher (horaire Ramadan si défini)."""
        if self.is_ramadan and self.cohort.ramadan_end_time:
            return self.cohort.ramadan_end_time
        return self.end_time

    def _compute_default_minutes(self) -> int:
        return self._compute_minutes(self.start_time, self.end_time)

    def _compute_minutes(self, start_time, end_time) -> int:
        from datetime import datetime, date as _date
        duration = datetime.combine(_date.today(), end_time) - datetime.combine(_date.today(), start_time)
        return max(0, int(duration.total_seconds() // 60))

    def save(self, *args, **kwargs):
        # Sauvegarder la durée planifiée une seule fois
        if self.planned_duration_minutes is None:
            self.planned_duration_minutes = self._compute_default_minutes()
        super().save(*args, **kwargs)