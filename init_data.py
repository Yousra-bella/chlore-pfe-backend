import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from chlore_api.models import Centre
from recipients.models import Recipient, Mouvement
from datetime import date

# ── 1. Vider les anciennes données ──────────────────────────────────────────
print("Suppression des anciennes données...")
Mouvement.objects.all().delete()
Recipient.objects.all().delete()
Centre.objects.filter(nom='Station Fes Centre').delete()
print("OK")

# ── 2. Créer les centres ─────────────────────────────────────────────────────
print("Création des centres...")
c_machraa  = Centre.objects.get_or_create(nom='MACHRAA BELKSIRI', defaults={'ville': 'Machraa Belksiri'})[0]
c_sidi     = Centre.objects.get_or_create(nom='SIDI SLIMANE',     defaults={'ville': 'Sidi Slimane'})[0]
c_tihli    = Centre.objects.get_or_create(nom='TIHLI',            defaults={'ville': 'Tihli'})[0]
c_casa     = Centre.objects.get_or_create(nom='DPA/A CASA BLANCA',defaults={'ville': 'Casablanca'})[0]
print("OK — 4 centres créés")

# ── 3. Fonction helper ───────────────────────────────────────────────────────
def parse_date(s):
    if not s or s.strip() == '':
        return date(2020, 1, 1)  # date par défaut si manquante
    try:
        j, m, a = s.strip().split('-')
        return date(int(a), int(m), int(j))
    except:
        return date(2020, 1, 1)

def creer(centre, code_centre, site, numero, capacite, date_epreuve, etat, observations=''):
    # Générer un code QR unique
    code_qr = f"{code_centre}-{numero}" if numero else f"{code_centre}-NONUM-{Recipient.objects.count()+1}"
    numero_serie = str(numero) if numero else f"SANS-{Recipient.objects.count()+1}"

    Recipient.objects.update_or_create(
        code_qr=code_qr,
        defaults={
            'numero_serie':          numero_serie,
            'centre':                centre,
            'etat':                  etat,
            'capacite_kg':           capacite,
            'date_derniere_epreuve': parse_date(date_epreuve),
        }
    )

# ── 4. MACHRAA BELKSIRI ──────────────────────────────────────────────────────
print("Insertion MACHRAA BELKSIRI...")
donnees_machraa = [
    ('4P1A11', 'ST OULAD NSAR', 113,      900, '27-12-2025', 'plein'),
    ('4P1A11', 'ST OULAD NSAR', 4501,     900, '27-05-2024', 'plein'),
    ('4P1A11', 'ST OULAD NSAR', 5951,     900, '27-12-2024', 'plein'),
    ('4P1A11', 'ST OULAD NSAR', 175,      400, '27-12-2024', 'plein'),
    ('4P1A11', 'ST OULAD NSAR', 4605,     400, '27-05-2024', 'plein'),
    ('4P1A11', 'ST OULAD NSAR', 5814,     400, '25-01-2024', 'plein'),
    ('4P1A11', 'ST OULAD NSAR', 27916083, 400, '27-12-2024', 'plein'),
    ('4P1A11', 'ST OULAD NSAR', 4229,     900, '27-12-2024', 'plein'),
    ('4P1A11', 'ST OULAD NSAR', 101,      900, '25-01-2024', 'vide'),
    ('4P1A11', 'ST OULAD NSAR', 45,       900, '27-05-2024', 'branche'),
    ('4P1A11', 'ST OULAD NSAR', 5920,     900, '27-05-2024', 'branche'),
]
for code, site, num, cap, dep, etat in donnees_machraa:
    creer(c_machraa, code, site, num, cap, dep, etat, 'Affectation SP4/2')

# ── 5. SIDI SLIMANE ──────────────────────────────────────────────────────────
print("Insertion SIDI SLIMANE...")
donnees_sidi = [
    ('4P1E12', 'KCEIBIA', 4291, 400, '27-05-2024', 'plein'),
    ('4P1E12', 'KCEIBIA', 5749, 400, '27-12-2024', 'plein'),
    ('4P1E12', 'KCEIBIA', 173,  400, '25-07-2025', 'plein'),
    ('4P1E13', 'KCEIBIA', 84,   900, '27-05-2025', 'epreuve'),
    ('4P1E13', 'KCEIBIA', 96,   900, '25-12-2023', 'epreuve'),
    ('4P1E13', 'KCEIBIA', 99,   900, '25-01-2024', 'plein'),
]
for code, site, num, cap, dep, etat in donnees_sidi:
    creer(c_sidi, code, site, num, cap, dep, etat, 'Affectation SP4/2')

# ── 6. TIHLI ─────────────────────────────────────────────────────────────────
print("Insertion TIHLI...")
donnees_tihli = [
    ('4P1E21', 'SR TIHLI', 5928, 900, '23-03-2023', 'epreuve'),
    ('4P1E21', 'SR TIHLI', 4237, 900, '25-04-2025', 'plein'),
    ('4P1E21', 'SR TIHLI', 4629, 400, '25-07-2025', 'plein'),
    ('4P1E21', 'SR TIHLI', 39,   400, '25-04-2024', 'plein'),
    ('4P1E21', 'SR TIHLI', 126,  900, '',           'epreuve'),
    ('4P1E21', 'SR TIHLI', 5945, 900, '',           'epreuve'),
    ('4P1E21', 'SR TIHLI', 4251, 900, '25-04-2025', 'plein'),
    ('4P1E21', 'SR TIHLI', 5925, 900, '26-04-2023', 'epreuve'),
]
for code, site, num, cap, dep, etat in donnees_tihli:
    aff = 'Affectation SP4/1' if etat == 'epreuve' else 'Affectation SP4/2'
    creer(c_tihli, code, site, num, cap, dep, etat, aff)

# ── 7. DPA/A CASA BLANCA ─────────────────────────────────────────────────────
print("Insertion DPA/A CASA BLANCA...")
donnees_casa = [
    (900, ''), (900, ''),
    (400, ''), (400, ''), (400, ''), (400, ''), (400, ''),
]
for i, (cap, dep) in enumerate(donnees_casa, 1):
    Recipient.objects.update_or_create(
        code_qr=f"DPA-CASA-{cap}-{i:02d}",
        defaults={
            'numero_serie':          f"CASA-{cap}-{i:02d}",
            'centre':                c_casa,
            'etat':                  'epreuve',
            'capacite_kg':           cap,
            'date_derniere_epreuve': date(2020, 1, 1),
        }
    )

# ── 8. Résumé ────────────────────────────────────────────────────────────────
total = Recipient.objects.count()
print(f"\nTerminé — {total} récipients insérés")
for centre in Centre.objects.all():
    nb = Recipient.objects.filter(centre=centre).count()
    print(f"  {centre.nom} : {nb} récipients")