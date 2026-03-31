from django.db.models.signals import post_save
from django.dispatch import receiver
from dateutil.relativedelta import relativedelta # Il faudra pip install python-dateutil
from students.models import Enrollment
from finance.models import Installment

@receiver(post_save, sender=Enrollment)
def generate_installments(sender, instance, created, **kwargs):
    """
    Génère l'échéancier automatiquement dès qu'une inscription est créée.
    """
    if kwargs.get('raw', False):
        return

    if created:
        # 1. Cas Paiement TOTAL ou PACK
        if instance.payment_plan in ['FULL', 'PACK']:
            Installment.objects.create(
                enrollment=instance,
                due_date=instance.date, # Dû immédiatement
                amount=instance.tariff.amount
            )
        
        # 2. Cas Paiement MENSUEL
        elif instance.payment_plan == 'MONTHLY':
            start_date = instance.cohort.start_date
            end_date = instance.cohort.end_date
            total_amount = instance.tariff.amount
            
            # Calcul du nombre de mois (approximatif pour diviser le prix)
            # On utilise relativedelta pour la précision des mois
            delta = relativedelta(end_date, start_date)
            months_count = delta.years * 12 + delta.months
            # On ajoute 1 si le cours déborde sur un autre mois
            if delta.days > 0: 
                months_count += 1
            
            if months_count < 1: months_count = 1

            monthly_amount = total_amount / months_count
            
            # Création des échéances
            current_date = start_date
            for i in range(months_count):
                Installment.objects.create(
                    enrollment=instance,
                    due_date=current_date, # Le 1er jour du cycle
                    amount=monthly_amount
                )
                # On avance d'un mois
                current_date = current_date + relativedelta(months=1)