from django.contrib import admin
from .models import Recipient, Mouvement
from .models import Recipient, Mouvement, ConfigPeriodicite
from .models import Recipient, Mouvement, ConfigPeriodicite, Anomalie

@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display  = ['numero_serie', 'code_qr', 'etat', 'centre', 'capacite_kg']
    list_filter   = ['etat', 'centre']
    search_fields = ['numero_serie', 'code_qr']


@admin.register(Mouvement)
class MouvementAdmin(admin.ModelAdmin):
    list_display  = ['recipient', 'agent', 'ancien_etat', 'nouvel_etat', 'date_heure', 'synced']
    list_filter   = ['nouvel_etat', 'synced']
    search_fields = ['recipient__numero_serie']


    
@admin.register(ConfigPeriodicite)
class ConfigPeriodiciteAdmin(admin.ModelAdmin):
    list_display = ['capacite_kg', 'periodicite_mois', 'description']
    
@admin.register(Anomalie)
class AnomalieAdmin(admin.ModelAdmin):
    list_display = ['mouvement', 'chef_centre', 'commentaire', 'date_heure']