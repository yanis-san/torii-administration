"""
Interface Admin pour gérer les sauvegardes de la base de données
"""
from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.utils.html import format_html
from django.http import JsonResponse
import os
import json
import gzip
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from django.conf import settings


class BackupAdminSite(admin.AdminSite):
    """Site admin personnalisé avec page de backup"""
    site_header = "Administration - Torii Management"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('backup/', self.admin_site.backup_view, name='backup'),
            path('backup/create/', self.backup_create, name='backup_create'),
            path('backup/list/', self.backup_list, name='backup_list'),
            path('backup/restore/', self.backup_restore, name='backup_restore'),
        ]
        return custom_urls + urls

    def backup_view(self, request):
        """Vue principale du backup"""
        backup_dir = Path(r"C:\Users\Social Media Manager\OneDrive\Torii-management\backups")
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Obtenir les backups
        backups = sorted(backup_dir.glob('backup_*.sql.gz'))
        backup_list = []

        for backup in backups[-10:]:  # Dernier 10
            metadata_file = backup.parent / backup.name.replace('.sql.gz', '.json')
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
                backup_list.append({
                    'name': backup.name,
                    'size_mb': backup.stat().st_size / (1024 * 1024),
                    'date': metadata.get('datetime'),
                    'hash': metadata.get('hash'),
                })

        context = {
                'title': '💾 Gestion des Sauvegardes',
            'backup_list': backup_list,
            'total_backups': len(backups),
            'backup_dir': str(backup_dir),
        }

        return render(request, 'admin/backup.html', context)

    def backup_create(self, request):
        """Crée une sauvegarde"""
        if request.method == 'POST':
            # Appeler la commande de backup
            db_name = settings.DATABASES['default']['NAME']
            db_user = settings.DATABASES['default']['USER']
            db_host = settings.DATABASES['default']['HOST']
            db_port = settings.DATABASES['default']['PORT']
            db_password = settings.DATABASES['default']['PASSWORD']

            backup_dir = Path(r"C:\Users\Social Media Manager\OneDrive\Torii-management\backups")
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f"backup_{db_name}_{timestamp}.sql"
            backup_gz = backup_dir / f"backup_{db_name}_{timestamp}.sql.gz"

            env = os.environ.copy()
            env['PGPASSWORD'] = db_password

            try:
                # Dump
                dump_cmd = [
                    'pg_dump',
                    '-h', db_host,
                    '-U', db_user,
                    '-p', str(db_port),
                    '-Fc',
                    db_name
                ]

                with open(backup_file, 'wb') as f:
                    subprocess.run(dump_cmd, env=env, stdout=f, stderr=subprocess.PIPE, check=True)

                # Compress
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(backup_gz, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                backup_file.unlink()

                # Metadata
                import hashlib
                sha256_hash = hashlib.sha256()
                with open(backup_gz, 'rb') as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)

                metadata = {
                    'backup_file': backup_gz.name,
                    'timestamp': timestamp,
                    'datetime': datetime.now().isoformat(),
                    'database': db_name,
                    'size_bytes': backup_gz.stat().st_size,
                    'hash': sha256_hash.hexdigest(),
                    'status': 'completed'
                }

                metadata_file = backup_dir / f"backup_{db_name}_{timestamp}.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)

                return JsonResponse({
                    'success': True,
                    'message': f'✅ Sauvegarde réussie: {backup_gz.name}',
                    'size_mb': backup_gz.stat().st_size / (1024 * 1024),
                })

            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'❌ Erreur: {str(e)}',
                })

        return JsonResponse({'error': 'Méthode non autorisée'})

    def backup_list(self, request):
        """Liste les backups"""
        backup_dir = Path(r"C:\Users\Social Media Manager\OneDrive\Torii-management\backups")
        backups = sorted(backup_dir.glob('backup_*.sql.gz'))

        backup_list = []
        for backup in backups:
            metadata_file = backup.parent / backup.name.replace('.sql.gz', '.json')
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
                backup_list.append({
                    'name': backup.name,
                    'size_mb': backup.stat().st_size / (1024 * 1024),
                    'date': metadata.get('datetime'),
                    'hash': metadata.get('hash')[:16] + '...',
                })

        return JsonResponse({'backups': backup_list})

    def backup_restore(self, request):
        """Restaure une sauvegarde"""
        if request.method == 'POST':
            backup_name = request.POST.get('backup_name')
            backup_dir = Path(r"C:\Users\Social Media Manager\OneDrive\Torii-management\backups")
            backup_file = backup_dir / backup_name

            if not backup_file.exists():
                return JsonResponse({
                    'success': False,
                    'message': '❌ Fichier non trouvé',
                })

            db_name = settings.DATABASES['default']['NAME']
            db_user = settings.DATABASES['default']['USER']
            db_host = settings.DATABASES['default']['HOST']
            db_port = settings.DATABASES['default']['PORT']
            db_password = settings.DATABASES['default']['PASSWORD']

            env = os.environ.copy()
            env['PGPASSWORD'] = db_password

            try:
                # Vérifier l'intégrité
                metadata_file = backup_file.parent / backup_file.name.replace('.sql.gz', '.json')
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                    
                    import hashlib
                    sha256_hash = hashlib.sha256()
                    with open(backup_file, 'rb') as f:
                        for byte_block in iter(lambda: f.read(4096), b""):
                            sha256_hash.update(byte_block)
                    
                    if metadata['hash'] != sha256_hash.hexdigest():
                        return JsonResponse({
                            'success': False,
                            'message': '❌ Erreur d\'intégrité! Le fichier a été corrompu.',
                        })

                # Décompresser
                temp_file = backup_file.parent / 'temp_restore.sql'
                with gzip.open(backup_file, 'rb') as f_in:
                    with open(temp_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # Restaurer
                restore_cmd = [
                    'pg_restore',
                    '-h', db_host,
                    '-U', db_user,
                    '-p', str(db_port),
                    '-d', db_name,
                    '--clean',
                    '--if-exists',
                    str(temp_file)
                ]

                result = subprocess.run(
                    restore_cmd,
                    env=env,
                    capture_output=True,
                    check=True
                )

                temp_file.unlink()

                return JsonResponse({
                    'success': True,
                    'message': f'✅ Restauration réussie depuis {backup_name}',
                })

            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'❌ Erreur de restauration: {str(e)}',
                })

        return JsonResponse({'error': 'Méthode non autorisée'})
