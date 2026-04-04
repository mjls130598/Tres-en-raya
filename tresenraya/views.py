import random

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import permissions, status
from tresenraya.models import Celda, Jugador, Partida, Tablero
from django.contrib.auth.models import User
from tresenraya.serializers import RegistroSerializer

class RegistroView(APIView):
    """Registro de un nuevo usuario en el sistema"""
    def post(self, request):
        serializer = RegistroSerializer(data=request.data)

        # Si el usuario dado es válido
        if serializer.is_valid():
            # Guardamos el usuario
            user = serializer.save()
            
            # Generamos el token para el nuevo usuario
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                "token": token.key,
                "username": user.username,
                "message": "Usuario creado con éxito."
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CrearPartidaView(APIView):
    """Creación de una nueva partida"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):

        # 1. Obtener el nombre del oponente
        oponente_name = request.data.get('oponente')

        # Actualmente, obligamos al usuario a escribir un oponente
        # FUTURO: Esperar que se una un oponente o que el oponente sea "inteligente"
        if not oponente_name:
            return Response(
                {"Error": "Debes especificar un oponente"},
                status=status.HTTP_400_BAD_REQUEST) 
        
        try:
            oponente = User.objects.get(username = oponente_name)
        except User.DoesNotExist:
            return Response(
                {"Error": "El oponente dado no existe"},
                status=status.HTTP_404_NOT_FOUND)
        
        if oponente == request.user:
            return Response(
                {"Error": "No puedes jugar contra ti mismo"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Crear objetos de Partida y Tablero en la BBDD
        nueva_partida = Partida.objects.create()
        nuevo_tablero = Tablero.objects.create(partida = nueva_partida)

        # 3. Creación de jugadores
        jugadores = [request.user, oponente]
        random.shuffle(jugadores)

        jugador1 = Jugador.objects.create(
            usuario = jugadores[0],
            partida = nueva_partida,
            simbolo = "X"
        )

        jugador2 = Jugador.objects.create(
            usuario = jugadores[1],
            partida = nueva_partida,
            simbolo = "O"
        )

        # Asignamos el turno al jugador1
        nueva_partida.turno_actual = jugadores[0]
        nueva_partida.save()

        # 4. Creación del contenido del Tablero
        [[Celda.objects.create(
            tablero = nuevo_tablero,
            fila = fila,
            columna = columna
            ) for columna in range(3)] for fila in range(3)]
        
        return Response({
            "partida_id": nueva_partida.id,
            "jugador_x": jugador1.usuario.username,
            "jugador_o": jugador2.usuario.username,
            "turno_actual": nueva_partida.turno_actual.username
        }, status=status.HTTP_201_CREATED)
