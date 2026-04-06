from django.contrib.auth.models import User
from rest_framework import serializers

from tresenraya.models import Movimiento, Partida

class RegistroSerializer(serializers.ModelSerializer):
    """Serializador para la creación de usuarios"""
    
    class Meta:
        model = User
        fields = ['username', 'password', 'email']
        extra_kwargs = {'password': {'write_only': True}} # La contraseña no se devuelve en el JSON

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
    
class MovimientoVisualizacionSerializer(serializers.ModelSerializer):
    """Serializador para obtención del listado de movimientos de una partida"""

    jugador_nombre = serializers.ReadOnlyField(source="jugador.username")
    simbolo = serializers.ReadOnlyField(source="celda.valor")
    posicion = serializers.ReadOnlyField(source='coordenadas')
    tablero = serializers.SerializerMethodField() # Se recogerá el tablero después de ese movimiento en "get_tablero"

    class Meta:
        model = Movimiento
        fields = ['instante', 'jugador_nombre', 'simbolo', 'posicion', 'tablero']

    def get_tablero(self, obj):
        """Recrear el tablero después de realizar el movimiento"""

        # 1. Obtenemos las celdas de los movimientos antiguos a este
        movimientos_antiguos = Movimiento.objects.filter(
            partida = obj.partida,
            instante__lte = obj.instante
        ).select_related('celda')

        # 2. Creamos la matriz con los movimientos antiguos
        matriz = [["" for _ in range(3)] for _ in range(3)]

        # 3. Rellenamos la matriz con los movimientos antiguos
        for movimiento in movimientos_antiguos:
            fila = movimiento.celda.fila
            columna = movimiento.celda.columna
            simbolo = movimiento.celda.valor

            matriz[fila][columna] = simbolo

        return matriz        