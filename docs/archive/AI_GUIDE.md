# Guide IA - Application de Gestion d'Institut de Langues

> Ce document décrit l'architecture complète de l'application pour faciliter l'interaction avec une IA de développement ou de maintenance.

---

## 📋 Vue d'ensemble

**Type d'application :** Système de gestion d'institut de langues  
**Framework :** Django 6.0  
**Base de données :** PostgreSQL (production) / SQLite (tests)  
**Frontend :** Templates Django + Tailwind CSS + Alpine.js + HTMX  
**Langue :** Français (interface et documentation)

### Applications Django

L'application est organisée en 6 modules principaux :

1. **core** - Utilisateurs, années académiques, salles de classe, profils enseignants
2. **academics** - Groupes (cohorts), séances de cours, emplois du temps
3. **students** - Étudiants, inscriptions, présences
4. **finance** - Tarifs, paiements étudiants, paie des professeurs
5. **cash** - Gestion multi-caisses (monnaie, JLPT, caisse principale, etc.)
6. **documents** - Génération de documents Word (listes de présence)

---

## 🏗️ Architecture des Modèles

### Module `core`

#### **User** (Utilisateur système)
Hérite de `AbstractUser` de Django.

**Champs principaux :**
- `is_teacher` : Boolean - Marque l'utilisateur comme professeur
- `is_admin` : Boolean - Statut administrateur
- `phone` : CharField(20) - Téléphone
- `birth_date` : DateField - Date de naissance
- `profile_picture` : ImageField - Photo de profil (upload_to='profiles/users/')

**Propriétés calculées :**
- `age` : Calcule l'âge à partir de `birth_date`

**Relations :**
- Un User peut avoir plusieurs `assigned_cohorts` (groupes dont il est titulaire)
- Un User peut avoir plusieurs `substitute_cohorts` (groupes où il est suppléant)
- Un User peut avoir un `teacher_profile` (profil financier si is_teacher=True)

---

#### **TeacherProfile** (Profil financier enseignant)
Créé automatiquement via signal `post_save` quand un User avec `is_teacher=True` est créé.

**Champs :**
- `user` : OneToOneField(User)
- `preferred_payment_method` : CharField - Choix : CASH, TRANSFER, CHECK
- `payment_frequency` : CharField - Choix : MONTHLY, BY_SESSION
- `bank_details` : CharField - Numéro CCP/RIB
- `tax_id` : CharField - NIF (Numéro d'Identification Fiscale)
- `notes` : TextField - Notes administratives
- `created_at`, `updated_at` : DateTimeField auto

**Utilité :** Permet de stocker les préférences de paiement de chaque professeur pour faciliter les virements et la comptabilité.

---

#### **AcademicYear** (Année académique)
Ex: "2024-2025"

**Champs :**
- `label` : CharField(20, unique=True) - Ex: "2024-2025"
- `start_date` : DateField - Début de l'année
- `end_date` : DateField - Fin de l'année
- `is_current` : Boolean - Marque l'année en cours

**Relations :**
- Une année a plusieurs `cohorts` (groupes)

---

#### **Classroom** (Salle de classe)
Ex: "Salle Tokyo", "Salle Séoul"

**Champs :**
- `name` : CharField(50) - Nom de la salle
- `capacity` : IntegerField - Capacité en nombre d'étudiants

---

### Module `academics`

#### **Subject** (Matière)
Ex: "Japonais", "Coréen", "Anglais"

**Champs :**
- `name` : CharField(100)

---

#### **Level** (Niveau)
Ex: "N5", "TOPIK 1", "B1"

**Champs :**
- `name` : CharField(50)

---

#### **Cohort** (Groupe/Classe)
Le cœur de l'organisation pédagogique.

**Champs principaux :**
- `name` : CharField(150) - Nom du groupe
- `subject` : ForeignKey(Subject) - Matière enseignée
- `level` : ForeignKey(Level) - Niveau du cours
- `academic_year` : ForeignKey(AcademicYear) - Année académique
- `start_date` : DateField - Début du groupe
- `end_date` : DateField - Fin prévue du groupe

**Champs enseignants :**
- `teacher` : ForeignKey(User, is_teacher=True) - Professeur titulaire
- `substitute_teacher` : ForeignKey(User, null=True) - Professeur suppléant (optionnel)
- `teacher_hourly_rate` : IntegerField - Tarif horaire pour la paie du prof (DA/h)

**Champs financiers (étudiants) :**
- `standard_price` : IntegerField - Prix standard pour les inscriptions à ce groupe

**Champs système :**
- `schedule_generated` : Boolean - Flag pour déclencher la génération automatique de séances via signal

**Relations :**
- Un cohort a plusieurs `weekly_schedules` (patrons hebdomadaires)
- Un cohort a plusieurs `sessions` (séances réelles)
- Un cohort a plusieurs `enrollments` (inscriptions d'étudiants)
- Un cohort a plusieurs `teacher_payments` (paiements de profs liés à ce cohort)

**Logique métier :**
- Le `teacher_hourly_rate` sert à calculer automatiquement les montants dus au professeur en fonction des heures de cours réalisées.
- Le `standard_price` est utilisé comme tarif par défaut lors de l'inscription d'un étudiant (peut être remplacé par un Tariff personnalisé).

---

#### **WeeklySchedule** (Emploi du temps hebdomadaire)
Template pour générer automatiquement les séances.

**Champs :**
- `cohort` : ForeignKey(Cohort)
- `day_of_week` : IntegerField - Choix : 0=Lundi, 1=Mardi, ..., 6=Dimanche
- `start_time` : TimeField
- `end_time` : TimeField
- `classroom` : ForeignKey(Classroom)

**Utilité :** Quand on coche `schedule_generated=True` sur un Cohort, un signal génère automatiquement toutes les séances en répétant le pattern hebdomadaire entre `start_date` et `end_date`.

---

#### **CourseSession** (Séance de cours réelle)
Représente une occurrence concrète d'un cours.

**Champs :**
- `cohort` : ForeignKey(Cohort)
- `date` : DateField - Date de la séance
- `start_time` : TimeField
- `end_time` : TimeField
- `teacher` : ForeignKey(User) - Prof assigné (peut différer du titulaire si remplacement)
- `classroom` : ForeignKey(Classroom)
- `status` : CharField - Choix : SCHEDULED, COMPLETED, CANCELLED, POSTPONED
- `note` : TextField - Notes sur la séance

**Relations :**
- Une session a plusieurs `attendances` (présences d'étudiants)

**Logique métier :**
- Seules les séances avec `status='COMPLETED'` comptent pour le calcul de la paie du professeur.
- `CANCELLED` : séance annulée, pas de rattrapage, ne compte pas.
- `POSTPONED` : séance reportée, génère automatiquement une séance de rattrapage à une date ultérieure.
- Le système supporte le remplacement : le `teacher` de la session peut différer du `teacher` du cohort.

**Calcul de durée :**
```python
duration_minutes = (end_time.hour*60 + end_time.minute) - (start_time.hour*60 + start_time.minute)
```

---

### Module `students`

#### **Student** (Étudiant)

**Champs :**
- `first_name`, `last_name` : CharField(100)
- `email` : EmailField (optionnel)
- `phone`, `phone_2` : CharField(20) - Numéros de contact
- `birth_date` : DateField (optionnel)
- `motivation` : TextField - Raison de l'inscription
- `student_code` : CharField(20, unique=True) - Code étudiant unique (auto ou manuel)
- `profile_picture` : ImageField - Photo (upload_to='profiles/students/')
- `created_at` : DateTimeField auto

**Propriétés calculées :**
- `age` : Calcule l'âge à partir de `birth_date`

**Relations :**
- Un étudiant a plusieurs `enrollments` (inscriptions à des groupes)

**Affichage :** `"{last_name.upper()} {first_name}"` (Ex: "DURAND Alice")

---

#### **Enrollment** (Inscription/Contrat)
Lie un étudiant à un groupe avec ses conditions financières.

**Champs principaux :**
- `student` : ForeignKey(Student)
- `cohort` : ForeignKey(Cohort)
- `tariff` : ForeignKey(Tariff) - Tarif appliqué
- `payment_plan` : CharField - Choix : FULL (totalité), MONTHLY (échelonné), PACK (pack d'heures)
- `discount` : ForeignKey(Discount, null=True) - Réduction appliquée (optionnelle)

**Champs pack d'heures :**
- `hours_purchased` : DecimalField(5,1) - Heures achetées (pour mode PACK)
- `hours_consumed` : DecimalField(5,1) - Heures consommées

**Champs statut :**
- `is_active` : Boolean - Inscription active ou non
- `date` : DateField auto - Date de l'inscription

**Propriétés calculées :**
- `balance_due` : Calcule le reste à payer (tarif - total des paiements effectués)

**Relations :**
- Une inscription a plusieurs `payments` (paiements effectués)
- Une inscription a plusieurs `installments` (échéances)
- Une inscription a plusieurs `attendances` (présences aux séances)

**Logique métier :**
- **FULL** : L'étudiant paie la totalité en une fois.
- **MONTHLY** : Le montant est divisé en échéances mensuelles (générées automatiquement par le système).
- **PACK** : L'étudiant achète un certain nombre d'heures, qui sont déduites à chaque séance facturée.

---

#### **Attendance** (Présence)
Ligne de présence individuelle pour une séance.

**Champs :**
- `session` : ForeignKey(CourseSession)
- `student` : ForeignKey(Student)
- `enrollment` : ForeignKey(Enrollment)
- `status` : CharField - Choix : PRESENT, ABSENT, LATE, EXCUSED
- `billable` : Boolean - Indique si la séance doit être facturée (déduire du pack d'heures)
- `note` : TextField - Notes sur la présence
- `updated_at` : DateTimeField auto

**Contrainte :** `unique_together = ('session', 'student')` - Un étudiant ne peut avoir qu'une seule ligne de présence par séance.

**Logique métier :**
- Par défaut, `billable=True` : la séance compte pour le calcul du reste d'heures.
- L'admin peut marquer `billable=False` si la séance est offerte ou excusée.
- Utilisé pour calculer les heures consommées dans le mode PACK.

**Création automatique :**
- Signal `post_save` sur Enrollment : crée automatiquement des Attendance pour toutes les séances futures du cohort.
- Signal `post_save` sur CourseSession : crée automatiquement des Attendance pour tous les étudiants inscrits actifs du cohort.

---

### Module `finance`

#### **Tariff** (Catalogue de prix)
Liste des tarifs disponibles pour les inscriptions.

**Champs :**
- `name` : CharField(150) - Ex: "Tarif 2025 - Japonais N1 - Standard"
- `amount` : IntegerField - Montant total en DA

**Utilité :** Évite de saisir manuellement le prix à chaque inscription. On choisit un tarif dans la liste.

---

#### **Payment** (Paiement étudiant)
Entrée d'argent dans la caisse.

**Champs :**
- `enrollment` : ForeignKey(Enrollment)
- `amount` : IntegerField - Montant en DA
- `method` : CharField - Choix : CASH, CARD, CHECK
- `date` : DateField auto
- `transaction_id` : CharField - Numéro de chèque/virement
- `recorded_by` : ForeignKey(User)

**Logique métier :**
- Chaque paiement est lié à une inscription spécifique.
- Le total des paiements est comparé au `tariff.amount` pour calculer le solde restant.

---

#### **Installment** (Échéance)
Échéance de paiement pour un plan MONTHLY.

**Champs :**
- `enrollment` : ForeignKey(Enrollment)
- `due_date` : DateField - Date limite de paiement
- `amount` : IntegerField - Montant dû
- `is_paid` : Boolean - Statut payé/impayé
- `payment` : ForeignKey(Payment, null=True) - Lien vers le paiement qui a soldé cette échéance

**Logique métier :**
- Généré automatiquement lors de la création d'une inscription avec `payment_plan='MONTHLY'`.
- Permet de suivre les échéances impayées et d'envoyer des rappels.

---

#### **Discount** (Réduction)
Promotions ou bourses appliquées aux inscriptions.

**Champs :**
- `name` : CharField(100) - Ex: "Réduction Fratrie"
- `value` : IntegerField - Valeur de la réduction
- `type` : CharField - Choix : PERCENT (%), FIXED (montant fixe en DA)
- `is_active` : Boolean - Réduction active ou non

**Utilité :**
- Permet d'appliquer des réductions de manière systématique (ex: -10% pour fratrie, -5000 DA bourse, etc.).

---

#### **TeacherPayment** (Paiement professeur - ancien système)
Historique des paiements aux enseignants (sorties d'argent).

**Champs :**
- `teacher` : ForeignKey(User, is_teacher=True)
- `period_start`, `period_end` : DateField - Période couverte
- `total_amount` : IntegerField - Montant total payé
- `payment_method` : CharField - Choix : CASH, TRANSFER, CHECK
- `payment_date` : DateField - Date du paiement
- `recorded_by` : ForeignKey(User)
- `proof_reference` : CharField - N° de chèque/virement
- `notes` : TextField

**Note :** Ce modèle est l'ancien système de paie globale. Il est progressivement remplacé par **TeacherCohortPayment** pour un suivi plus précis par cohort.

---

#### **TeacherCohortPayment** (Paiement par cohort - nouveau système TDD)
Paiement pour un professeur pour **UN COHORT SPÉCIFIQUE**, avec calcul automatique.

**Champs :**
- `teacher` : ForeignKey(User, is_teacher=True)
- `cohort` : ForeignKey(Cohort)
- `period_start`, `period_end` : DateField - Période couverte
- `amount_due` : DecimalField(10,2) - Montant dû (calculé auto : Σ(durée_séance × tarif_horaire))
- `amount_paid` : DecimalField(10,2) - Montant payé
- `payment_date` : DateField - Date du paiement
- `payment_method` : CharField - CASH, TRANSFER, CHECK
- `recorded_by` : ForeignKey(User)
- `notes` : TextField
- `created_at`, `updated_at` : DateTimeField auto

**Propriétés calculées :**
- `balance_due` : Reste à payer (`amount_due - amount_paid`)
- `is_fully_paid` : Boolean - Vrai si soldé

**Contraintes :**
- Index : `(teacher, cohort, -payment_date)` et `(cohort, -payment_date)` pour optimiser les requêtes.
- UniqueConstraint : `(teacher, cohort, period_start, period_end, payment_date, amount_paid)` pour éviter les doublons.

**Logique métier :**
- Le système calcule automatiquement `amount_due` en sommant les heures de toutes les séances **COMPLETED** du cohort dans la période, multipliées par `cohort.teacher_hourly_rate`.
- Supporte les paiements partiels : plusieurs enregistrements peuvent exister pour un même cohort/période.
- Permet un suivi indépendant par groupe : chaque cohort a son propre historique de paiements.

**Formule de calcul :**
```python
# Pour chaque séance COMPLETED du cohort dans la période
duration_hours = (end_time - start_time) en heures
pay_for_session = duration_hours * cohort.teacher_hourly_rate

# Somme sur toutes les séances
amount_due = Σ(pay_for_session)
```

---

### Module `cash`

#### **CashCategory** (Catégorie de caisse)
Ex: "Monnaie", "Caisse JLPT", "Caisse Principale"

**Champs :**
- `name` : CharField(100, unique=True)
- `description` : TextField - Description de l'usage
- `current_amount` : IntegerField - Montant actuel en DA
- `created_at` : DateTimeField auto
- `last_reset` : DateTimeField - Dernière remise à zéro
- `is_total` : Boolean - Si True, cette catégorie représente le total calculé automatiquement

**Logique métier :**
- Permet de gérer plusieurs caisses séparées (monnaie pour rendre, fonds JLPT, etc.).
- Une catégorie spéciale "TOTAL" (is_total=True) est calculée comme la somme de toutes les autres.

---

#### **CashTransaction** (Transaction de caisse)
Historique des mouvements de caisse.

**Champs :**
- `category` : ForeignKey(CashCategory)
- `transaction_type` : CharField - Choix : ADD (ajout), REMOVE (retrait), SET (définir montant), RESET (remise à zéro)
- `amount` : IntegerField - Montant
- `note` : TextField - Raison/note
- `created_at` : DateTimeField auto
- `created_by` : ForeignKey(User, null=True)
- `amount_before` : IntegerField - Montant avant l'opération
- `amount_after` : IntegerField - Montant après l'opération

**Logique métier :**
- Chaque transaction enregistre l'état avant/après pour traçabilité.
- Les transactions ne sont pas supprimables (audit trail), mais peuvent être "annulées" en créant une transaction inverse.

---

### Module `documents`

**Modèles :** Aucun modèle propre (utilise les modèles d'autres apps).

**Fonctionnalités :**
- Génération de documents Word (listes de présence) à partir des templates `.docx`.
- Téléchargement de listes de présence par séance ou par cohort complet.
- Utilise la bibliothèque `python-docx` pour manipuler les fichiers Word.

---

## 🌐 Routes et URLs

### Routes principales (`config/urls.py`)

```python
/admin/                     # Interface d'administration Django
/login/                     # Connexion
/logout/                    # Déconnexion
/signup/                    # Inscription (si activé)
/                           # Dashboard principal
/enrollment/new/            # Créer une inscription
/students/                  # Module étudiants
/finance/                   # Module finance
/academics/                 # Module académique
/documents/                 # Génération de documents
/cash/                      # Gestion de caisse
```

---

### Routes `academics` (app_name='academics')

```python
/academics/cohorts/                         # Liste des groupes
/academics/cohorts/<pk>/                    # Détail d'un groupe
/academics/cohorts/<pk>/generate/           # Générer les séances auto
/academics/session/<session_id>/            # Détail d'une séance
/academics/session/<session_id>/postpone/   # Reporter une séance
/academics/session/<session_id>/cancel-postpone/  # Annuler le report
```

**Fonctionnalités :**
- **Liste des groupes** : Affiche tous les cohorts avec filtres par année/matière/prof.
- **Détail groupe** : Affiche les séances, étudiants inscrits, statistiques.
- **Génération auto** : Utilise les `WeeklySchedule` pour créer toutes les séances entre start_date et end_date.
- **Report de séance** : Crée une séance de rattrapage et ajuste la date de fin du groupe si nécessaire.

---

### Routes `students` (app_name='students')

```python
/students/           # Liste des étudiants
/students/<pk>/      # Détail d'un étudiant
```

**Fonctionnalités :**
- **Liste** : Affiche tous les étudiants avec recherche par nom et filtres par groupe.
- **Détail** : Affiche les inscriptions, l'historique des paiements, le solde, les présences.

---

### Routes `finance` (app_name='finance')

```python
# Paiements étudiants
/finance/payment/add/<enrollment_id>/       # Ajouter un paiement

# Paie professeurs (ancien système - redirige vers nouveau)
/finance/payroll/                           # Liste paie (→ redirige vers /finance/payroll-cohort/)
/finance/payroll/teacher/<teacher_id>/      # Détail paie prof (ancien)
/finance/payroll/teacher/<teacher_id>/pay/  # Enregistrer paiement prof (ancien)

# Paie par cohort (nouveau système TDD)
/finance/payroll-cohort/                    # Liste paie par cohort
/finance/payroll-cohort/<cohort_id>/        # Détail paie pour un cohort
/finance/payroll-cohort/<cohort_id>/pay/    # Enregistrer paiement pour un cohort
```

**Fonctionnalités paie par cohort :**
- **Liste** (`/finance/payroll-cohort/`) :
  - Affiche tous les cohorts avec calcul auto des montants dus par prof et par groupe.
  - Filtres optionnels : professeur, période (start/end).
  - **Pas de filtre par défaut** : l'utilisateur choisit la période.
  - Affiche : nombre de séances, heures totales, montant dû, montant payé, solde.
  
- **Détail** (`/finance/payroll-cohort/<cohort_id>/`) :
  - Affiche le détail des séances COMPLETED pour un cohort/prof/période.
  - Calcul automatique : durée × tarif horaire pour chaque séance.
  - Historique des paiements pour ce cohort.
  - Gère les dates vides : si `start` et `end` sont vides, utilise les bornes min/max des séances du cohort.
  
- **Enregistrement paiement** (`/finance/payroll-cohort/<cohort_id>/pay/`) :
  - Formulaire pré-rempli avec `amount_due`, période, prof, cohort.
  - Permet paiement partiel ou total.
  - Calcul JS du reste à payer en temps réel.
  - Gère les dates vides : utilise les dates par défaut du cohort/sessions.
  - Crée un enregistrement `TeacherCohortPayment`.

**Logique métier importante :**
- Les montants dus sont **calculés à la volée** en fonction des séances COMPLETED.
- Les filtres de date sont **optionnels** et permettent de cibler une période précise.
- Plusieurs paiements peuvent exister pour un même cohort (paiements échelonnés).
- La contrainte unique empêche les doublons exacts (même prof, cohort, période, date et montant).

---

### Routes `cash` (app_name='cash')

```python
/cash/                                  # Dashboard caisses
/cash/create/                           # Créer une catégorie
/cash/category/<pk>/                    # Détail d'une catégorie
/cash/category/<pk>/transaction/        # Ajouter une transaction
/cash/category/<pk>/reset/              # Remettre à zéro
/cash/category/<pk>/custom-reset/       # Reset avec montant personnalisé
/cash/category/<pk>/delete/             # Supprimer catégorie
/cash/transaction/<id>/cancel/          # Annuler une transaction
```

**Fonctionnalités :**
- **Dashboard** : Affiche toutes les catégories avec leur montant actuel et historique des transactions récentes.
- **Transactions** : ADD (ajouter), REMOVE (retirer), SET (définir), RESET (remettre à zéro).
- **Audit trail** : Toutes les transactions sont enregistrées avec before/after.

---

### Routes `documents` (app_name='documents')

```python
/documents/                                      # Sélectionner un groupe
/documents/generate/<cohort_id>/                 # Générer documents pour un groupe
/documents/attendance/session/<session_id>/      # Télécharger liste de présence séance
/documents/attendance/cohort/<cohort_id>/        # Télécharger liste complète groupe
```

**Fonctionnalités :**
- Génération de listes de présence au format Word (.docx).
- Liste par séance : une page par séance avec les étudiants inscrits.
- Liste complète : toutes les séances d'un groupe dans un seul document.

---

## 🔄 Flux de données et logique métier

### 1. Création d'un groupe (Cohort)

1. Admin crée un Cohort avec :
   - Matière, niveau, année académique
   - Dates de début/fin
   - Prof titulaire + tarif horaire
   - Prix standard pour inscriptions
   
2. Admin crée des `WeeklySchedule` pour définir le planning hebdomadaire (ex: Lundi 9h-11h, Mercredi 14h-16h).

3. Admin coche `schedule_generated=True` → **Signal** génère automatiquement toutes les séances (CourseSession) en répétant le pattern entre start_date et end_date.

4. Les séances sont créées avec `status='SCHEDULED'`.

---

### 2. Inscription d'un étudiant

1. Admin crée/sélectionne un Student.

2. Admin crée un Enrollment :
   - Lie l'étudiant au Cohort
   - Choisit un Tariff (ou utilise le standard_price du cohort)
   - Choisit le payment_plan (FULL, MONTHLY, PACK)
   - Applique un Discount éventuel

3. **Signal post_save sur Enrollment** :
   - Crée automatiquement des `Attendance` pour toutes les séances futures du cohort.
   - Si payment_plan='MONTHLY', génère des `Installment` (échéances).

---

### 3. Enregistrement de présences

1. Prof ou admin va sur la page de détail d'une séance.

2. Formulaire de présence pré-rempli avec tous les étudiants inscrits actifs.

3. Admin coche PRESENT/ABSENT/LATE/EXCUSED pour chaque étudiant.

4. Admin peut décocher `billable` si la séance ne doit pas être facturée (offerte, rattrapage, etc.).

5. Enregistrement → Les `Attendance` sont mises à jour.

6. Si la séance est marquée `COMPLETED`, elle sera comptée pour :
   - La paie du professeur (calcul automatique)
   - La consommation d'heures du pack (si mode PACK et billable=True)

---

### 4. Calcul de la paie professeur

#### Vue liste (`/finance/payroll-cohort/`)

1. Vue récupère tous les cohorts (filtrables par prof et période).

2. Pour chaque cohort :
   ```python
   sessions = cohort.sessions.filter(status='COMPLETED')
   if period_start and period_end:
       sessions = sessions.filter(date__range=[period_start, period_end])
   
   total_minutes = sum(
       (s.end_time.hour*60 + s.end_time.minute) - (s.start_time.hour*60 + s.start_time.minute)
       for s in sessions
   )
   total_hours = total_minutes / 60
   amount_due = total_hours * cohort.teacher_hourly_rate
   
   # Paiements existants pour ce cohort/période
   payments = TeacherCohortPayment.objects.filter(
       cohort=cohort,
       period_start__gte=period_start,
       period_end__lte=period_end
   )
   total_paid = sum(p.amount_paid for p in payments)
   balance_due = amount_due - total_paid
   ```

3. Affichage du tableau avec : nom groupe, prof, nb séances, heures, montant dû, montant payé, solde.

#### Vue détail (`/finance/payroll-cohort/<cohort_id>/`)

1. Affiche la liste des séances COMPLETED avec détail de chaque paiement :
   - Date séance
   - Durée en heures
   - Tarif horaire
   - Montant calculé pour cette séance

2. Affiche l'historique des paiements pour ce cohort.

3. Calcule le solde global.

#### Enregistrement paiement (`/finance/payroll-cohort/<cohort_id>/pay/`)

1. Formulaire pré-rempli avec :
   - `amount_due` (calculé depuis les séances)
   - `period_start`, `period_end` (de la requête ou défaut cohort)
   - `payment_method` (préférence du prof si disponible)

2. Admin saisit `amount_paid` (peut être partiel).

3. Validation :
   - Si `amount_paid > amount_due`, warning mais pas de blocage (avance possible).
   - Si dates vides, utilise les bornes des séances du cohort.

4. Création d'un `TeacherCohortPayment` avec :
   - teacher, cohort, période, montants, méthode, enregistreur, notes

5. Contrainte unique empêche les doublons exacts.

---

### 5. Report de séance

1. Admin accède à `/academics/session/<session_id>/postpone/`.

2. Saisit la nouvelle date de rattrapage.

3. Le système :
   - Marque la séance originale comme `status='POSTPONED'`.
   - Crée une nouvelle séance avec la date de rattrapage, `status='SCHEDULED'`.
   - Si la date de rattrapage > `cohort.end_date`, ajuste automatiquement `end_date`.

4. **Signal post_save sur la nouvelle séance** :
   - Crée automatiquement des `Attendance` pour tous les étudiants inscrits actifs.

---

### 6. Gestion des caisses

1. Admin crée plusieurs `CashCategory` (ex: Monnaie, JLPT, Principale).

2. Pour chaque transaction :
   - Sélectionne la catégorie
   - Choisit le type (ADD, REMOVE, SET, RESET)
   - Saisit le montant et une note

3. Le système enregistre une `CashTransaction` avec before/after.

4. Le `current_amount` de la catégorie est mis à jour automatiquement.

5. La catégorie "TOTAL" est recalculée comme la somme de toutes les autres.

---

## 🧪 Tests

### Tests existants

**Fichiers de tests :**
- `academics/tests.py` - Tests des groupes et séances
- `students/tests.py` - Tests des étudiants et inscriptions
- `finance/tests.py` - Tests de paie (ancien système)
- `finance/test_payroll_cohort.py` - Tests de paie par cohort (nouveau système TDD)
- `finance/test_teacher_payroll_by_cohort.py` - Tests spécifiques au calcul par cohort
- `core/tests.py` - Tests des utilisateurs et profils

**Tests paie par cohort (7 tests) :**
1. `test_session_aggregation_completed_only` - Vérifie que seules les séances COMPLETED sont comptées.
2. `test_payment_model_balance_properties` - Teste les propriétés `balance_due` et `is_fully_paid`.
3. `test_uniqueness_constraint_duplicate_prevented` - Vérifie que la contrainte unique empêche les doublons.
4. `test_payroll_list_view_no_default_dates` - Vérifie qu'aucune date n'est pré-sélectionnée par défaut.
5. `test_detail_view_handles_empty_params` - Vérifie le fallback sur les dates cohort/sessions si params vides.
6. `test_record_payment_handles_empty_dates` - Vérifie que le formulaire de paiement gère les dates vides.
7. `test_legacy_payroll_redirects` - Vérifie la redirection de l'ancienne URL vers la nouvelle.

**Configuration tests :**
- SQLite en mémoire pour éviter les problèmes de permissions PostgreSQL.
- Paramétrage dans `config/settings.py` :
```python
if 'test' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'TEST': {'NAME': ':memory:'},
        }
    }
```

**Lancer les tests :**
```bash
python manage.py test                                    # Tous les tests
python manage.py test finance.test_payroll_cohort        # Tests paie cohort
python manage.py test academics                          # Tests académique
```

---

## 🎨 Frontend et Templates

### Stack technique
- **Templates Django** : Système de templates natif avec héritage
- **Tailwind CSS** : Framework CSS utility-first
- **Alpine.js** : Framework JS léger pour interactivité
- **HTMX** : Pour les requêtes AJAX sans JS

### Structure des templates

**Base template :** `templates/base.html`
- Contient la navbar, sidebar, et structure générale.
- Sidebar avec liens vers :
  - Dashboard
  - Étudiants
  - Groupes
  - Paie des Professeurs (`/finance/payroll-cohort/`)
  - Documents
  - Caisses

**Templates par module :**
- `templates/core/` - Login, signup, dashboard
- `templates/academics/` - Liste groupes, détail groupe, détail séance
- `templates/students/` - Liste étudiants, détail étudiant, formulaire inscription
- `templates/finance/` - Paie profs (liste, détail, formulaire paiement)
- `templates/cash/` - Dashboard caisses, formulaires transactions
- `templates/documents/` - Sélection groupe, génération documents

### Composants réutilisables

**Cartes responsive :**
```html
<div class="bg-white shadow-md rounded-lg p-4">
  <!-- Contenu -->
</div>
```

**Tableaux avec fallback mobile :**
- Desktop : tableau classique
- Mobile : cartes empilées (hidden md:table-cell)

**Formulaires :**
- Labels clairs avec `for` associé
- Inputs avec Tailwind : `border-gray-300 rounded-md shadow-sm`
- Boutons : `bg-blue-600 text-white hover:bg-blue-700`

---

## 🔐 Permissions et sécurité

### Niveaux d'accès

1. **Anonyme** : Accès uniquement à /login/
2. **is_teacher=True** : Dashboard + groupes assignés + séances
3. **is_staff=True ou is_admin=True** : Accès complet

### Protection des vues

```python
from django.contrib.auth.decorators import login_required

@login_required
def ma_vue(request):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    # ...
```

### Signaux automatiques

**Création automatique de TeacherProfile :**
```python
@receiver(post_save, sender=User)
def create_teacher_profile(sender, instance, created, **kwargs):
    if created and instance.is_teacher:
        TeacherProfile.objects.create(user=instance)
```

**Création automatique de présences :**
- Quand on crée un Enrollment → crée Attendance pour toutes les séances futures du cohort.
- Quand on crée une CourseSession → crée Attendance pour tous les étudiants actifs du cohort.

---

## 📦 Dépendances principales

**requirements.txt (extrait) :**
```
Django==6.0
psycopg[binary]>=3.1.0    # PostgreSQL
Pillow                    # Images
python-docx               # Génération Word
django-tailwind           # Tailwind intégration (optionnel)
```

---

## 🚀 Démarrage et commandes

### Installation

```bash
# Créer environnement virtuel
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Installer dépendances
pip install -r requirements.txt

# Créer la base de données
python manage.py makemigrations
python manage.py migrate

# Créer superuser
python manage.py createsuperuser

# Lancer serveur
python manage.py runserver
```

### Commandes utiles

```bash
# Tests
python manage.py test
python manage.py test finance.test_payroll_cohort

# Migrations
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations

# Shell interactif
python manage.py shell

# Collecter fichiers statiques (production)
python manage.py collectstatic
```

### Scripts utilitaires

**`create_multiple_cohorts.py`** : Génère des données de test (3 cohorts avec séances).
**`check_data.py`** : Diagnostics de la base de données.
**`check_cohort_dates.py`** : Vérifie les dates des cohorts.
**`do_fix.py`** : Utilitaire de remplacement de code (helper pour éditions rapides).

---

## 🧩 Patterns et conventions

### Nommage

**Modèles :** Singulier, CamelCase (ex: `Student`, `CourseSession`)  
**Vues :** snake_case, verbe + nom (ex: `student_list`, `record_cohort_payment`)  
**URLs :** kebab-case (ex: `/payroll-cohort/`, `/teacher-payroll/`)  
**Templates :** snake_case (ex: `student_detail.html`, `teacher_cohort_payroll.html`)

### Structure des vues

```python
def ma_vue(request, pk):
    # 1. Récupération des objets
    obj = get_object_or_404(Model, pk=pk)
    
    # 2. Traitement GET/POST
    if request.method == 'POST':
        # Validation et sauvegarde
        messages.success(request, "Succès!")
        return redirect('app:view_name')
    
    # 3. Préparation du contexte
    context = {
        'obj': obj,
        'data': compute_data(),
    }
    
    # 4. Rendu template
    return render(request, 'app/template.html', context)
```

### Calculs financiers

**Toujours en DA (Dinars Algériens), entiers ou Decimal.**

```python
# Calcul paie prof
total_minutes = sum(
    (s.end_time.hour*60 + s.end_time.minute) - 
    (s.start_time.hour*60 + s.start_time.minute)
    for s in sessions
)
total_hours = total_minutes / 60
amount_due = total_hours * cohort.teacher_hourly_rate
```

**Affichage avec séparateurs :**
```python
f"{amount:,} DA".replace(',', ' ')  # 12000 DA → "12 000 DA"
```

---

## 📊 Statistiques et rapports

### Dashboard principal
- Nombre d'étudiants actifs
- Nombre de groupes en cours
- Séances du jour
- Paiements en attente
- Solde des caisses

### Rapports paie
- Vue globale : tous les cohorts, tous les profs
- Vue par prof : détail de tous ses groupes
- Vue par cohort : historique complet des paiements
- Export possible (à implémenter : CSV, PDF)

### Rapports présences
- Taux de présence par étudiant
- Taux de présence par groupe
- Heures consommées vs achetées (mode PACK)

---

## 🔧 Maintenance et évolution

### Points d'amélioration possibles

1. **Tests supplémentaires :**
   - Multi-teachers (plusieurs profs sur différents cohorts)
   - Substitute teacher (sessions données par le suppléant)
   - Partial-day sessions (sessions de durées variables)
   - Period filters edge cases (périodes chevauchant plusieurs cohorts)

2. **Fonctionnalités futures :**
   - Export CSV/PDF des paies
   - Notifications email pour échéances
   - Interface mobile dédiée (PWA)
   - Intégration calendrier (iCal)
   - API REST pour applications externes

3. **Optimisations :**
   - Cache des calculs de paie
   - Requêtes optimisées avec `select_related`/`prefetch_related`
   - Index supplémentaires si volume important

---

## 💡 Exemples de requêtes utiles

### Trouver toutes les séances d'un prof entre deux dates

```python
from academics.models import CourseSession
from datetime import date

sessions = CourseSession.objects.filter(
    teacher__username='yanis',
    date__range=[date(2025, 1, 1), date(2025, 1, 31)],
    status='COMPLETED'
)
```

### Calculer le montant dû à un prof pour un cohort

```python
from academics.models import Cohort

cohort = Cohort.objects.get(id=1)
sessions = cohort.sessions.filter(status='COMPLETED')

total_minutes = sum(
    (s.end_time.hour*60 + s.end_time.minute) - 
    (s.start_time.hour*60 + s.start_time.minute)
    for s in sessions
)
total_hours = total_minutes / 60
amount_due = total_hours * cohort.teacher_hourly_rate
```

### Trouver les étudiants avec un solde impayé

```python
from students.models import Enrollment

enrollments = Enrollment.objects.filter(is_active=True)
unpaid = [e for e in enrollments if e.balance_due > 0]
```

### Historique des paiements d'un étudiant

```python
from students.models import Student

student = Student.objects.get(student_code='ST-2025-001')
enrollments = student.enrollments.all()

for enrollment in enrollments:
    print(f"Groupe: {enrollment.cohort}")
    print(f"Tarif: {enrollment.tariff.amount} DA")
    payments = enrollment.payments.all()
    for p in payments:
        print(f"  - {p.date}: {p.amount} DA ({p.get_method_display()})")
    print(f"Reste: {enrollment.balance_due} DA\n")
```

### Séances non marquées comme complétées

```python
from academics.models import CourseSession
from datetime import date

past_sessions = CourseSession.objects.filter(
    date__lt=date.today(),
    status='SCHEDULED'
)
```

---

## 📝 Notes importantes pour l'IA

### Principes de calcul automatique

1. **Paie professeur** : TOUJOURS calculée dynamiquement depuis les séances COMPLETED.
2. **Solde étudiant** : TOUJOURS calculé comme `tariff.amount - sum(payments)`.
3. **Heures pack** : Déduites à chaque séance où `attendance.billable=True`.

### Contraintes métier

1. **Une séance CANCELLED ne génère PAS de rattrapage** (définitif).
2. **Une séance POSTPONED génère UN rattrapage** (nouvelle séance).
3. **Les filtres de date sont optionnels** dans les vues de paie (l'utilisateur choisit).
4. **Les paiements professeurs sont enregistrés par cohort** pour traçabilité fine.

### Points de vigilance

1. **Éviter les calculs en JS** : toujours valider côté serveur.
2. **Jamais supprimer de transactions** : créer une transaction inverse.
3. **Les signaux créent automatiquement les Attendance** : ne pas dupliquer en vue.
4. **UniqueConstraint sur TeacherCohortPayment** : éviter les doublons exacts.

---

## 🎯 Résumé pour prompt IA

**Quand tu travailles sur cette application :**

1. **Respecte l'architecture modulaire** : core, academics, students, finance, cash, documents.
2. **Utilise les signaux existants** : TeacherProfile auto-créé, Attendance auto-créée.
3. **Calculs dynamiques** : Ne stocke jamais de montants calculables, sauf pour historique (TeacherCohortPayment).
4. **Tests obligatoires** : Tout nouveau calcul ou logique métier doit avoir un test.
5. **Nommage cohérent** : Suis les conventions Django et les patterns existants.
6. **Filtres optionnels** : Ne pré-sélectionne jamais de dates par défaut dans les vues de paie.
7. **Gestion des dates vides** : Utilise toujours des fallbacks basés sur cohort.start_date/end_date ou min/max des sessions.

**Structure typique d'une nouvelle fonctionnalité :**
1. Modèle(s) avec propriétés calculées
2. Vue(s) avec logique métier
3. Template(s) responsive
4. URLs et tests
5. Documentation dans ce guide

---

## 📞 Contact et support

**Développeur principal :** Yanis Barbara  
**Email :** (à compléter si nécessaire)  
**Repository :** school_management (Owner: yanis-san, Branch: main)

---

**Dernière mise à jour :** 2025-12-16  
**Version Django :** 6.0  
**Base de données :** PostgreSQL (production), SQLite (tests)
