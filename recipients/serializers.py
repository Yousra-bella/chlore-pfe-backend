from rest_framework import serializers
from .models import Recipient, Mouvement, ConfigPeriodicite, Anomalie

# ═══════════════════════════════════════════════════════════════
#  RÈGLES MÉTIER ONEE — périodicités par capacité
#  Pour ajouter une capacité : une seule ligne à ajouter ici
# ═══════════════════════════════════════════════════════════════
REGLES_PERIODICITE = {
    50:  {'min': 24, 'max': 24, 'label': 'Bouteille 50 kg'},
    400: {'min': 24, 'max': 24, 'label': 'Citerne 400 kg'},
    900: {'min': 24, 'max': 24, 'label': 'Réservoir 900 kg'},
    # ── Ajouter d'autres capacités ici ──────────────────────
    # 500:  {'min': 12, 'max': 24, 'label': 'Citerne 500 kg'},
    # 2000: {'min': 24, 'max': 36, 'label': 'Tank 2000 kg'},
    # ────────────────────────────────────────────────────────
}
# Toute capacité non listée → libre entre 1 et 60 mois
REGLE_DEFAUT = {'min': 1, 'max': 60, 'label': 'Équipement personnalisé'}


# ═══════════════════════════════════════════════════════════════
#  RECIPIENT
# ═══════════════════════════════════════════════════════════════
class RecipientSerializer(serializers.ModelSerializer):
    date_prochaine_epreuve = serializers.DateField(read_only=True)
    epreuve_expiree        = serializers.BooleanField(read_only=True)
    jours_avant_epreuve    = serializers.IntegerField(read_only=True)
    etat_display           = serializers.CharField(source='get_etat_display', read_only=True)
    centre_nom             = serializers.CharField(source='centre.nom', read_only=True)

    class Meta:
        model  = Recipient
        fields = '__all__'


# ═══════════════════════════════════════════════════════════════
#  ANOMALIE — une seule déclaration
# ═══════════════════════════════════════════════════════════════
class AnomalieSerializer(serializers.ModelSerializer):
    chef_centre_nom = serializers.CharField(source='chef_centre.username', read_only=True)

    class Meta:
        model            = Anomalie
        fields           = ['id', 'mouvement', 'chef_centre_nom', 'commentaire', 'date_heure']
        read_only_fields = ['date_heure', 'chef_centre']


# ═══════════════════════════════════════════════════════════════
#  MOUVEMENT
# ═══════════════════════════════════════════════════════════════
class MouvementSerializer(serializers.ModelSerializer):
    recipient_serie     = serializers.CharField(source='recipient.numero_serie', read_only=True)
    agent_nom           = serializers.CharField(source='agent.username',         read_only=True)
    centre_nom          = serializers.CharField(source='centre.nom',             read_only=True)
    ancien_etat_display = serializers.SerializerMethodField()
    nouvel_etat_display = serializers.SerializerMethodField()
    anomalies           = AnomalieSerializer(many=True, read_only=True)

    class Meta:
        model            = Mouvement
        fields           = '__all__'
        read_only_fields = ['date_heure', 'agent', 'centre']

    def get_ancien_etat_display(self, obj):
        return dict(Recipient.ETAT_CHOICES).get(obj.ancien_etat, obj.ancien_etat)

    def get_nouvel_etat_display(self, obj):
        return dict(Recipient.ETAT_CHOICES).get(obj.nouvel_etat, obj.nouvel_etat)


# ═══════════════════════════════════════════════════════════════
#  CHANGEMENT D'ÉTAT
# ═══════════════════════════════════════════════════════════════
class ChangementEtatSerializer(serializers.Serializer):
    """Utilisé par ChangerEtatView pour valider la requête mobile."""
    nouvel_etat = serializers.ChoiceField(choices=Recipient.ETAT_CHOICES)
    observation = serializers.CharField(min_length=5)


# ═══════════════════════════════════════════════════════════════
#  CONFIG PERIODICITE — avec validation métier ONEE
# ═══════════════════════════════════════════════════════════════
class ConfigPeriodiciteSerializer(serializers.ModelSerializer):

    class Meta:
        model  = ConfigPeriodicite
        fields = ['id', 'capacite_kg', 'periodicite_mois', 'description']

    def validate_capacite_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "❌ La capacité doit être un entier positif."
            )
        return value

    def validate_periodicite_mois(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "❌ La périodicité doit être un entier positif."
            )
        return value

    def validate(self, data):
        capacite    = data.get('capacite_kg',
                        self.instance.capacite_kg if self.instance else None)
        periodicite = data.get('periodicite_mois',
                        self.instance.periodicite_mois if self.instance else None)

        if capacite is None or periodicite is None:
            return data

        regle = REGLES_PERIODICITE.get(capacite, REGLE_DEFAUT)
        min_v = regle['min']
        max_v = regle['max']
        label = regle['label']

        # ── Périodicité fixe (min == max) ─────────────────────
        if min_v == max_v and periodicite != min_v:
            raise serializers.ValidationError({
                'periodicite_mois': (
                    f"❌ La périodicité pour {label} ({capacite} kg) "
                    f"doit être exactement {min_v} mois. "
                    f"Valeur saisie : {periodicite} mois."
                )
            })

        # ── Plage autorisée ───────────────────────────────────
        if periodicite < min_v:
            raise serializers.ValidationError({
                'periodicite_mois': (
                    f"❌ Périodicité trop courte pour {label} ({capacite} kg). "
                    f"Minimum autorisé : {min_v} mois. "
                    f"Valeur saisie : {periodicite} mois."
                )
            })

        if periodicite > max_v:
            raise serializers.ValidationError({
                'periodicite_mois': (
                    f"❌ Périodicité trop longue pour {label} ({capacite} kg). "
                    f"Maximum autorisé : {max_v} mois. "
                    f"Valeur saisie : {periodicite} mois."
                )
            })

        return data