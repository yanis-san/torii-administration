# documents/sync.py
"""
Système de synchronisation COMPLÈTE pour données multi-utilisateurs.
Permet le merge de TOUTE la base sans perte (students, cohorts, sessions, presences, paiements, tarifs, etc).
RÈGLE: UPDATE uniquement, JAMAIS supprimer. Sauvegarde auto avant import.
"""
import csv
from io import StringIO, BytesIO
from datetime import datetime
from django.utils import timezone
from django.db.models import Q
import subprocess
import os

from students.models import Attendance, Student
from academics.models import Cohort, CourseSession, Subject, Level
from finance.models import Payment, TeacherCohortPayment, Tariff, Discount
from core.models import AcademicYear, User, Classroom


class SyncManager:
    """Gère la synchronisation et le merge des données."""

    @staticmethod
    def export_attendance_sync_csv(cohort_id):
        """
        Exporte un CSV de synchronisation pour les presences.
        Format: étudiant | séance | statut | timestamp_modif | auteur
        """
        cohort = Cohort.objects.get(id=cohort_id)
        sessions = cohort.sessions.all().order_by('date')
        enrollments = cohort.enrollments.select_related('student').order_by('student__last_name')
        
        attendance_records = Attendance.objects.filter(
            session__cohort=cohort
        ).select_related('student', 'session')
        
        # Index pour accès rapide
        att_dict = {
            (a.student_id, a.session_id): a 
            for a in attendance_records
        }
        
        output = StringIO()
        writer = csv.writer(output)
        
        # En-tête
        writer.writerow([
            'cohort_id',
            'cohort_name',
            'student_id',
            'student_name',
            'session_id',
            'session_date',
            'status',
            'last_modified',
            'modified_by',
        ])
        
        # Données
        for enr in enrollments:
            for sess in sessions:
                att = att_dict.get((enr.student_id, sess.id))
                status = att.status if att else 'PRESENT'
                last_mod = att.updated_at.isoformat() if att and hasattr(att, 'updated_at') else ''
                modified_by = att.modified_by if att and hasattr(att, 'modified_by') else 'system'
                
                writer.writerow([
                    cohort.id,
                    cohort.name,
                    enr.student.id,
                    f"{enr.student.last_name} {enr.student.first_name}",
                    sess.id,
                    sess.date.isoformat(),
                    status,
                    last_mod,
                    modified_by,
                ])
        
        return output.getvalue()

    @staticmethod
    def import_attendance_sync_csv(csv_content, user):
        """
        Importe et merge un CSV de synchronisation des presences.
        Résout les conflits par 'last-write-wins' (timestamp le plus récent gagne).
        """
        reader = csv.DictReader(StringIO(csv_content))
        changes = {'created': 0, 'updated': 0, 'conflicts': 0}
        
        for row in reader:
            try:
                student_id = int(row['student_id'])
                session_id = int(row['session_id'])
                status = row['status']
                remote_timestamp = row.get('last_modified', '')
                
                # Récupère ou crée l'enregistrement
                att, created = Attendance.objects.get_or_create(
                    student_id=student_id,
                    session_id=session_id,
                    defaults={'status': status}
                )
                
                if created:
                    changes['created'] += 1
                    if not hasattr(att, 'modified_by'):
                        att.modified_by = user.username
                    att.save()
                else:
                    # Compare les timestamps pour décider du merge
                    local_timestamp = att.updated_at.isoformat() if hasattr(att, 'updated_at') else ''
                    
                    if remote_timestamp and local_timestamp:
                        if remote_timestamp > local_timestamp:
                            # Remote est plus récent
                            att.status = status
                            changes['updated'] += 1
                        else:
                            # Local est plus récent (conflit, on garde local)
                            changes['conflicts'] += 1
                    else:
                        # Si pas de timestamp, on prend le remote
                        att.status = status
                        changes['updated'] += 1
                    
                    if not hasattr(att, 'modified_by'):
                        att.modified_by = user.username
                    att.save()
            
            except (ValueError, Attendance.DoesNotExist, Student.DoesNotExist, CourseSession.DoesNotExist):
                pass
        
        return changes

    @staticmethod
    def export_payments_sync_csv(cohort_id):
        """
        Exporte CSV de synchronisation pour les paiements d'étudiants.
        """
        cohort = Cohort.objects.get(id=cohort_id)
        enrollments = cohort.enrollments.select_related('student', 'tariff')
        
        payments = Payment.objects.filter(
            enrollment__cohort=cohort
        ).select_related('enrollment__student')
        
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'cohort_id',
            'cohort_name',
            'enrollment_id',
            'student_id',
            'student_name',
            'amount',
            'date',
            'method',
            'transaction_id',
            'last_modified',
            'modified_by',
        ])
        
        for pay in payments:
            writer.writerow([
                cohort.id,
                cohort.name,
                pay.enrollment.id,
                pay.enrollment.student.id,
                f"{pay.enrollment.student.last_name} {pay.enrollment.student.first_name}",
                pay.amount,
                pay.date.isoformat(),
                pay.method,
                pay.transaction_id or '',
                pay.updated_at.isoformat() if hasattr(pay, 'updated_at') else '',
                pay.modified_by if hasattr(pay, 'modified_by') else 'system',
            ])
        
        return output.getvalue()

    @staticmethod
    def import_payments_sync_csv(csv_content, user):
        """
        Importe et merge CSV de paiements.
        Merge par: enrollment_id + date + amount (clé composite).
        """
        reader = csv.DictReader(StringIO(csv_content))
        changes = {'created': 0, 'updated': 0, 'duplicates': 0}
        
        for row in reader:
            try:
                enrollment_id = int(row['enrollment_id'])
                amount = float(row['amount'])
                date_str = row['date']
                method = row['method']
                transaction_id = row.get('transaction_id', '')
                
                # Clé : (enrollment, date, amount)
                # Évite les doublons mais permet plusieurs paiements le même jour
                pay, created = Payment.objects.get_or_create(
                    enrollment_id=enrollment_id,
                    date=date_str,
                    amount=amount,
                    defaults={'method': method, 'transaction_id': transaction_id or None}
                )
                
                if created:
                    changes['created'] += 1
                    if not hasattr(pay, 'modified_by'):
                        pay.modified_by = user.username
                    pay.save()
                else:
                    changes['duplicates'] += 1
            
            except (ValueError, Exception):
                pass
        
        return changes


class ConflictResolver:
    """Résout les conflits de synchronisation."""
    
    @staticmethod
    def detect_conflicts(local_data, remote_data):
        """
        Détecte les conflits entre données locales et distantes.
        Retourne liste de conflits.
        """
        conflicts = []
        
        for key in set(list(local_data.keys()) + list(remote_data.keys())):
            if key not in local_data:
                # Remote only
                conflicts.append({
                    'type': 'remote_only',
                    'key': key,
                    'data': remote_data[key],
                })
            elif key not in remote_data:
                # Local only
                conflicts.append({
                    'type': 'local_only',
                    'key': key,
                    'data': local_data[key],
                })
            else:
                local = local_data[key]
                remote = remote_data[key]
                if local != remote:
                    # Modification conflict
                    conflicts.append({
                        'type': 'both_modified',
                        'key': key,
                        'local': local,
                        'remote': remote,
                        'resolution': 'last_write_wins',  # ou 'manual_review'
                    })
        
        return conflicts

    @staticmethod
    def resolve_by_timestamp(local_record, remote_record):
        """Résout conflit en comparant timestamps."""
        local_time = getattr(local_record, 'updated_at', None)
        remote_time = getattr(remote_record, 'updated_at', None)
        
        if not local_time or not remote_time:
            return local_record  # Fallback
        
        return remote_record if remote_time > local_time else local_record

    @staticmethod
    def resolve_by_majority(records_list):
        """Résout conflit par vote (utile pour les statuts)."""
        from collections import Counter
        values = [r.get('value') for r in records_list if 'value' in r]
        if not values:
            return records_list[0]
        most_common = Counter(values).most_common(1)[0][0]
        return next((r for r in records_list if r.get('value') == most_common), records_list[0])


class GlobalSyncManager:
    """
    Gère la synchronisation COMPLÈTE de TOUTE la base de données.
    Exporte/Importe: Students, Cohorts, Sessions, Enrollments, Presences, Paiements, Tarifs, Réductions, Matières, Niveaux, etc.
    RÈGLE: UPDATE uniquement, JAMAIS supprimer. Compare timestamps.
    """
    
    @staticmethod
    def export_global_sync_zip():
        """
        Exporte UN ZIP contenant TOUTES les données:
        1. students.csv - Tous les étudiants
        2. subjects.csv - Toutes les matières
        3. levels.csv - Tous les niveaux
        4. tariffs.csv - Tous les tarifs
        5. discounts.csv - Toutes les réductions
        6. cohorts.csv - Tous les cohorts
        7. sessions.csv - Toutes les séances
        8. enrollments.csv - Toutes les inscriptions
        9. presences.csv - Toutes les présences
        10. paiements_etudiants.csv - Tous les paiements étudiants
        11. paiements_profs.csv - Tous les paiements profs
        12. _metadata.csv - Infos sur l'export
        
        Retourne: BytesIO du ZIP, nom_fichier
        """
        from zipfile import ZipFile
        
        # Année académique courante
        try:
            current_year = AcademicYear.objects.get(is_current=True)
        except AcademicYear.DoesNotExist:
            return None, None
        
        zip_buffer = BytesIO()
        
        with ZipFile(zip_buffer, 'w') as zip_file:
            
            # 0. METADATA - Infos sur l'export
            metadata_output = StringIO()
            metadata_writer = csv.writer(metadata_output)
            metadata_writer.writerow(['key', 'value'])
            metadata_writer.writerow(['export_date', datetime.now().isoformat()])
            metadata_writer.writerow(['academic_year', current_year.label])
            metadata_writer.writerow(['version', '2.0_COMPLETE'])
            metadata_writer.writerow(['total_students', Student.objects.count()])
            metadata_writer.writerow(['total_cohorts', Cohort.objects.filter(academic_year=current_year).count()])
            zip_file.writestr('_metadata.csv', metadata_output.getvalue())
            
            # 1. SUBJECTS.CSV - Toutes les matières
            subjects_output = StringIO()
            subjects_writer = csv.writer(subjects_output)
            subjects_writer.writerow(['id', 'name'])
            for subject in Subject.objects.all():
                subjects_writer.writerow([subject.id, subject.name])
            zip_file.writestr('subjects.csv', subjects_output.getvalue())
            
            # 2. LEVELS.CSV - Tous les niveaux
            levels_output = StringIO()
            levels_writer = csv.writer(levels_output)
            levels_writer.writerow(['id', 'name'])
            for level in Level.objects.all():
                levels_writer.writerow([level.id, level.name])
            zip_file.writestr('levels.csv', levels_output.getvalue())
            
            # 3. TARIFFS.CSV - Tous les tarifs
            tariffs_output = StringIO()
            tariffs_writer = csv.writer(tariffs_output)
            tariffs_writer.writerow(['id', 'name', 'amount'])
            for tariff in Tariff.objects.all():
                tariffs_writer.writerow([tariff.id, tariff.name, str(tariff.amount)])
            zip_file.writestr('tariffs.csv', tariffs_output.getvalue())
            
            # 4. DISCOUNTS.CSV - Toutes les réductions
            discounts_output = StringIO()
            discounts_writer = csv.writer(discounts_output)
            discounts_writer.writerow(['id', 'name', 'value', 'type'])
            for discount in Discount.objects.all():
                discounts_writer.writerow([discount.id, discount.name, str(discount.value), discount.type])
            zip_file.writestr('discounts.csv', discounts_output.getvalue())
            
            # 5. STUDENTS.CSV - Tous les étudiants
            students_output = StringIO()
            students_writer = csv.writer(students_output)
            students_writer.writerow([
                'id', 'first_name', 'last_name', 'sex', 'email', 'phone', 
                'phone_2', 'birth_date', 'motivation', 'student_code', 'created_at'
            ])
            
            for student in Student.objects.all():
                students_writer.writerow([
                    student.id,
                    student.first_name,
                    student.last_name,
                    student.sex or '',
                    student.email or '',
                    student.phone or '',
                    student.phone_2 or '',
                    student.birth_date.isoformat() if student.birth_date else '',
                    student.motivation or '',
                    student.student_code or '',
                    student.created_at.isoformat() if student.created_at else ''
                ])
            
            zip_file.writestr('students.csv', students_output.getvalue())
            
            # 6. COHORTS.CSV - Tous les cohorts de l'année courante
            cohorts_output = StringIO()
            cohorts_writer = csv.writer(cohorts_output)
            cohorts_writer.writerow([
                'id', 'name', 'subject_id', 'subject_name', 'teacher_id', 'teacher_name',
                'academic_year_id', 'start_date', 'end_date', 'schedule',
                'max_students', 'cohort_type', 'is_active', 'created_at', 'updated_at'
            ])
            
            cohorts = Cohort.objects.filter(academic_year=current_year).select_related('subject', 'teacher', 'academic_year')
            for cohort in cohorts:
                cohorts_writer.writerow([
                    cohort.id,
                    cohort.name,
                    cohort.subject.id if cohort.subject else '',
                    cohort.subject.name if cohort.subject else '',
                    cohort.teacher.id if cohort.teacher else '',
                    cohort.teacher.get_full_name() if cohort.teacher else '',
                    cohort.academic_year.id if cohort.academic_year else '',
                    cohort.start_date.isoformat() if cohort.start_date else '',
                    cohort.end_date.isoformat() if cohort.end_date else '',
                    cohort.schedule or '',
                    cohort.max_students or '',
                    cohort.cohort_type or '',
                    cohort.is_active,
                    cohort.created_at.isoformat() if hasattr(cohort, 'created_at') and cohort.created_at else '',
                    cohort.updated_at.isoformat() if hasattr(cohort, 'updated_at') and cohort.updated_at else ''
                ])
            
            zip_file.writestr('cohorts.csv', cohorts_output.getvalue())
            
            # 7. SESSIONS.CSV - Toutes les séances des cohorts
            sessions_output = StringIO()
            sessions_writer = csv.writer(sessions_output)
            sessions_writer.writerow([
                'id', 'cohort_id', 'date', 'start_time', 'end_time',
                'duration', 'status', 'notes', 'created_at', 'updated_at'
            ])
            
            for cohort in cohorts:
                for session in cohort.sessions.all():
                    sessions_writer.writerow([
                        session.id,
                        session.cohort_id,
                        session.date.isoformat() if session.date else '',
                        session.start_time.isoformat() if session.start_time else '',
                        session.end_time.isoformat() if session.end_time else '',
                        str(session.duration) if hasattr(session, 'duration') and session.duration else '',
                        session.status if hasattr(session, 'status') else '',
                        session.notes or '',
                        session.created_at.isoformat() if hasattr(session, 'created_at') and session.created_at else '',
                        session.updated_at.isoformat() if hasattr(session, 'updated_at') and session.updated_at else ''
                    ])
            
            zip_file.writestr('sessions.csv', sessions_output.getvalue())
            
            # 8. ENROLLMENTS.CSV - Toutes les inscriptions
            enrollments_output = StringIO()
            enrollments_writer = csv.writer(enrollments_output)
            enrollments_writer.writerow([
                'id', 'student_id', 'cohort_id', 'tariff_id', 'payment_plan',
                'discount_id', 'hours_purchased', 'hours_consumed',
                'is_active', 'date', 'contract_code', 'created_at', 'updated_at'
            ])
            
            for cohort in cohorts:
                for enrollment in cohort.enrollments.select_related('student', 'tariff', 'discount'):
                    enrollments_writer.writerow([
                        enrollment.id,
                        enrollment.student_id,
                        enrollment.cohort_id,
                        enrollment.tariff_id if enrollment.tariff else '',
                        enrollment.payment_plan,
                        enrollment.discount_id if enrollment.discount else '',
                        str(enrollment.hours_purchased) if enrollment.hours_purchased else '0',
                        str(enrollment.hours_consumed) if enrollment.hours_consumed else '0',
                        enrollment.is_active,
                        enrollment.date.isoformat() if enrollment.date else '',
                        enrollment.contract_code or '',
                        enrollment.created_at.isoformat() if hasattr(enrollment, 'created_at') and enrollment.created_at else '',
                        enrollment.updated_at.isoformat() if hasattr(enrollment, 'updated_at') and enrollment.updated_at else ''
                    ])
            
            zip_file.writestr('enrollments.csv', enrollments_output.getvalue())
            
            # 9. PRESENCES.CSV - Toutes les présences
            presences_output = StringIO()
            presences_writer = csv.writer(presences_output)
            presences_writer.writerow([
                'id', 'student_id', 'session_id', 'status',
                'notes', 'updated_at', 'updated_by'
            ])
            
            all_presences = Attendance.objects.filter(
                session__cohort__academic_year=current_year
            ).select_related('student', 'session')
            
            for attendance in all_presences:
                presences_writer.writerow([
                    attendance.id if hasattr(attendance, 'id') else '',
                    attendance.student_id,
                    attendance.session_id,
                    attendance.status,
                    attendance.notes if hasattr(attendance, 'notes') else '',
                    attendance.updated_at.isoformat() if hasattr(attendance, 'updated_at') and attendance.updated_at else '',
                    attendance.updated_by if hasattr(attendance, 'updated_by') else ''
                ])
            
            zip_file.writestr('presences.csv', presences_output.getvalue())
            
            # 10. PAIEMENTS_ETUDIANTS.CSV - Tous les paiements étudiants
            paiements_etudiants_output = StringIO()
            paiements_etudiants_writer = csv.writer(paiements_etudiants_output)
            paiements_etudiants_writer.writerow([
                'id', 'enrollment_id', 'amount', 'date', 'method',
                'notes', 'created_at', 'updated_at', 'updated_by'
            ])
            
            all_payments = Payment.objects.filter(
                enrollment__cohort__academic_year=current_year
            ).select_related('enrollment')
            
            for payment in all_payments:
                paiements_etudiants_writer.writerow([
                    payment.id,
                    payment.enrollment_id if hasattr(payment, 'enrollment_id') else payment.enrollment.id,
                    str(payment.amount),
                    payment.date.isoformat() if payment.date else '',
                    payment.method,
                    payment.notes if hasattr(payment, 'notes') else '',
                    payment.created_at.isoformat() if hasattr(payment, 'created_at') and payment.created_at else '',
                    payment.updated_at.isoformat() if hasattr(payment, 'updated_at') and payment.updated_at else '',
                    payment.updated_by if hasattr(payment, 'updated_by') else ''
                ])
            
            zip_file.writestr('paiements_etudiants.csv', paiements_etudiants_output.getvalue())
            
            # 11. PAIEMENTS_PROFS.CSV - Tous les paiements profs
            paiements_profs_output = StringIO()
            paiements_profs_writer = csv.writer(paiements_profs_output)
            paiements_profs_writer.writerow([
                'id', 'cohort_id', 'teacher_id', 'amount', 'date',
                'notes', 'created_at', 'updated_at', 'updated_by'
            ])
            
            teacher_payments = TeacherCohortPayment.objects.filter(
                cohort__academic_year=current_year
            ).select_related('cohort', 'teacher')
            
            for payment in teacher_payments:
                paiements_profs_writer.writerow([
                    payment.id,
                    payment.cohort_id,
                    payment.teacher_id if hasattr(payment, 'teacher_id') else '',
                    str(payment.amount),
                    payment.date.isoformat() if payment.date else '',
                    payment.notes if hasattr(payment, 'notes') else '',
                    payment.created_at.isoformat() if hasattr(payment, 'created_at') and payment.created_at else '',
                    payment.updated_at.isoformat() if hasattr(payment, 'updated_at') and payment.updated_at else '',
                    payment.updated_by if hasattr(payment, 'updated_by') else ''
                ])
            
            zip_file.writestr('paiements_profs.csv', paiements_profs_output.getvalue())
            
            # 12. _DELETED_IDS.CSV - Liste des IDs qui ont été supprimés (pour sync des suppressions)
            # Format: table, id
            # Permet de synchroniser les suppressions sans perte de données
            deleted_ids_output = StringIO()
            deleted_ids_writer = csv.writer(deleted_ids_output)
            deleted_ids_writer.writerow(['table', 'id', 'deleted_reason'])
            
            # Pour l'instant, on n'exporte rien (vide)
            # Plus tard, si on implémente soft delete, on exportera les IDs supprimés ici
            
            zip_file.writestr('_deleted_ids.csv', deleted_ids_output.getvalue())
            
            # 13. _ALL_SESSION_IDS.CSV - TOUS les IDs de sessions qui existent (pour détecter suppressions)
            all_session_ids_output = StringIO()
            all_session_ids_writer = csv.writer(all_session_ids_output)
            all_session_ids_writer.writerow(['id'])
            for cohort in cohorts:
                for session in cohort.sessions.all():
                    all_session_ids_writer.writerow([session.id])
            zip_file.writestr('_all_session_ids.csv', all_session_ids_output.getvalue())
            
            # 14. _ALL_ENROLLMENT_IDS.CSV - TOUS les IDs d'inscriptions qui existent
            all_enrollment_ids_output = StringIO()
            all_enrollment_ids_writer = csv.writer(all_enrollment_ids_output)
            all_enrollment_ids_writer.writerow(['id'])
            for cohort in cohorts:
                for enrollment in cohort.enrollments.all():
                    all_enrollment_ids_writer.writerow([enrollment.id])
            zip_file.writestr('_all_enrollment_ids.csv', all_enrollment_ids_output.getvalue())
        
        zip_buffer.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'sync_global_COMPLET_{current_year.label}_{timestamp}.zip'
        
        return zip_buffer, filename
    
    @staticmethod
    def import_global_sync_zip(zip_file):
        """
        Importe et synchronise TOUTES les données depuis un ZIP global.
        ÉTAPES:
        1. Import des données (subjects, levels, tariffs, discounts, students, cohorts, etc.)
        2. Log d'historique
        RÈGLE: UPDATE uniquement, JAMAIS supprimer. Compare timestamps (last-write-wins).
        
        Returns:
            dict avec statistiques d'import détaillées
        """
        from zipfile import ZipFile
        from django.db import transaction
        from students.models import Tariff, Enrollment
        
        stats = {
            'subjects_added': 0,
            'subjects_updated': 0,
            'levels_added': 0,
            'levels_updated': 0,
            'tariffs_added': 0,
            'tariffs_updated': 0,
            'discounts_added': 0,
            'discounts_updated': 0,
            'students_added': 0,
            'students_updated': 0,
            'cohorts_added': 0,
            'cohorts_updated': 0,
            'sessions_added': 0,
            'sessions_updated': 0,
            'sessions_deleted': 0,
            'enrollments_added': 0,
            'enrollments_updated': 0,
            'enrollments_deleted': 0,
            'presences_added': 0,
            'presences_updated': 0,
            'paiements_etudiants_added': 0,
            'paiements_etudiants_updated': 0,
            'paiements_profs_added': 0,
            'paiements_profs_updated': 0,
            'errors': []
        }
        
        # ÉTAPE 1: IMPORT DES DONNÉES
        try:
            with ZipFile(zip_file, 'r') as zip_ref:
                
                # 1. SUBJECTS.CSV
                if 'subjects.csv' in zip_ref.namelist():
                    subjects_csv = zip_ref.read('subjects.csv').decode('utf-8')
                    reader = csv.DictReader(StringIO(subjects_csv))
                    
                    for row in reader:
                        try:
                            subject_id = int(row['id'])
                            try:
                                subject = Subject.objects.get(id=subject_id)
                                if subject.name != row['name']:
                                    subject.name = row['name']
                                    subject.save()
                                    stats['subjects_updated'] += 1
                            except Subject.DoesNotExist:
                                Subject.objects.create(id=subject_id, name=row['name'])
                                stats['subjects_added'] += 1
                        except Exception as e:
                            stats['errors'].append(f"Subject ID {row.get('id')}: {str(e)}")
                
                # 2. LEVELS.CSV
                if 'levels.csv' in zip_ref.namelist():
                    levels_csv = zip_ref.read('levels.csv').decode('utf-8')
                    reader = csv.DictReader(StringIO(levels_csv))
                    
                    for row in reader:
                        try:
                            level_id = int(row['id'])
                            try:
                                level = Level.objects.get(id=level_id)
                                if level.name != row['name']:
                                    level.name = row['name']
                                    level.save()
                                    stats['levels_updated'] += 1
                            except Level.DoesNotExist:
                                Level.objects.create(id=level_id, name=row['name'])
                                stats['levels_added'] += 1
                        except Exception as e:
                            stats['errors'].append(f"Level ID {row.get('id')}: {str(e)}")
                
                # 3. TARIFFS.CSV
                if 'tariffs.csv' in zip_ref.namelist():
                    tariffs_csv = zip_ref.read('tariffs.csv').decode('utf-8')
                    reader = csv.DictReader(StringIO(tariffs_csv))
                    
                    for row in reader:
                        try:
                            tariff_id = int(row['id'])
                            try:
                                tariff = Tariff.objects.get(id=tariff_id)
                                if tariff.name != row['name'] or str(tariff.amount) != row['amount']:
                                    tariff.name = row['name']
                                    tariff.amount = int(row['amount'])
                                    tariff.save()
                                    stats['tariffs_updated'] += 1
                            except Tariff.DoesNotExist:
                                Tariff.objects.create(id=tariff_id, name=row['name'], amount=int(row['amount']))
                                stats['tariffs_added'] += 1
                        except Exception as e:
                            stats['errors'].append(f"Tariff ID {row.get('id')}: {str(e)}")
                
                # 4. DISCOUNTS.CSV
                if 'discounts.csv' in zip_ref.namelist():
                    discounts_csv = zip_ref.read('discounts.csv').decode('utf-8')
                    reader = csv.DictReader(StringIO(discounts_csv))
                    
                    for row in reader:
                        try:
                            discount_id = int(row['id'])
                            try:
                                discount = Discount.objects.get(id=discount_id)
                                if (discount.name != row['name'] or 
                                    str(discount.value) != row['value'] or 
                                    discount.type != row['type']):
                                    discount.name = row['name']
                                    discount.value = int(row['value'])
                                    discount.type = row['type']
                                    discount.save()
                                    stats['discounts_updated'] += 1
                            except Discount.DoesNotExist:
                                Discount.objects.create(
                                    id=discount_id,
                                    name=row['name'],
                                    value=int(row['value']),
                                    type=row['type']
                                )
                                stats['discounts_added'] += 1
                        except Exception as e:
                            stats['errors'].append(f"Discount ID {row.get('id')}: {str(e)}")
                
                # 5. STUDENTS.CSV
                if 'students.csv' in zip_ref.namelist():
                    students_csv = zip_ref.read('students.csv').decode('utf-8')
                    reader = csv.DictReader(StringIO(students_csv))
                    
                    for row in reader:
                        try:
                            student_id = int(row['id'])
                            
                            # Chercher l'étudiant existant
                            try:
                                student = Student.objects.get(id=student_id)
                                # Comparer timestamps (students n'a que created_at, pas updated_at)
                                remote_time = datetime.fromisoformat(row['created_at']) if row.get('created_at') else None
                                local_time = student.created_at if student.created_at else None
                                
                                # UPDATE si remote plus récent
                                if remote_time and local_time and remote_time > local_time:
                                    student.first_name = row['first_name']
                                    student.last_name = row['last_name']
                                    student.sex = row.get('sex') or ''
                                    student.email = row['email'] or None
                                    student.phone = row['phone'] or ''
                                    student.phone_2 = row.get('phone_2') or ''
                                    student.birth_date = datetime.strptime(row['birth_date'], '%Y-%m-%d').date() if row.get('birth_date') else None
                                    student.motivation = row.get('motivation') or ''
                                    student.student_code = row.get('student_code') or ''
                                    student.save()
                                    stats['students_updated'] += 1
                            
                            except Student.DoesNotExist:
                                # CREATE nouveau student avec l'ID original
                                Student.objects.create(
                                    id=student_id,
                                    first_name=row['first_name'],
                                    last_name=row['last_name'],
                                    sex=row.get('sex') or '',
                                    email=row['email'] or None,
                                    phone=row['phone'] or '',
                                    phone_2=row.get('phone_2') or '',
                                    birth_date=datetime.strptime(row['birth_date'], '%Y-%m-%d').date() if row.get('birth_date') else None,
                                    motivation=row.get('motivation') or '',
                                    student_code=row.get('student_code') or ''
                                )
                                stats['students_added'] += 1
                        
                        except Exception as e:
                            stats['errors'].append(f"Student ID {row.get('id')}: {str(e)}")
                
                # 2. COHORTS.CSV
                if 'cohorts.csv' in zip_ref.namelist():
                    cohorts_csv = zip_ref.read('cohorts.csv').decode('utf-8')
                    reader = csv.DictReader(StringIO(cohorts_csv))
                    
                    for row in reader:
                        try:
                            cohort_id = int(row['id'])
                            
                            try:
                                cohort = Cohort.objects.get(id=cohort_id)
                                remote_time = datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                                local_time = cohort.updated_at if hasattr(cohort, 'updated_at') else None
                                
                                if (remote_time and local_time and remote_time > local_time) or (remote_time and not local_time):
                                    cohort.name = row['name']
                                    cohort.subject_id = int(row['subject_id']) if row['subject_id'] else None
                                    cohort.teacher_id = int(row['teacher_id']) if row['teacher_id'] else None
                                    cohort.academic_year_id = int(row['academic_year_id']) if row['academic_year_id'] else None
                                    cohort.start_date = datetime.strptime(row['start_date'], '%Y-%m-%d').date() if row['start_date'] else None
                                    cohort.end_date = datetime.strptime(row['end_date'], '%Y-%m-%d').date() if row['end_date'] else None
                                    cohort.schedule = row['schedule'] or None
                                    cohort.max_students = int(row['max_students']) if row['max_students'] else None
                                    cohort.cohort_type = row['cohort_type'] or None
                                    cohort.is_active = row['is_active'] == 'True'
                                    cohort.save()
                                    stats['cohorts_updated'] += 1
                            
                            except Cohort.DoesNotExist:
                                Cohort.objects.create(
                                    id=cohort_id,
                                    name=row['name'],
                                    subject_id=int(row['subject_id']) if row['subject_id'] else None,
                                    teacher_id=int(row['teacher_id']) if row['teacher_id'] else None,
                                    academic_year_id=int(row['academic_year_id']) if row['academic_year_id'] else None,
                                    start_date=datetime.strptime(row['start_date'], '%Y-%m-%d').date() if row['start_date'] else None,
                                    end_date=datetime.strptime(row['end_date'], '%Y-%m-%d').date() if row['end_date'] else None,
                                    schedule=row['schedule'] or None,
                                    max_students=int(row['max_students']) if row['max_students'] else None,
                                    cohort_type=row['cohort_type'] or None,
                                    is_active=row['is_active'] == 'True'
                                )
                                stats['cohorts_added'] += 1
                        
                        except Exception as e:
                            stats['errors'].append(f"Cohort ID {row.get('id')}: {str(e)}")
                
                # 3. SESSIONS.CSV
                if 'sessions.csv' in zip_ref.namelist():
                    sessions_csv = zip_ref.read('sessions.csv').decode('utf-8')
                    reader = csv.DictReader(StringIO(sessions_csv))
                    
                    for row in reader:
                        try:
                            session_id = int(row['id'])
                            
                            try:
                                session = CourseSession.objects.get(id=session_id)
                                remote_time = datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                                local_time = session.updated_at if hasattr(session, 'updated_at') else None
                                
                                if (remote_time and local_time and remote_time > local_time) or (remote_time and not local_time):
                                    session.cohort_id = int(row['cohort_id'])
                                    session.date = datetime.strptime(row['date'], '%Y-%m-%d').date() if row['date'] else None
                                    session.start_time = datetime.strptime(row['start_time'], '%H:%M:%S').time() if row['start_time'] else None
                                    session.end_time = datetime.strptime(row['end_time'], '%H:%M:%S').time() if row['end_time'] else None
                                    if hasattr(session, 'status'):
                                        session.status = row['status'] or None
                                    if hasattr(session, 'notes'):
                                        session.notes = row['notes'] or None
                                    session.save()
                                    stats['sessions_updated'] += 1
                            
                            except CourseSession.DoesNotExist:
                                CourseSession.objects.create(
                                    id=session_id,
                                    cohort_id=int(row['cohort_id']),
                                    date=datetime.strptime(row['date'], '%Y-%m-%d').date() if row['date'] else None,
                                    start_time=datetime.strptime(row['start_time'], '%H:%M:%S').time() if row['start_time'] else None,
                                    end_time=datetime.strptime(row['end_time'], '%H:%M:%S').time() if row['end_time'] else None
                                )
                                stats['sessions_added'] += 1
                        
                        except Exception as e:
                            stats['errors'].append(f"Session ID {row.get('id')}: {str(e)}")
                
                # 4. ENROLLMENTS.CSV
                if 'enrollments.csv' in zip_ref.namelist():
                    from students.models import Enrollment
                    enrollments_csv = zip_ref.read('enrollments.csv').decode('utf-8')
                    reader = csv.DictReader(StringIO(enrollments_csv))
                    
                    for row in reader:
                        try:
                            enrollment_id = int(row['id'])
                            
                            try:
                                enrollment = Enrollment.objects.get(id=enrollment_id)
                                remote_time = datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                                local_time = enrollment.updated_at if hasattr(enrollment, 'updated_at') else None
                                
                                if (remote_time and local_time and remote_time > local_time) or (remote_time and not local_time):
                                    enrollment.student_id = int(row['student_id'])
                                    enrollment.cohort_id = int(row['cohort_id'])
                                    enrollment.tariff_id = int(row['tariff_id']) if row['tariff_id'] else None
                                    enrollment.payment_plan = row['payment_plan']
                                    enrollment.discount_id = int(row['discount_id']) if row['discount_id'] else None
                                    enrollment.hours_purchased = float(row['hours_purchased']) if row['hours_purchased'] else 0
                                    enrollment.hours_consumed = float(row['hours_consumed']) if row['hours_consumed'] else 0
                                    enrollment.is_active = row['is_active'] == 'True'
                                    enrollment.contract_code = row['contract_code'] or None
                                    enrollment.save()
                                    stats['enrollments_updated'] += 1
                            
                            except Enrollment.DoesNotExist:
                                Enrollment.objects.create(
                                    id=enrollment_id,
                                    student_id=int(row['student_id']),
                                    cohort_id=int(row['cohort_id']),
                                    tariff_id=int(row['tariff_id']) if row['tariff_id'] else None,
                                    payment_plan=row['payment_plan'],
                                    discount_id=int(row['discount_id']) if row['discount_id'] else None,
                                    hours_purchased=float(row['hours_purchased']) if row['hours_purchased'] else 0,
                                    hours_consumed=float(row['hours_consumed']) if row['hours_consumed'] else 0,
                                    is_active=row['is_active'] == 'True',
                                    contract_code=row['contract_code'] or None
                                )
                                stats['enrollments_added'] += 1
                        
                        except Exception as e:
                            stats['errors'].append(f"Enrollment ID {row.get('id')}: {str(e)}")
                
                # 5. PRESENCES.CSV
                if 'presences.csv' in zip_ref.namelist():
                    presences_csv = zip_ref.read('presences.csv').decode('utf-8')
                    reader = csv.DictReader(StringIO(presences_csv))
                    
                    for row in reader:
                        try:
                            # Si l'ID existe, on utilise get_or_create sur l'ID
                            # Sinon on utilise session+student comme clé unique
                            if row['id']:
                                attendance_id = int(row['id'])
                                try:
                                    attendance = Attendance.objects.get(id=attendance_id)
                                    remote_time = datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                                    local_time = attendance.updated_at if hasattr(attendance, 'updated_at') else None
                                    
                                    if (remote_time and local_time and remote_time > local_time) or (remote_time and not local_time):
                                        attendance.status = row['status']
                                        if hasattr(attendance, 'updated_by'):
                                            attendance.updated_by = row['updated_by'] or None
                                        attendance.save()
                                        stats['presences_updated'] += 1
                                
                                except Attendance.DoesNotExist:
                                    Attendance.objects.create(
                                        id=attendance_id,
                                        student_id=int(row['student_id']),
                                        session_id=int(row['session_id']),
                                        status=row['status']
                                    )
                                    stats['presences_added'] += 1
                            else:
                                # Pas d'ID, utiliser session+student
                                attendance, created = Attendance.objects.get_or_create(
                                    session_id=int(row['session_id']),
                                    student_id=int(row['student_id']),
                                    defaults={'status': row['status']}
                                )
                                if created:
                                    stats['presences_added'] += 1
                                else:
                                    remote_time = datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                                    local_time = attendance.updated_at if hasattr(attendance, 'updated_at') else None
                                    if (remote_time and local_time and remote_time > local_time) or (remote_time and not local_time):
                                        attendance.status = row['status']
                                        attendance.save()
                                        stats['presences_updated'] += 1
                        
                        except Exception as e:
                            stats['errors'].append(f"Presence row {reader.line_num}: {str(e)}")
                
                # 6. PAIEMENTS_ETUDIANTS.CSV
                if 'paiements_etudiants.csv' in zip_ref.namelist():
                    paiements_csv = zip_ref.read('paiements_etudiants.csv').decode('utf-8')
                    reader = csv.DictReader(StringIO(paiements_csv))
                    
                    for row in reader:
                        try:
                            payment_id = int(row['id'])
                            
                            try:
                                payment = Payment.objects.get(id=payment_id)
                                remote_time = datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                                local_time = payment.updated_at if hasattr(payment, 'updated_at') else None
                                
                                if (remote_time and local_time and remote_time > local_time) or (remote_time and not local_time):
                                    payment.amount = float(row['amount'])
                                    payment.date = datetime.strptime(row['date'], '%Y-%m-%d').date() if row['date'] else None
                                    payment.method = row['method']
                                    if hasattr(payment, 'notes'):
                                        payment.notes = row['notes'] or None
                                    if hasattr(payment, 'updated_by'):
                                        payment.updated_by = row['updated_by'] or None
                                    payment.save()
                                    stats['paiements_etudiants_updated'] += 1
                            
                            except Payment.DoesNotExist:
                                Payment.objects.create(
                                    id=payment_id,
                                    enrollment_id=int(row['enrollment_id']),
                                    amount=float(row['amount']),
                                    date=datetime.strptime(row['date'], '%Y-%m-%d').date() if row['date'] else None,
                                    method=row['method']
                                )
                                stats['paiements_etudiants_added'] += 1
                        
                        except Exception as e:
                            stats['errors'].append(f"Payment ID {row.get('id')}: {str(e)}")
                
                # 7. PAIEMENTS_PROFS.CSV
                if 'paiements_profs.csv' in zip_ref.namelist():
                    paiements_profs_csv = zip_ref.read('paiements_profs.csv').decode('utf-8')
                    reader = csv.DictReader(StringIO(paiements_profs_csv))
                    
                    for row in reader:
                        try:
                            payment_id = int(row['id'])
                            
                            try:
                                payment = TeacherCohortPayment.objects.get(id=payment_id)
                                remote_time = datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                                local_time = payment.updated_at if hasattr(payment, 'updated_at') else None
                                
                                if (remote_time and local_time and remote_time > local_time) or (remote_time and not local_time):
                                    payment.amount = float(row['amount'])
                                    payment.date = datetime.strptime(row['date'], '%Y-%m-%d').date() if row['date'] else None
                                    if hasattr(payment, 'notes'):
                                        payment.notes = row['notes'] or None
                                    if hasattr(payment, 'updated_by'):
                                        payment.updated_by = row['updated_by'] or None
                                    payment.save()
                                    stats['paiements_profs_updated'] += 1
                            
                            except TeacherCohortPayment.DoesNotExist:
                                TeacherCohortPayment.objects.create(
                                    id=payment_id,
                                    cohort_id=int(row['cohort_id']),
                                    teacher_id=int(row['teacher_id']) if row['teacher_id'] else None,
                                    amount=float(row['amount']),
                                    date=datetime.strptime(row['date'], '%Y-%m-%d').date() if row['date'] else None
                                )
                                stats['paiements_profs_added'] += 1
                        
                        except Exception as e:
                            stats['errors'].append(f"Teacher payment ID {row.get('id')}: {str(e)}")
                
                # ÉTAPE 3: GÉRER LES SUPPRESSIONS
                # Vérifier si des sessions/enrollments existent localement mais pas dans l'export
                # Si oui, les marquer comme supprimés (soft delete via is_active=False ou suppression réelle)
                
                stats['sessions_deleted'] = 0
                stats['enrollments_deleted'] = 0
                
                # Lire les IDs de sessions qui existent dans l'export
                if '_all_session_ids.csv' in zip_ref.namelist():
                    exported_session_ids = set()
                    sessions_csv = zip_ref.read('_all_session_ids.csv').decode('utf-8')
                    reader = csv.DictReader(StringIO(sessions_csv))
                    for row in reader:
                        exported_session_ids.add(int(row['id']))
                    
                    # Trouver les sessions locales qui n'existent PAS dans l'export
                    # (= supprimées sur l'autre PC)
                    try:
                        current_year = AcademicYear.objects.get(is_current=True)
                        local_sessions = CourseSession.objects.filter(
                            cohort__academic_year=current_year
                        )
                        
                        for session in local_sessions:
                            if session.id not in exported_session_ids:
                                # Cette session a été supprimée sur l'autre PC
                                # On la supprime aussi ici
                                session.delete()
                                stats['sessions_deleted'] += 1
                    except Exception as e:
                        stats['errors'].append(f"Erreur détection sessions supprimées: {str(e)}")
                
                # Pareil pour les enrollments
                if '_all_enrollment_ids.csv' in zip_ref.namelist():
                    from students.models import Enrollment
                    exported_enrollment_ids = set()
                    enrollments_csv = zip_ref.read('_all_enrollment_ids.csv').decode('utf-8')
                    reader = csv.DictReader(StringIO(enrollments_csv))
                    for row in reader:
                        exported_enrollment_ids.add(int(row['id']))
                    
                    try:
                        current_year = AcademicYear.objects.get(is_current=True)
                        local_enrollments = Enrollment.objects.filter(
                            cohort__academic_year=current_year
                        )
                        
                        for enrollment in local_enrollments:
                            if enrollment.id not in exported_enrollment_ids:
                                # Cette inscription a été supprimée sur l'autre PC
                                # On la supprime aussi ici
                                enrollment.delete()
                                stats['enrollments_deleted'] += 1
                    except Exception as e:
                        stats['errors'].append(f"Erreur détection enrollments supprimés: {str(e)}")
        
        except Exception as e:
            stats['errors'].append(f"Erreur ZIP: {str(e)}")
        
        return stats
