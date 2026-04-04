from django.contrib.auth.models import User
from rest_framework import serializers

class RegistroSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password', 'email']
        extra_kwargs = {'password': {'write_only': True}} # La contraseña no se devuelve en el JSON

    def create(self, validated_data):
        # Usamos create_user para que la contraseña se guarde encriptada
        user = User.objects.create_user(**validated_data)
        return user