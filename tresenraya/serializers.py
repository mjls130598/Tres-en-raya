from django.contrib.auth.models import User
from rest_framework import serializers

from tresenraya.models import Partida

class RegistroSerializer(serializers.ModelSerializer):
    """Serializador para la creación de usuarios"""
    
    class Meta:
        model = User
        fields = ['username', 'password', 'email']
        extra_kwargs = {'password': {'write_only': True}} # La contraseña no se devuelve en el JSON 🔒

    def create(self, validated_data):
        # Usamos create_user para que la contraseña se guarde encriptada
        user = User.objects.create_user(**validated_data)
        return user
    
class PartidaListadoSerializer(serializers.ModelSerializer):
    """Serializador para obtención del listado de partidas creadas"""

    turno_actual_nombre = serializers.ReadOnlyField(source="turno_actual.username")
    ganador_nombre = serializers.ReadOnlyField(source="ganador.username")
    jugadores = serializers.SerializerMethodField()

    class Meta:
        model = Partida
        fields = ['id', 'finalizada', 'fecha_creacion', 'turno_actual_nombre', 'ganador_nombre', 'jugadores']

    def get_jugadores(self, obj):
        """Obtener todos los jugadores de la partida"""
        return obj.jugador_set.values_list('usuario__username', flat=True)