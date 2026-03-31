# Logique Métier de l'Application "School Management"

Ce document décrit en détail l'architecture métier et le fonctionnement de l'application de gestion d'école (spécialisée dans les langues telles que le Japonais, Chinois, Coréen). Il est conçu pour guider une IA ou un développeur dans la refonte ou la migration de l'application, en s'assurant qu'aucune règle métier ne soit perdue.

## 1. Vue d'Ensemble du Modèle de Données

L'application est découpée en plusieurs applications Django (modules) pour séparer les responsabilités.

### A. Utilisateurs & Système (`core`)
- **Utilisateurs (Users)** : Le système distingue le personnel administratif (Staff/Admin) des professeurs (`is_teacher = True`).
- **Années Académiques (Academic Year)** : Gestion des périodes scolaires (ex: 2024-2025). Une seule année peut être active à la fois. Comprend la gestion des **frais d'inscription annuels** (en Dinar Algérien - DA).
- **Salles de Classe (Classrooms)** : Gestion de la capacité d'accueil.

### B. Gestion Pédagogique (`academics`)
- **Matières et Niveaux (Subjects & Levels)** : Les cours enseignés (ex: Japonais, Niveau 1).
- **Groupes / Cohortes (Cohorts)** : C'est le cœur du système. Un groupe est défini par :
  - La matière et le niveau.
  - La modalité : **En ligne** (Online) ou **Présentiel** (In-person).
  - Le type : **Individuel** (Private) ou **Groupe**.
  - Une planification de tarifs standards ou spécifiques.
  - La gestion des professeurs : Un prof principal, des remplaçants potentiels, et un "professeur suppléant".
  - **Gestion du Ramadan** : L'app gère spécifiquement la période de Ramadan (dates de début/fin, horaires réajustés, et même tarifs horaires professeurs spécifiques pour cette période).
  - Un système d'**abréviation générée automatiquement** (ex: `JPN6IO0126` pour Japonais Niv.6, Individuel, En Ligne, Jan 2026).
- **Emploi du temps (WeeklySchedule)** : Patron de répétition d'un cours (ex: "Tous les lundis de 10h à 12h en Salle Tokyo").
- **Séances Relles (CourseSession)** : Générées à partir des groupes. Les séances peuvent être `Préve`, `Réalisée`, `Corrigée/Reportée` ou `Annulée`.
  - La durée peut être calculée ou surchargée (`duration_override_minutes`).
  - Le prof et la salle peuvent exceptionnellement changer pour *une* séance sans impacter le groupe global.
  - Calcul du tarif horaire : L'application vérifie d'abord [1. Surcharge de la séance], puis [2. Tarif Ramadan du groupe], puis [3. Tarif standard du groupe].

### C. Gestion des Élèves (`students`)
- **Profil Élève** : Informations personnelles.
- **Inscriptions (Enrollment)** : Un élève s'inscrit à une ou plusieurs cohortes/groupes. Il doit également régler des frais d'inscription s'ils sont applicables pour l'année académique.

### D. Finance & Paie Professeurs (`finance` & `cash`)
- **Paiements Élèves** : Suivi des versements (mensuels, par session ou forfait total).
- **Paie des professeurs (Payroll)** : Basée rigoureusement sur les heures *réellement* enseignées selon le statut des séances.
- **Caisse (Cash / Till)** : Gestion de la "caisse physique" (`CashCategory` et `CashTransaction`). Permet de suivre la monnaie en caisse, avec un historique détaillé (Ajout, Retrait, Reset).

### E. Autres Modules Connexes
- **Inventaire (`inventory`)** : Suivi des livres et du matériel (entrées, sorties, ruptures de stock).
- **Prospection (`prospects`)** : CRM intégré pour suivre les leads, les intéressés, et leur conversion en élèves réels.
- **Génération de documents (`documents`, `certificate`, `attestation`)** : 
  - Factures/Reçus de paiement
  - Attestations de présence/scolarité.
  - Certificats de réussite.
- **Rapports & Emails (`reports`, `emails`)** : Statistiques sur le remplissage, la finance, et l'envoi de trames de mails aux étudiants.

---

## 2. Règles Métiers Cruciales (Attention lors de la migration)

1. **Calcul des Rémunérations (Paie)** :
   Le calcul pour générer la paie d'un professeur est très dynamique :
   - `Durée payée` = Durée réelle d'une séance (qui elle-même est modifiée si nous sommes en période de Ramadan ou modifiée manuellement par un admin).
   - `Taux horaire` = Taux de la séance (override) OU taux Ramadan du groupe OU taux normal du groupe.

2. **Génération D'Horaires et Exceptions** :
   - Un modèle de planification hebdomadaire ne génère les séances en base données que lorsqu'un administrateur valide.
   - Si une séance est *Reportée* (`POSTPONED`), le système doit forcer l'ajout d'une nouvelle séance pour que les étudiants aient bien le quota global promis à l'inscription.
   - Les séances *Annulées* (`CANCELLED`) ne se rattrapent pas et ne sont pas payées au professeur.

3. **Logique Ramadan** :
   La période de Ramadan en Algérie décale considérablement les horaires. Toute séance qui tombe mathématiquement entre `ramadan_start` et `ramadan_end` (au sein du `Cohort`) se voit écrasée de force par les paramètres `ramadan_start_time` et `ramadan_end_time`. C'est l'intelligence première de ce projet et il ne faut surtout pas perdre cette mécanique globale vs dynamique.

4. **Nomenclature des Cohortes** :
   La fonction `get_abbreviation()` assure la normalisation unique. Il est vital de conserver cette logique de syntaxe stricte car elle sert très probablement de filtre ou d'identifiant naturel pour la scolarité : `[CODE_LANGUE][NIVEAU][MODALITE_ET_TYPE][MOIS_ANNEE]`.

5. **Clôture Financière et Cash Management** :
   - Tracer avant/après chaque transaction de la caisse (`amount_before`, `amount_after`). Historisation obligatoire (`created_at`, `created_by`).
   - Le système possède une notion de "Reset" de caisse qui purge/archive les entrées d'avant sans fausser les revenus déclarés.

## 3. Recommandations pour la Nouvelle Architecture

- **Domain-Driven Design (DDD)** : Pensez à encapsuler la logique de "SessionCourse" (Calcul de prix, durée Ramadan) dans un service spécifique plutôt que dans les modèles.
- **Tâches asynchrones** : Conservez un gestionnaire de queue (ex: Celery ou Background Jobs) pour tout ce qui concerne `certificate`, `attestation`, `emails`, car c'est bloquant pour un affichage HTTP direct si l'école scale. 
- **Timezones** : Faites très attention à `timezone` et aux heures d'hiver/été / fuseaux horaires constants (Alger).
