from datetime import datetime, date
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from chlore_api.models import Centre, User
from recipients.models import Recipient, ConfigPeriodicite


# ── Mapping des états Excel ONEE → valeurs techniques du modèle ──
MAPPING_ETATS = {
    "Plein en stock": "plein",
    "En Utilisation": "branche",
    "Vide": "vide",
    "En Attente pour réparation ou épreuve": "entretien",
}

DATE_PAR_DEFAUT = date(2024, 1, 1)  # utilisée si aucune date d'épreuve n'est fournie


def parser_date(date_str):
    """Convertit une date au format JJ-MM-AAAA en objet date Python."""
    if not date_str:
        return DATE_PAR_DEFAUT
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").date()
    except ValueError:
        return DATE_PAR_DEFAUT


def generer_code_qr(numero_serie, code_centre):
    """Génère un code QR basé sur le numéro de série et le code centre."""
    return f"QR-{code_centre}-{numero_serie}"


# ── Données des centres ──
CENTRES_DATA = [
    {"nom": "MACHRAA BELKSIRI", "ville": ""},
    {"nom": "SIDI SLIMANE", "ville": ""},
    {"nom": "TIHLI", "ville": ""},
    {"nom": "DPA/A CASA BLANCA", "ville": "Casablanca"},
]

# ── Données des récipients (issues du tableau ONEE) ──
RECIPIENTS_DATA = [
    # MACHRAA BELKSIRI — code 4P1A11 — ST OULAD NSAR
    {"centre": "MACHRAA BELKSIRI", "code": "4P1A11", "numero_serie": "113",      "capacite": 900, "date": "27-12-2025", "etat": "Plein en stock"},
    {"centre": "MACHRAA BELKSIRI", "code": "4P1A11", "numero_serie": "4501",     "capacite": 900, "date": "27-05-2024", "etat": "Plein en stock"},
    {"centre": "MACHRAA BELKSIRI", "code": "4P1A11", "numero_serie": "5951",     "capacite": 900, "date": "27-12-2024", "etat": "Plein en stock"},
    {"centre": "MACHRAA BELKSIRI", "code": "4P1A11", "numero_serie": "175",      "capacite": 400, "date": "27-12-2024", "etat": "Plein en stock"},
    {"centre": "MACHRAA BELKSIRI", "code": "4P1A11", "numero_serie": "4605",     "capacite": 400, "date": "27-05-2024", "etat": "Plein en stock"},
    {"centre": "MACHRAA BELKSIRI", "code": "4P1A11", "numero_serie": "5814",     "capacite": 400, "date": "25-01-2024", "etat": "Plein en stock"},
    {"centre": "MACHRAA BELKSIRI", "code": "4P1A11", "numero_serie": "27916083", "capacite": 400, "date": "27-12-2024", "etat": "Plein en stock"},
    {"centre": "MACHRAA BELKSIRI", "code": "4P1A11", "numero_serie": "4229",     "capacite": 900, "date": "27-12-2024", "etat": "Plein en stock"},
    {"centre": "MACHRAA BELKSIRI", "code": "4P1A11", "numero_serie": "101",      "capacite": 900, "date": "25-01-2024", "etat": "Vide"},
    {"centre": "MACHRAA BELKSIRI", "code": "4P1A11", "numero_serie": "45",       "capacite": 900, "date": "27-05-2024", "etat": "En Utilisation"},
    {"centre": "MACHRAA BELKSIRI", "code": "4P1A11", "numero_serie": "5920",     "capacite": 900, "date": "27-05-2024", "etat": "En Utilisation"},

    # SIDI SLIMANE — code 4P1E12 — KCEIBIA
    {"centre": "SIDI SLIMANE", "code": "4P1E12", "numero_serie": "4291", "capacite": 400, "date": "27-05-2024", "etat": "Plein en stock"},
    {"centre": "SIDI SLIMANE", "code": "4P1E12", "numero_serie": "5749", "capacite": 400, "date": "27-12-2024", "etat": "Plein en stock"},
    {"centre": "SIDI SLIMANE", "code": "4P1E12", "numero_serie": "173",  "capacite": 400, "date": "25-07-2025", "etat": "Plein en stock"},

    # SIDI SLIMANE — code 4P1E13 — KCEIBIA
    {"centre": "SIDI SLIMANE", "code": "4P1E13", "numero_serie": "84", "capacite": 900, "date": "27-05-2025", "etat": "En Attente pour réparation ou épreuve"},
    {"centre": "SIDI SLIMANE", "code": "4P1E13", "numero_serie": "96", "capacite": 900, "date": "25-12-2023", "etat": "En Attente pour réparation ou épreuve"},
    {"centre": "SIDI SLIMANE", "code": "4P1E13", "numero_serie": "99", "capacite": 900, "date": "25-01-2024", "etat": "Plein en stock"},

    # TIHLI — code 4P1E21 — SR TIHLI
    {"centre": "TIHLI", "code": "4P1E21", "numero_serie": "5928", "capacite": 900, "date": "23-03-2023", "etat": "En Attente pour réparation ou épreuve"},
    {"centre": "TIHLI", "code": "4P1E21", "numero_serie": "4237", "capacite": 900, "date": "25-04-2025", "etat": "Plein en stock"},
    {"centre": "TIHLI", "code": "4P1E21", "numero_serie": "4629", "capacite": 400, "date": "25-07-2025", "etat": "Plein en stock"},
    {"centre": "TIHLI", "code": "4P1E21", "numero_serie": "39",   "capacite": 400, "date": "25-04-2024", "etat": "Plein en stock"},
    {"centre": "TIHLI", "code": "4P1E21", "numero_serie": "126",  "capacite": 900, "date": None,         "etat": "En Attente pour réparation ou épreuve"},
    {"centre": "TIHLI", "code": "4P1E21", "numero_serie": "5945", "capacite": 900, "date": None,         "etat": "En Attente pour réparation ou épreuve"},
    {"centre": "TIHLI", "code": "4P1E21", "numero_serie": "4251", "capacite": 900, "date": "25-04-2025", "etat": "Plein en stock"},
    {"centre": "TIHLI", "code": "4P1E21", "numero_serie": "5925", "capacite": 900, "date": "26-04-2023", "etat": "En Attente pour réparation ou épreuve"},

    # DPA/A CASA BLANCA — pas de numéro de série réel dans le tableau source, générés
    {"centre": "DPA/A CASA BLANCA", "code": "DPA-A", "numero_serie": "DPA-A-001", "capacite": 900, "date": None, "etat": "En Attente pour réparation ou épreuve"},
    {"centre": "DPA/A CASA BLANCA", "code": "DPA-A", "numero_serie": "DPA-A-002", "capacite": 900, "date": None, "etat": "En Attente pour réparation ou épreuve"},
    {"centre": "DPA/A CASA BLANCA", "code": "DPA-A", "numero_serie": "DPA-A-003", "capacite": 400, "date": None, "etat": "En Attente pour réparation ou épreuve"},
    {"centre": "DPA/A CASA BLANCA", "code": "DPA-A", "numero_serie": "DPA-A-004", "capacite": 400, "date": None, "etat": "En Attente pour réparation ou épreuve"},
    {"centre": "DPA/A CASA BLANCA", "code": "DPA-A", "numero_serie": "DPA-A-005", "capacite": 400, "date": None, "etat": "En Attente pour réparation ou épreuve"},
    {"centre": "DPA/A CASA BLANCA", "code": "DPA-A", "numero_serie": "DPA-A-006", "capacite": 400, "date": None, "etat": "En Attente pour réparation ou épreuve"},
    {"centre": "DPA/A CASA BLANCA", "code": "DPA-A", "numero_serie": "DPA-A-007", "capacite": 400, "date": None, "etat": "En Attente pour réparation ou épreuve"},
]

# ── Comptes utilisateurs de test ──
UTILISATEURS_DATA = [
    {"username": "admin",                       "password": "Admin@2026!", "role": "admin",        "centre": None},
    {"username": "chef.machraabelksiri",        "password": "Chef@2026!",  "role": "chef_centre",  "centre": "MACHRAA BELKSIRI"},
    {"username": "chef.sidislimane",            "password": "Chef@2026!",  "role": "chef_centre",  "centre": "SIDI SLIMANE"},
    {"username": "chef.tihli",                  "password": "Chef@2026!",  "role": "chef_centre",  "centre": "TIHLI"},
    {"username": "chef.dpaacasablanca",         "password": "Chef@2026!",  "role": "chef_centre",  "centre": "DPA/A CASA BLANCA"},
    {"username": "agent1",                      "password": "Agent@2026!", "role": "agent",        "centre": "MACHRAA BELKSIRI"},
]

# ── Règles de périodicité ONEE (déjà vues dans serializers.py) ──
CONFIG_PERIODICITE_DATA = [
    {"capacite_kg": 50,  "periodicite_mois": 24, "description": "Bouteille 50 kg"},
    {"capacite_kg": 400, "periodicite_mois": 24, "description": "Citerne 400 kg"},
    {"capacite_kg": 900, "periodicite_mois": 24, "description": "Réservoir 900 kg"},
]


class Command(BaseCommand):
    help = "Peuple la base de données avec les centres, récipients et utilisateurs de test ONEE (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Début du seed..."))

        # ── 1. Centres ──
        centres_crees = {}
        for data in CENTRES_DATA:
            centre, created = Centre.objects.get_or_create(
                nom=data["nom"],
                defaults={"ville": data["ville"]},
            )
            centres_crees[data["nom"]] = centre
            statut = "créé" if created else "déjà existant"
            self.stdout.write(f"  Centre '{centre.nom}' — {statut}")

        # ── 2. Config Périodicité ──
        for data in CONFIG_PERIODICITE_DATA:
            config, created = ConfigPeriodicite.objects.get_or_create(
                capacite_kg=data["capacite_kg"],
                defaults={
                    "periodicite_mois": data["periodicite_mois"],
                    "description": data["description"],
                },
            )
            statut = "créée" if created else "déjà existante"
            self.stdout.write(f"  ConfigPeriodicite {config.capacite_kg}kg — {statut}")

        # ── 3. Utilisateurs ──
        for data in UTILISATEURS_DATA:
            centre_obj = centres_crees.get(data["centre"]) if data["centre"] else None

            if data["role"] == "admin":
                user, created = User.objects.get_or_create(
                    username=data["username"],
                    defaults={
                        "role": "admin",
                        "is_staff": True,
                        "is_superuser": True,
                        "centre": centre_obj,
                    },
                )
            else:
                user, created = User.objects.get_or_create(
                    username=data["username"],
                    defaults={
                        "role": data["role"],
                        "centre": centre_obj,
                    },
                )

            if created:
                user.set_password(data["password"])
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f"  Utilisateur '{user.username}' créé (mdp: {data['password']})"
                ))
            else:
                self.stdout.write(f"  Utilisateur '{user.username}' — déjà existant")

        # ── 4. Récipients ──
        nb_crees = 0
        nb_existants = 0
        for data in RECIPIENTS_DATA:
            centre_obj = centres_crees[data["centre"]]
            code_qr = generer_code_qr(data["numero_serie"], data["code"])
            etat_technique = MAPPING_ETATS.get(data["etat"], "vide")
            date_epreuve = parser_date(data["date"])

            recipient, created = Recipient.objects.get_or_create(
                numero_serie=data["numero_serie"],
                defaults={
                    "code_qr": code_qr,
                    "centre": centre_obj,
                    "etat": etat_technique,
                    "capacite_kg": data["capacite"],
                    "date_derniere_epreuve": date_epreuve,
                },
            )
            if created:
                nb_crees += 1
            else:
                nb_existants += 1

        self.stdout.write(self.style.SUCCESS(
            f"  Récipients : {nb_crees} créés, {nb_existants} déjà existants"
        ))

        self.stdout.write(self.style.SUCCESS("Seed terminé avec succès."))