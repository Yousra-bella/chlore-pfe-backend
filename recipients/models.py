from django.db import models
from django.conf import settings
from datetime import date


class Recipient(models.Model):
    ETAT_CHOICES = [
        ('plein',       'Plein'),
        ('branche',     'Branché'),
        ('vide',        'Vide'),
        ('remplissage', 'En remplissage'),
        ('entretien',   'En entretien'),
        ('epreuve',     'En épreuve'),
    ]
    CAPACITE_CHOICES = [
    (50,  '50 kg'),
    (400, '400 kg'),
    (900, '900 kg'),
]
    PERIODICITE = {
    50:  24,
    400: 24,
    900: 24,
}

    numero_serie          = models.CharField(max_length=100, unique=True)
    code_qr               = models.CharField(max_length=200, unique=True)
    centre                = models.ForeignKey('chlore_api.Centre', on_delete=models.PROTECT, related_name='recipients')
    etat                  = models.CharField(max_length=20, choices=ETAT_CHOICES, default='plein')
    capacite_kg           = models.IntegerField(choices=CAPACITE_CHOICES, default=50)
    fournisseur           = models.CharField(max_length=100, blank=True, default='')
    date_derniere_epreuve = models.DateField()
    created_at            = models.DateTimeField(auto_now_add=True)

    @property
    def periodicite_mois(self):
        try:
            config = ConfigPeriodicite.objects.get(capacite_kg=self.capacite_kg)
            return config.periodicite_mois
        except ConfigPeriodicite.DoesNotExist:
            return self.PERIODICITE.get(self.capacite_kg, 12)

    @property
    def date_prochaine_epreuve(self):
        from dateutil.relativedelta import relativedelta
        return self.date_derniere_epreuve + relativedelta(months=self.periodicite_mois)

    @property
    def jours_avant_epreuve(self):
        return (self.date_prochaine_epreuve - date.today()).days

    @property
    def epreuve_expiree(self):
        return self.jours_avant_epreuve < 0

    def __str__(self):
        return f"{self.numero_serie} — {self.etat}"
    class Meta:
        indexes = [
            models.Index(fields=['centre', 'etat']),
        ]


class Mouvement(models.Model):
    recipient   = models.ForeignKey(Recipient, on_delete=models.CASCADE, related_name='mouvements')
    centre      = models.ForeignKey('chlore_api.Centre', on_delete=models.PROTECT)
    agent       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    ancien_etat = models.CharField(max_length=20)
    nouvel_etat = models.CharField(max_length=20)
    observation = models.TextField()
    date_heure  = models.DateTimeField(auto_now_add=True)
    synced      = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date_heure']
        indexes = [
            models.Index(fields=['recipient', 'date_heure']),
        ]

    def __str__(self):
        return f"{self.recipient.numero_serie} : {self.ancien_etat} → {self.nouvel_etat}"


class ConfigPeriodicite(models.Model):
    capacite_kg      = models.IntegerField(unique=True)
    periodicite_mois = models.IntegerField()
    description      = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.capacite_kg} kg → {self.periodicite_mois} mois"
class Anomalie(models.Model):
    mouvement   = models.ForeignKey(Mouvement, on_delete=models.CASCADE, related_name='anomalies')
    chef_centre = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    commentaire = models.TextField()
    date_heure  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_heure']

    def __str__(self):
        return f"Anomalie sur {self.mouvement} par {self.chef_centre.username}"