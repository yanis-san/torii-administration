"""
Commande Django pour restaurer une sauvegarde COMPLÈTE (DB + fichiers médias).

Usage:
    python manage.py restore_data backup_complet_db_20260129_143025.tar.gz          # Depuis OneDrive
    python manage.py restore_data "C:\Backups\backup_complet_db_20260129_143025.tar.gz"  # Chemin absolu
    python manage.py restore_data "./backup_complet_db_20260129_143025.tar.gz"      # Chemin relatif
    python manage.py restore_data backup_complet_db_20260129_143025.tar.gz --force  # Sans confirmation
"""

import os
import subprocess
import json
import gzip
import shutil
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = "Restaure une sauvegarde COMPLÈTE (DB + fichiers médias)"

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            type=str,
            nargs='?',
            help='Nom ou chemin du fichier de backup à restaurer',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Restaurer sans confirmation',
        )

    def handle(self, *args, **options):
        # Infos base de données
        self.db_name = settings.DATABASES['default']['NAME']
        self.db_user = settings.DATABASES['default']['USER']
        self.db_host = settings.DATABASES['default']['HOST']
        self.db_port = settings.DATABASES['default']['PORT']
        self.db_password = settings.DATABASES['default']['PASSWORD']
        
        # Dossier de base du projet
        self.base_dir = settings.BASE_DIR
        self.media_root = settings.MEDIA_ROOT
        
        # Dossier OneDrive par défaut
        self.onedrive_backup_dir = Path(r"C:\Users\Social Media Manager\OneDrive\Torii-management\backups")

        # Trouver le fichier de backup
        backup_file_path = self._find_backup_file(options['backup_file'])
        
        if not backup_file_path:
            raise CommandError('❌ Fichier de backup non trouvé')

        self.stdout.write(self.style.WARNING(f'⚠️  Restauration du backup: {backup_file_path.name}'))
        
        # Vérifier l'intégrité
        metadata = self._verify_backup_integrity(backup_file_path)
        
        # Demander une confirmation
        if not options['force']:
            confirmation = input('\n⚠️  ATTENTION: Cette action va REMPLACER la base de données ET les fichiers médias actuels. Êtes-vous sûr? (yes/no): ')
            if confirmation.lower() != 'yes':
                self.stdout.write(self.style.WARNING('❌ Restauration annulée'))
                return

        # Restaurer la sauvegarde
        self._restore_backup(backup_file_path)
        
        # Vérifier que tout s'est bien passé
        self._verify_restoration()

    def _find_backup_file(self, backup_filename):
        """Trouve le fichier de backup en cherchant dans plusieurs emplacements"""
        if not backup_filename:
            # Si aucun nom donné, prendre le dernier backup OneDrive
            backups = sorted(self.onedrive_backup_dir.glob('backup_complet_*.tar.gz'))
            if not backups:
                return None
            return backups[-1]
        
        # Convertir en Path
        backup_path = Path(backup_filename)
        
        # Mode 1: Chemin absolu ou relatif
        if backup_path.exists():
            return backup_path.resolve()
        
        # Mode 2: Chercher dans OneDrive
        onedrive_path = self.onedrive_backup_dir / backup_filename
        if onedrive_path.exists():
            return onedrive_path
        
        # Mode 3: Chercher le fichier par nom dans le répertoire courant
        current_path = Path.cwd() / backup_filename
        if current_path.exists():
            return current_path
        
        return None

    def _verify_backup_integrity(self, backup_file_path):
        """Vérifie l'intégrité du backup et retourne les métadonnées"""
        metadata_file = backup_file_path.parent / backup_file_path.name.replace('.tar.gz', '.json')
        
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
            self.stdout.write(f'✅ Métadonnées trouvées')
            self.stdout.write(f'   📦 Type: {metadata.get("type", "N/A")}')
            self.stdout.write(f'   📋 Contient: {", ".join(metadata.get("includes", []))}')
            self.stdout.write(f'   ⏰ Créé: {metadata.get("datetime", "N/A")}')
            self.stdout.write(f'   💾 Taille: {metadata.get("size_mb", "N/A")} MB')
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  Métadonnées non trouvées'))
        
        return metadata

    def _restore_backup(self, backup_file_path):
        """Restaure la sauvegarde complète"""
        temp_dir = Path(tempfile.gettempdir()) / f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            self.stdout.write('\n🔄 Restauration en cours...')
            
            # ============ ÉTAPE 1: Extraire l'archive ============
            self.stdout.write('📦 [1/3] Extraction de l\'archive...')
            self._extract_tar_archive(backup_file_path, temp_dir)
            
            # ============ ÉTAPE 2: Restaurer la base de données ============
            self.stdout.write('🗄️  [2/3] Restauration de la base de données...')
            db_file = temp_dir / f"database_{self.db_name}.sql"
            if db_file.exists():
                self._restore_database(db_file)
            else:
                self.stdout.write(self.style.WARNING('⚠️  Fichier base de données non trouvé dans l\'archive'))
            
            # ============ ÉTAPE 3: Restaurer les fichiers médias ============
            self.stdout.write('📁 [3/3] Restauration des fichiers médias...')
            self._restore_media_files(temp_dir)
            
            # Succès
            self.stdout.write(self.style.SUCCESS(f'\n✅ RESTAURATION COMPLÈTE RÉUSSIE!'))
            
        except Exception as e:
            raise CommandError(f'❌ Erreur lors de la restauration: {str(e)}')
        finally:
            # Nettoyer les fichiers temporaires
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def _extract_tar_archive(self, archive_path, extract_to):
        """Extrait l'archive TAR.GZ"""
        extract_to.mkdir(parents=True, exist_ok=True)
        
        try:
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(path=extract_to)
            self.stdout.write(f'   ✅ Archive extraite: {extract_to.name}')
        except Exception as e:
            raise CommandError(f'❌ Erreur lors de l\'extraction: {e}')

    def _restore_database(self, db_file):
        """Restaure la base de données PostgreSQL"""
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_password

        restore_cmd = [
            'pg_restore',
            '-h', self.db_host,
            '-U', self.db_user,
            '-p', str(self.db_port),
            '-d', self.db_name,
            '--clean',  # Nettoyer les objets existants
            '--if-exists',  # Ne pas errorer si l'objet existe
            str(db_file)
        ]

        try:
            result = subprocess.run(
                restore_cmd,
                env=env,
                capture_output=True,
                check=True
            )
            self.stdout.write(f'   ✅ Base de données restaurée')
        except subprocess.CalledProcessError as e:
            raise CommandError(f'❌ Erreur lors de la restauration DB: {e.stderr.decode()}')

    def _restore_media_files(self, temp_dir):
        """Restaure les fichiers médias"""
        media_src = temp_dir / 'media'
        
        if not media_src.exists():
            self.stdout.write('   ℹ️  Aucun dossier médias à restaurer')
            return
        
        # Nettoyer le dossier médias actuel (optionnel mais recommandé)
        if self.media_root.exists():
            self.stdout.write(f'   🗑️  Suppression des anciens fichiers médias...')
            shutil.rmtree(self.media_root)
        
        # Copier les nouveaux fichiers
        self.media_root.mkdir(parents=True, exist_ok=True)
        
        file_count = 0
        total_size = 0
        
        for item in media_src.rglob('*'):
            if item.is_file():
                relative_path = item.relative_to(media_src)
                dest_file = self.media_root / relative_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_file)
                file_count += 1
                total_size += item.stat().st_size
        
        total_size_mb = total_size / (1024 * 1024)
        self.stdout.write(f'   ✅ {file_count} fichiers médias restaurés ({total_size_mb:.2f} MB)')

    def _verify_restoration(self):
        """Vérifie que la restauration s'est bien déroulée"""
        self.stdout.write('\n🔍 Vérification de la restauration...')
        
        try:
            # Vérifier la base de données
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM django_migrations")
                migration_count = cursor.fetchone()[0]
                self.stdout.write(f'   ✅ Base de données opérationnelle ({migration_count} migrations)')
            
            # Vérifier les fichiers médias
            if self.media_root.exists():
                media_files = list(self.media_root.rglob('*'))
                file_count = len([f for f in media_files if f.is_file()])
                self.stdout.write(f'   ✅ Dossier médias opérationnel ({file_count} fichiers)')
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️  Impossible de vérifier complètement: {e}'))
