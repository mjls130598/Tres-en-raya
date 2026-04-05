import random

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import permissions, status
from tresenraya.models import Celda, Jugador, Movimiento, Partida, Tablero
from django.contrib.auth.models import User
from tresenraya.serializers import PartidaListadoSerializer, RegistroSerializer

class RegistroView(APIView):
    """Registro de un nuevo usuario en el sistema"""
    permission_classes = [permissions.AllowAny]

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
    

class ListarPartidasView(APIView):
    """Visualización de todas las partidas de un usuario (además del filtro por finalizada y por oponente)"""

    def get(self, request):

        # Filtramos por las partidas que participe el usuario de la petición
        partidas_usuario = Partida.objects.filter(jugador__usuario=request.user)

        # Si existe, filtramos por partidas finalizadas o no
        finalizada_param = request.query_params.get('finalizada')
        
        if finalizada_param is not None:
            finalizada_param = finalizada_param.lower()
            print(finalizada_param)
            if finalizada_param != "true" and finalizada_param != "false":
                return Response({
                    "Error": "El parámetro 'finalizada' debe ser 'true' o 'false'"
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            
            es_finalizada = finalizada_param == 'true'
            partidas_usuario = partidas_usuario.filter(finalizada = es_finalizada)

        # Si existe, filtramos por oponente
        oponente_param = request.query_params.get('oponente')
        if oponente_param is not None:
            try:
                oponente = User.objects.get(username = oponente_param)
            except User.DoesNotExist:
                return Response(
                    {"Error": "El oponente dado no existe"},
                    status=status.HTTP_404_NOT_FOUND) 
           
            partidas_usuario = partidas_usuario.filter(jugador__usuario=oponente)

        return Response(PartidaListadoSerializer(partidas_usuario, many=True).data)


class RealizarMovimientoView(APIView):
    """Realización de los movimientos dentro de una partida"""

    def _validaciones_datos(self, partida_id, usuario, fila, columna):
        """
        Validamos los datos recibidos antes de realizar cualquier movimiento en el tablero.
        Si todos los datos son correctos, se devuelve la partida y el jugador que
        realiza el movimiento

        Arguments:
            partida_id (int): El id de la partida
            usuario (User): El usuario que quiere realizar el movimiento
            fila, columna (int): Las coordenadas del movimiento

        
        Returns:
            respuesta (Response): La respuesta con el error encontrado
            partida   (Partida) : La partida completa
            jugador   (Jugador) : El jugador de esa partida
        """

        # Obtenemos la partida
        try:
            partida = Partida.objects.get(id=partida_id)
        except Partida.DoesNotExist:
            return Response(
                {"Error": "La partida dada no existe"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificamos que la partida no esté terminada
        if partida.finalizada:
            return Response(
                {"Error": "La partida dada ya ha finalizado"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Comprobamos que el usuario forma parte de la partida
        try:
            jugador = Jugador.objects.get(partida=partida, usuario=usuario)
        except Jugador.DoesNotExist:
            return Response(
                {"Error": "No formas parte de esta partida"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Comprobamos que el usuario es el que tiene el turno
        if partida.turno_actual != usuario:
            return Response(
                {"Error": "No es tu turno"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verificamos que la fila y la columna esté dentro del tablero
        if not(0 <= fila <= 2 and 0 <= columna <= 2):
            return Response(
                {"Error": "Coordenadas fuera del tablero"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Chequeamos que la celda está vacía
        if Movimiento.objects.filter(partida, celda__fila=fila, celda__columna=columna).exists():
            return Response(
                {"Error": "Esa casilla ya está ocupada"},
                status=status.HTTP_400_BAD_REQUEST
            )
        

        return partida, jugador

    def post(self, request):

        # 1. OBTENCIÓN DE LOS DATOS RECIBIDOS
        partida_id = request.data.get('partida_id')
        fila = request.data.get('fila')
        columna = request.data.get('columna')

        # 2. VALIDACIONES

        validacion = self._validaciones_datos(partida_id, request.user, fila, columna)

        # Si devuelve un Response del error, se devuelve al usuario
        if isinstance(validacion, Response):
            return validacion
        
        # Sino, se recoge la partida y el jugador
        partida, jugador = validacion
        
        # 3. EJECUCIÓN DEL MOVIMIENTO

        # Creación/obtención del tablero
        tablero, _ = Tablero.objects.get_or_create(tablero=partida)

        # Creación/obtención de la celda
        celda, _ = Celda.objects.get_or_create(tablero=tablero, fila=fila,
                                               columna=columna, valor=jugador.simbolo)

        # Guardamos registro de log
        Movimiento.objects.create(
            partida=partida,
            jugador=request.user,
            celda=celda
        )
