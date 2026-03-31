"""
Commande Django personnalisée pour sauvegarder et restaurer la base de données PostgreSQL.

Usage:
    python manage.py db_backup              # Sauvegarder
    python manage.py db_backup --restore    # Restaurer le dernier backup
    python manage.py db_backup --list       # Lister les backups
    python manage.py db_backup --info       # Info sur les backups
"""

import os
import subprocess
import json
import hashlib
import gzip
import shutil
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = "Sauvegarde et restaure la base de données PostgreSQL"

    def add_arguments(self, parser):
        parser.add_argument(
            '--restore',
            action='store_true',
            help='Restaurer le dernier backup',
        )
        parser.add_argument(
            '--restore-file',
            type=str,
            help='Restaurer un fichier spécifique du dossier OneDrive',
        )
        parser.add_argument(
            '--restore-path',
            type=str,
            help='Restaurer depuis un chemin absolu ou relatif (ex: C:\\Backup\\backup.sql.gz ou ./backup.sql.gz)',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='Lister tous les backups',
        )
        parser.add_argument(
            '--info',
            action='store_true',
            help='Afficher les infos sur les backups',
        )
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Vérifier l\'intégrité du dernier backup',
        )

    def handle(self, *args, **options):
        # Créer le dossier OneDrive s'il n'existe pas
        self.backup_dir = Path(r"C:\Users\Social Media Manager\OneDrive\Torii-management\backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Infos base de données
        self.db_name = settings.DATABASES['default']['NAME']
        self.db_user = settings.DATABASES['default']['USER']
        self.db_host = settings.DATABASES['default']['HOST']
        self.db_port = settings.DATABASES['default']['PORT']
        self.db_password = settings.DATABASES['default']['PASSWORD']

        if options['restore']:
            self.restore_backup()
        elif options['restore_file']:
            self.restore_backup(filename=options['restore_file'])
        elif options['restore_path']:
            self.restore_backup(filepath=options['restore_path'])
        elif options['list']:
            self.list_backups()
        elif options['info']:
            self.backup_info()
        elif options['verify']:
            self.verify_backup()
        else:
            self.create_backup()

    def create_backup(self):
        """Crée une sauvegarde de la base de données"""
        self.stdout.write(self.style.SUCCESS('🔄 Début de la sauvegarde...'))

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f"backup_{self.db_name}_{timestamp}.sql"
        backup_gz = self.backup_dir / f"backup_{self.db_name}_{timestamp}.sql.gz"

        # Variables d'environnement pour pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_password

        try:
            # Commande pg_dump
            self.stdout.write(f'📦 Dump de la base de données...')
            dump_cmd = [
                'pg_dump',
                '-h', self.db_host,
                '-U', self.db_user,
                '-p', str(self.db_port),
                '-Fc',  # Format custom (binaire, plus efficace)
                self.db_name
            ]

            with open(backup_file, 'wb') as f:
                result = subprocess.run(
                    dump_cmd,
                    env=env,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    check=True
                )

            # Compresser le fichier
            self.stdout.write(f'📦 Compression du fichier...')
            with open(backup_file, 'rb') as f_in:
                with gzip.open(backup_gz, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Supprimer le fichier non compressé
            backup_file.unlink()

            # Calculer le hash
            file_hash = self._calculate_hash(backup_gz)

            # Créer un fichier de metadata
            metadata = {
                'backup_file': backup_gz.name,
                'timestamp': timestamp,
                'datetime': datetime.now().isoformat(),
                'database': self.db_name,
                'size_bytes': backup_gz.stat().st_size,
                'hash': file_hash,
                'status': 'completed'
            }

            metadata_file = self.backup_dir / f"backup_{self.db_name}_{timestamp}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            # Afficher les infos
            size_mb = backup_gz.stat().st_size / (1024 * 1024)
            self.stdout.write(self.style.SUCCESS(f'✅ Sauvegarde réussie!'))
            self.stdout.write(f'   📁 Fichier: {backup_gz.name}')
            self.stdout.write(f'   💾 Taille: {size_mb:.2f} MB')
            self.stdout.write(f'   🔐 Hash: {file_hash[:16]}...')
            self.stdout.write(f'   📍 Localisation: {backup_gz}')

        except subprocess.CalledProcessError as e:
            raise CommandError(f'❌ Erreur lors du dump: {e.stderr.decode()}')
        except Exception as e:
            raise CommandError(f'❌ Erreur: {str(e)}')

    def restore_backup(self, filename=None, filepath=None):
        """Restaure une sauvegarde
        
        Args:
            filename: Nom du fichier dans le dossier OneDrive
            filepath: Chemin absolu ou relatif vers le fichier de backup
        """
        
        # Trouver le fichier de backup
        if filepath:
            # Mode: chemin absolu ou relatif
            backup_file = Path(filepath).resolve()
            if not backup_file.exists():
                raise CommandError(f'❌ Fichier non trouvé: {filepath}')
            self.stdout.write(f'📂 Backup trouvé: {backup_file}')
        elif filename:
            # Mode: fichier dans le dossier OneDrive
            backup_file = self.backup_dir / filename
            if not backup_file.exists():
                raise CommandError(f'❌ Fichier non trouvé: {filename}')
        else:
            # Mode: dernier backup du dossier OneDrive
            backups = sorted(self.backup_dir.glob('backup_*.sql.gz'))
            if not backups:
                raise CommandError('❌ Aucune sauvegarde trouvée')
            backup_file = backups[-1]

        self.stdout.write(self.style.WARNING(f'⚠️  Restauration du backup: {backup_file.name}'))
        
        # Vérifier l'intégrité
        metadata_file = backup_file.parent / backup_file.name.replace('.sql.gz', '.json')
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
            stored_hash = metadata.get('hash')
            current_hash = self._calculate_hash(backup_file)
            if stored_hash != current_hash:
                raise CommandError(f'❌ Erreur d\'intégrité! Le backup a été corrompu.')
            self.stdout.write(f'✅ Intégrité vérifiée (hash: {current_hash[:16]}...)')
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  Métadonnées non trouvées. Vérification du hash impossible.'))
            # Calculer le hash quand même pour afficher
            current_hash = self._calculate_hash(backup_file)
            self.stdout.write(f'   Hash du fichier: {current_hash[:16]}...')
        
        # Demander une confirmation
        confirmation = input('⚠️  ATTENTION: Cette action va REMPLACER la base de données actuelle. Êtes-vous sûr? (yes/no): ')
        if confirmation.lower() != 'yes':
            self.stdout.write(self.style.WARNING('❌ Restauration annulée'))
            return

        # Variables d'environnement
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_password

        try:
            # Décompresser temporairement
            self.stdout.write('📦 Décompression...')
            temp_file = backup_file.parent / 'temp_restore.sql'
            with gzip.open(backup_file, 'rb') as f_in:
                with open(temp_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Restaurer
            self.stdout.write('📥 Restauration en cours...')
            restore_cmd = [
                'pg_restore',
                '-h', self.db_host,
                '-U', self.db_user,
                '-p', str(self.db_port),
                '-d', self.db_name,
                '--clean',  # Nettoyer les objets existants
                '--if-exists',  # Ne pas errorer si l'objet existe
                str(temp_file)
            ]

            result = subprocess.run(
                restore_cmd,
                env=env,
                capture_output=True,
                check=True
            )

            # Nettoyer le fichier temporaire
            temp_file.unlink()

            self.stdout.write(self.style.SUCCESS(f'✅ Restauration réussie!'))
            self.stdout.write(f'   📁 Depuis: {backup_file.name}')
            self.stdout.write(f'   ⏰ Timestamp: {metadata.get("datetime", "N/A")}')

            # Vérifier la restauration
            self.stdout.write('🔍 Vérification de la restauration...')
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM django_migrations")
                    migration_count = cursor.fetchone()[0]
                    self.stdout.write(f'✅ Base de données opérationnelle ({migration_count} migrations)')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠️  Impossible de vérifier: {e}'))

        except subprocess.CalledProcessError as e:
            raise CommandError(f'❌ Erreur lors de la restauration: {e.stderr.decode()}')
        except Exception as e:
            raise CommandError(f'❌ Erreur: {str(e)}')

    def list_backups(self):
        """Liste tous les backups disponibles"""
        backups = sorted(self.backup_dir.glob('backup_*.sql.gz'))
        
        if not backups:
            self.stdout.write(self.style.WARNING('⚠️  Aucune sauvegarde trouvée'))
            return

        self.stdout.write(self.style.SUCCESS(f'📋 Backups disponibles ({len(backups)} total):'))
        self.stdout.write('-' * 80)

        for i, backup in enumerate(backups[-10:], 1):  # Afficher les 10 derniers
            size_mb = backup.stat().st_size / (1024 * 1024)
            metadata_file = backup.parent / backup.name.replace('.sql.gz', '.json')
            
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
                    timestamp = metadata.get('datetime', 'N/A')
            else:
                timestamp = 'N/A'

            self.stdout.write(f'{i:2d}. {backup.name}')
            self.stdout.write(f'    💾 Taille: {size_mb:.2f} MB')
            self.stdout.write(f'    ⏰ Date: {timestamp}')

    def backup_info(self):
        """Affiche les infos sur les backups"""
        backups = sorted(self.backup_dir.glob('backup_*.sql.gz'))
        
        if not backups:
            self.stdout.write(self.style.WARNING('⚠️  Aucune sauvegarde trouvée'))
            return

        total_size = sum(b.stat().st_size for b in backups)
        total_mb = total_size / (1024 * 1024)

        self.stdout.write(self.style.SUCCESS('📊 Statistiques des Backups:'))
        self.stdout.write('-' * 80)
        self.stdout.write(f'📁 Dossier: {self.backup_dir}')
        self.stdout.write(f'📦 Nombre de backups: {len(backups)}')
        self.stdout.write(f'💾 Taille totale: {total_mb:.2f} MB')
        
        if backups:
            latest = backups[-1]
            metadata_file = latest.parent / latest.name.replace('.sql.gz', '.json')
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
                self.stdout.write(f'⏰ Dernier backup: {metadata.get("datetime")}')
                self.stdout.write(f'🔐 Hash: {metadata.get("hash")}')

    def verify_backup(self):
        """Vérifie l'intégrité du dernier backup"""
        backups = sorted(self.backup_dir.glob('backup_*.sql.gz'))
        if not backups:
            raise CommandError('❌ Aucune sauvegarde trouvée')

        backup_file = backups[-1]
        metadata_file = backup_file.parent / backup_file.name.replace('.sql.gz', '.json')

        if not metadata_file.exists():
            raise CommandError(f'❌ Métadonnées non trouvées pour {backup_file.name}')

        with open(metadata_file) as f:
            metadata = json.load(f)

        stored_hash = metadata.get('hash')
        current_hash = self._calculate_hash(backup_file)

        self.stdout.write(f'🔍 Vérification du backup: {backup_file.name}')
        self.stdout.write(f'   Hash stocké: {stored_hash}')
        self.stdout.write(f'   Hash actuel:  {current_hash}')

        if stored_hash == current_hash:
            self.stdout.write(self.style.SUCCESS('✅ Intégrité vérifiée!'))
        else:
            self.stdout.write(self.style.ERROR('❌ Erreur d\'intégrité! Fichier corrompu!'))

    def _calculate_hash(self, file_path):
        """Calcule le hash SHA256 d'un fichier"""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
