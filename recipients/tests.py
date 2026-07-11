from django.test import TestCase
from django.contrib.auth import get_user_model
from recipients.models import Recipient, Mouvement
from django.db import transaction
from django.utils import timezone

# 💡 On récupère le modèle Centre dynamiquement depuis le modèle Recipient
Centre = Recipient._meta.get_field('centre').remote_field.model

User = get_user_model()

class ChangerEtatTransactionTest(TestCase):
    def setUp(self):
        # 1. Création d'un centre logistique obligatoire
        self.centre = Centre.objects.create(nom="Centre Test")

        # 2. Création de l'utilisateur associé au centre
        self.user = User.objects.create_user(
            username='agent1', 
            password='password', 
            role='agent',
            centre=self.centre
        )
        
        # 3. Création du récipient avec tous ses champs obligatoires
        self.recipient = Recipient.objects.create(
            numero_serie='12345', 
            etat='plein',
            date_derniere_epreuve=timezone.now().date(),
            centre=self.centre
        )

    def test_transaction_atomic_force_le_tout_ou_rien(self):
        """Vérifie que si la sauvegarde du récipient plante, le mouvement n'est pas créé"""
        
        def simuler_plantage_save(*args, **kwargs):
            raise Exception("Plantage simulé de la base de données")
        
        self.recipient.save = simuler_plantage_save

        with self.assertRaises(Exception):
            with transaction.atomic():
                Mouvement.objects.create(
                    recipient=self.recipient,
                    centre=self.recipient.centre,
                    agent=self.user,
                    ancien_etat='plein',
                    nouvel_etat='branche',
                    observation='Test de sécurité'
                )
                self.recipient.etat = 'branche'
                self.recipient.save()

        mouvements_crees = Mouvement.objects.filter(recipient=self.recipient).count()
        self.assertEqual(mouvements_crees, 0, "Sécurité validée : Aucun mouvement fantôme n'a été enregistré !")