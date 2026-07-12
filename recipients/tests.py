from django.test import TestCase
from django.contrib.auth import get_user_model
from recipients.models import Recipient, Mouvement
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Centre, Recipient, Mouvement, Anomalie

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


User = get_user_model()

class AnomalieCreateViewTestCase(APITestCase):
    def setUp(self):
        # 1. Création de deux centres distincts
        self.centre_a = Centre.objects.create(nom="Centre A")
        self.centre_b = Centre.objects.create(nom="Centre B")

        # 2. Création du Chef de Centre rattaché au Centre A
        self.chef_a = User.objects.create_user(
            username="chef_a",
            password="password123",
            role="chef_centre",
            centre=self.centre_a
        )

        # 3. Création d'un récipient et d'un mouvement légitimes (Centre A)
        self.recipient_a = Recipient.objects.create(numero_serie="REC-A", centre=self.centre_a, etat="plein")
        self.mouvement_a = Mouvement.objects.create(
            recipient=self.recipient_a,
            centre=self.centre_a,
            agent=self.chef_a,
            ancien_etat="vide",
            nouvel_etat="plein"
        )

        # 4. Création d'un récipient et d'un mouvement d'un AUTRE centre (Centre B)
        self.recipient_b = Recipient.objects.create(numero_serie="REC-B", centre=self.centre_b, etat="plein")
        self.mouvement_b = Mouvement.objects.create(
            recipient=self.recipient_b,
            centre=self.centre_b,
            agent=self.chef_a,  # L'agent importe peu ici, c'est le centre du mouvement qui compte
            ancien_etat="vide",
            nouvel_etat="plein"
        )

    def test_creation_anomalie_centre_legitime(self):
        """Un chef de centre peut créer une anomalie sur un mouvement de son propre centre."""
        self.client.force_authenticate(user=self.chef_a)
        url = reverse('anomalie-create', kwargs={'mouvement_id': self.mouvement_a.id}) # Ajuste le nom de l'url si nécessaire
        data = {'commentaire': 'Le joint de la bouteille fuit légèrement.'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Anomalie.objects.count(), 1)

    def test_creation_anomalie_centre_fraude(self):
        """Un chef de centre est bloqué s'il tente de créer une anomalie sur un mouvement d'un autre centre."""
        self.client.force_authenticate(user=self.chef_a)
        url = reverse('anomalie-create', kwargs={'mouvement_id': self.mouvement_b.id})
        data = {'commentaire': 'Tentative d injection de données.'}
        
        response = self.client.post(url, data, format='json')
        
        # Le test s'attend à recevoir un refus 403 Forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['erreur'], "Ce mouvement n'appartient pas à votre centre")
        self.assertEqual(Anomalie.objects.count(), 0) # Aucune anomalie ne doit être créée

    def test_commentaire_trop_court(self):
        """La vue doit rejeter un commentaire de moins de 5 caractères."""
        self.client.force_authenticate(user=self.chef_a)
        url = reverse('anomalie-create', kwargs={'mouvement_id': self.mouvement_a.id})
        data = {'commentaire': 'Ràs'} # 3 caractères seulement
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Anomalie.objects.count(), 0)