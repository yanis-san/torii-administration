from django.core.management.base import BaseCommand
from inventory.models import ItemCategory, InventoryItem, ShoppingList
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Crée des données de test pour l\'app inventaire'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔄 Création des données de test...'))

        # Créer les catégories
        categories = []
        category_data = [
            ('Fournitures scolaires', '#FF5733'),
            ('Nettoyage', '#1ABC9C'),
            ('Fournitures de bureau', '#3498DB'),
            ('Matériel pédagogique', '#F39C12'),
            ('Produits hygiéniques', '#E74C3C'),
        ]

        for name, color in category_data:
            category, created = ItemCategory.objects.get_or_create(
                name=name,
                defaults={'color': color, 'description': f'Catégorie: {name}'}
            )
            categories.append(category)
            status = '✨ Créée' if created else '✓ Existe'
            self.stdout.write(f'  {status}: {name}')

        # Créer les articles
        items_data = [
            ('Cahiers A4', categories[0], 50, 20, 'pcs', True),
            ('Stylos bleus', categories[0], 100, 30, 'pcs', True),
            ('Gommes', categories[0], 45, 15, 'pcs', False),
            ('Produit nettoyant', categories[1], 10, 5, 'liters', True),
            ('Papier toilette', categories[1], 20, 10, 'rouleaux', True),
            ('Classeurs', categories[2], 30, 10, 'pcs', False),
            ('Agrafes', categories[2], 15, 5, 'boîtes', False),
            ('Tableaux blancs', categories[3], 8, 3, 'pcs', True),
            ('Marqueurs', categories[3], 40, 15, 'pcs', True),
            ('Savon liquide', categories[4], 12, 5, 'litres', True),
        ]

        for name, category, quantity, min_qty, unit, mandatory in items_data:
            item, created = InventoryItem.objects.get_or_create(
                name=name,
                category=category,
                defaults={
                    'quantity_current': quantity,
                    'quantity_min': min_qty,
                    'unit': unit,
                    'is_mandatory': mandatory,
                }
            )
            status = '✨ Créé' if created else '✓ Existe'
            self.stdout.write(f'  {status}: {name}')

        # Créer des listes d'achat
        try:
            admin_user = User.objects.filter(is_staff=True, is_teacher=False).first()
            if admin_user:
                list_data = [
                    ('Achat rentrée scolaire', 'Liste pour les fournitures scolaires', datetime.now().date() + timedelta(days=7), 'draft'),
                    ('Fournitures nettoyage', 'Articles pour le nettoyage des salles', datetime.now().date() + timedelta(days=3), 'in_progress'),
                ]

                for title, desc, date, status in list_data:
                    shopping_list, created = ShoppingList.objects.get_or_create(
                        title=title,
                        created_by=admin_user,
                        defaults={
                            'description': desc,
                            'event_date': date,
                            'status': status,
                        }
                    )
                    status_text = '✨ Créée' if created else '✓ Existe'
                    self.stdout.write(f'  {status_text}: {title}')
            else:
                self.stdout.write(self.style.WARNING('  ⚠️ Aucun utilisateur admin trouvé'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Erreur: {str(e)}'))

        self.stdout.write(self.style.SUCCESS('✅ Données de test créées avec succès!'))
