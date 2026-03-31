"""
Commande Django pour sauvegarder COMPLETEMENT la base de donnees ET les fichiers medias.

Usage:
    python manage.py backup_data                           # Sauvegarde vers OneDrive (par defaut)
    python manage.py backup_data --dest "C:\\Backups"       # Sauvegarde vers chemin personnalise
    python manage.py backup_data --verify                  # Verifier le dernier backup
    python manage.py backup_data --list                    # Lister les backups
"""

import os
import subprocess
import json
import hashlib
import gzip
import shutil
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = "Sauvegarde COMPLÈTEMENT la base de données ET les fichiers (médias, documents, etc)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dest',
            type=str,
            help='Destination personnalisée (par défaut: OneDrive)',
        )
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Vérifier l\'intégrité du dernier backup',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='Lister tous les backups',
        )

    def handle(self, *args, **options):
        # Déterminer le dossier de sauvegarde
        if options['dest']:
            self.backup_dir = Path(options['dest'])
        else:
            # Par défaut: OneDrive
            self.backup_dir = Path(r"C:\Users\Social Media Manager\OneDrive\Torii-management\backups")
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Infos base de données
        self.db_name = settings.DATABASES['default']['NAME']
        self.db_user = settings.DATABASES['default']['USER']
        self.db_host = settings.DATABASES['default']['HOST']
        self.db_port = settings.DATABASES['default']['PORT']
        self.db_password = settings.DATABASES['default']['PASSWORD']
        
        # Dossier de base du projet
        self.base_dir = settings.BASE_DIR
        self.media_root = settings.MEDIA_ROOT

        if options['verify']:
            self.verify_backup()
        elif options['list']:
            self.list_backups()
        else:
            self.create_full_backup()

    def create_full_backup(self):
        """Cree une sauvegarde COMPLETE: DB + fichiers"""
        self.stdout.write(self.style.SUCCESS('[DEBUT] Sauvegarde COMPLETE (DB + Medias)...'))

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_tar = self.backup_dir / f"backup_complet_{self.db_name}_{timestamp}.tar.gz"
        
        # Fichiers temporaires
        temp_dir = Path(tempfile.gettempdir()) / f"backup_{timestamp}"
        temp_dir.mkdir(exist_ok=True)
        
        db_file = temp_dir / f"database_{self.db_name}.sql"

        try:
            # ============ ÉTAPE 1: Dump de la base de données ============
            self.stdout.write('📦 [1/4] Dump de la base de données...')
            self._dump_database(db_file)
            
            # ============ ÉTAPE 2: Préparation des fichiers ============
            self.stdout.write('📁 [2/4] Préparation des fichiers médias...')
            self._prepare_media_files(temp_dir)
            
            # ============ ÉTAPE 3: Création de l'archive TAR.GZ ============
            self.stdout.write('📦 [3/4] Création de l\'archive compressée...')
            self._create_tar_archive(temp_dir, backup_tar)
            
            # ============ ÉTAPE 4: Calcul du hash et métadonnées ============
            self.stdout.write('🔐 [4/4] Calcul de l\'intégrité et métadonnées...')
            file_hash = self._calculate_hash(backup_tar)
            size_mb = backup_tar.stat().st_size / (1024 * 1024)
            
            # Créer les métadonnées
            metadata = {
                'backup_file': backup_tar.name,
                'timestamp': timestamp,
                'datetime': datetime.now().isoformat(),
                'database': self.db_name,
                'type': 'COMPLETE',  # DB + MEDIA
                'size_bytes': backup_tar.stat().st_size,
                'size_mb': round(size_mb, 2),
                'hash': file_hash,
                'includes': ['database', 'media', 'documents'],
                'status': 'completed'
            }
            
            metadata_file = self.backup_dir / f"backup_complet_{self.db_name}_{timestamp}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Afficher les infos
            self.stdout.write(self.style.SUCCESS(f'\n✅ SAUVEGARDE COMPLÈTE RÉUSSIE!'))
            self.stdout.write(f'\n   📋 Type: Base de données + Fichiers médias')
            self.stdout.write(f'   📁 Fichier: {backup_tar.name}')
            self.stdout.write(f'   💾 Taille: {size_mb:.2f} MB')
            self.stdout.write(f'   🔐 Hash: {file_hash[:16]}...')
            self.stdout.write(f'   📍 Localisation: {backup_tar}')
            self.stdout.write(f'   ⏰ Date: {metadata["datetime"]}')
            
            # Nettoyer les fichiers temporaires
            shutil.rmtree(temp_dir)
            
        except Exception as e:
            # Nettoyer en cas d'erreur
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            if backup_tar.exists():
                backup_tar.unlink()
            raise CommandError(f'❌ Erreur lors de la sauvegarde: {str(e)}')

    def _dump_database(self, db_file):
        """Dump la base de données PostgreSQL"""
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_password

        dump_cmd = [
            'pg_dump',
            '-h', self.db_host,
            '-U', self.db_user,
            '-p', str(self.db_port),
            '-Fc',  # Format custom (binaire, plus efficace)
            self.db_name
        ]

        with open(db_file, 'wb') as f:
            result = subprocess.run(
                dump_cmd,
                env=env,
                stdout=f,
                stderr=subprocess.PIPE,
                check=True
            )
        
        size_mb = db_file.stat().st_size / (1024 * 1024)
        self.stdout.write(f'   ✅ DB dumpée: {size_mb:.2f} MB')

    def _prepare_media_files(self, temp_dir):
        """Copie les fichiers médias dans le dossier temporaire"""
        if not self.media_root.exists():
            self.stdout.write(f'   ℹ️  Dossier médias vide ou inexistant')
            return
        
        media_temp = temp_dir / 'media'
        media_count = 0
        total_size = 0
        
        try:
            # Copier récursivement les fichiers médias
            for item in self.media_root.rglob('*'):
                if item.is_file():
                    relative_path = item.relative_to(self.media_root)
                    dest_file = media_temp / relative_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_file)
                    media_count += 1
                    total_size += item.stat().st_size
            
            total_size_mb = total_size / (1024 * 1024)
            self.stdout.write(f'   ✅ {media_count} fichiers médias copiés ({total_size_mb:.2f} MB)')
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   ⚠️  Erreur lors de la copie des médias: {e}'))

    def _create_tar_archive(self, temp_dir, output_file):
        """Crée une archive TAR.GZ compressée"""
        with tarfile.open(output_file, 'w:gz') as tar:
            tar.add(temp_dir, arcname='.')
        
        self.stdout.write(f'   ✅ Archive créée: {output_file.name}')

    def _calculate_hash(self, file_path):
        """Calcule le hash SHA256 d'un fichier"""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def verify_backup(self):
        """Vérifie l'intégrité du dernier backup"""
        backups = sorted(self.backup_dir.glob('backup_complet_*.tar.gz'))
        if not backups:
            raise CommandError('❌ Aucune sauvegarde trouvée')

        backup_file = backups[-1]
        metadata_file = backup_file.parent / backup_file.name.replace('.tar.gz', '.json')

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

    def list_backups(self):
        """Liste tous les backups disponibles"""
        backups = sorted(self.backup_dir.glob('backup_complet_*.tar.gz'))
        
        if not backups:
            self.stdout.write(self.style.WARNING('⚠️  Aucune sauvegarde trouvée'))
            return

        self.stdout.write(self.style.SUCCESS(f'📋 Sauvegardes COMPLÈTES disponibles ({len(backups)} total):'))
        self.stdout.write('-' * 100)

        for i, backup in enumerate(backups[-10:], 1):  # Afficher les 10 derniers
            size_mb = backup.stat().st_size / (1024 * 1024)
            metadata_file = backup.parent / backup.name.replace('.tar.gz', '.json')
            
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
                    timestamp = metadata.get('datetime', 'N/A')
                    includes = ', '.join(metadata.get('includes', []))
            else:
                timestamp = 'N/A'
                includes = 'N/A'

            self.stdout.write(f'{i:2d}. {backup.name}')
            self.stdout.write(f'    💾 Taille: {size_mb:.2f} MB')
            self.stdout.write(f'    ⏰ Date: {timestamp}')
            self.stdout.write(f'    📦 Contient: {includes}')
            self.stdout.write('')
