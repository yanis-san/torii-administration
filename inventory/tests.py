from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import ItemCategory, InventoryItem, ShoppingList, ShoppingListItem
from datetime import datetime, timedelta

User = get_user_model()


class InventoryModelTests(TestCase):
    def setUp(self):
        self.category = ItemCategory.objects.create(
            name="Fournitures",
            description="Fournitures scolaires",
            color="#FF5733"
        )
        self.item = InventoryItem.objects.create(
            name="Cahiers A4",
            category=self.category,
            quantity_current=50,
            quantity_min=20,
            unit="pcs"
        )

    def test_category_creation(self):
        """Tester la création d'une catégorie"""
        self.assertEqual(self.category.name, "Fournitures")
        self.assertIn("Fournitures", str(self.category))

    def test_inventory_item_creation(self):
        """Tester la création d'un article"""
        self.assertEqual(self.item.name, "Cahiers A4")
        self.assertEqual(self.item.quantity_current, 50)
        self.assertEqual(self.item.status, "in_stock")

    def test_inventory_item_status_update(self):
        """Tester la mise à jour du statut"""
        # Statut normal
        self.item.quantity_current = 50
        self.item.save()
        self.assertEqual(self.item.status, "in_stock")

        # Stock faible
        self.item.quantity_current = 20
        self.item.save()
        self.assertEqual(self.item.status, "low_stock")

        # Rupture
        self.item.quantity_current = 0
        self.item.save()
        self.assertEqual(self.item.status, "out_of_stock")


class ShoppingListModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_teacher=False
        )
        self.category = ItemCategory.objects.create(
            name="Fournitures",
            color="#FF5733"
        )
        self.item = InventoryItem.objects.create(
            name="Cahiers A4",
            category=self.category,
            quantity_current=50,
            quantity_min=20,
            unit="pcs"
        )
        self.shopping_list = ShoppingList.objects.create(
            title="Liste pour école",
            created_by=self.user,
            event_date=datetime.now().date() + timedelta(days=7),
            status='draft'
        )

    def test_shopping_list_creation(self):
        """Tester la création d'une liste"""
        self.assertEqual(self.shopping_list.title, "Liste pour école")
        self.assertEqual(self.shopping_list.status, "draft")
        self.assertEqual(self.shopping_list.total_cost, 0)

    def test_shopping_list_item_creation(self):
        """Tester l'ajout d'articles à la liste"""
        list_item = ShoppingListItem.objects.create(
            shopping_list=self.shopping_list,
            item=self.item,
            quantity_needed=10,
            unit="pcs",
            unit_price=2.50,
            priority=1
        )
        self.assertEqual(list_item.get_item_name(), "Cahiers A4")
        self.assertEqual(list_item.get_total_price(), 25.00)

    def test_shopping_list_cost_calculation(self):
        """Tester le calcul du coût total"""
        ShoppingListItem.objects.create(
            shopping_list=self.shopping_list,
            item=self.item,
            quantity_needed=10,
            unit="pcs",
            unit_price=2.50,
            priority=1
        )
        self.shopping_list.update_total_cost()
        self.assertEqual(self.shopping_list.total_cost, 25.00)


class InventoryViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123',
            is_teacher=False,
            is_staff=True
        )
        self.teacher_user = User.objects.create_user(
            username='teacher',
            email='teacher@example.com',
            password='teacher123',
            is_teacher=True
        )

    def test_inventory_dashboard_requires_login(self):
        """Vérifier que le dashboard nécessite une connexion"""
        response = self.client.get(reverse('inventory:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirection vers login

    def test_inventory_dashboard_admin_access(self):
        """Vérifier que l'admin peut accéder au dashboard"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('inventory:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_inventory_dashboard_teacher_no_access(self):
        """Vérifier que les profs ne peuvent pas accéder"""
        self.client.login(username='teacher', password='teacher123')
        response = self.client.get(reverse('inventory:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirection

    def test_inventory_list_view(self):
        """Tester la liste des articles"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('inventory:inventory_list'))
        self.assertEqual(response.status_code, 200)

    def test_shopping_lists_view(self):
        """Tester la liste des listes d'achat"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('inventory:shopping_lists'))
        self.assertEqual(response.status_code, 200)
