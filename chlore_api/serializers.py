from rest_framework import serializers
from .models import Centre, User


class CentreSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Centre
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    centre_nom = serializers.CharField(source='centre.nom', read_only=True, default='')
    password   = serializers.CharField(write_only=True, required=False)

    class Meta:
        model  = User
        fields = [
            'id', 'username', 'email', 'role',
            'centre', 'centre_nom', 'telephone',
            'first_name', 'last_name', 'password',
            'is_active',
        ]

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance