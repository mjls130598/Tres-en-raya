import random

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import permissions, status
from django.db import transaction
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

        try:
            # Creación de la partida dentro de una transacción
            # Para asegurar de que se guarda todo o nada
            with transaction.atomic():

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
                
                return Response({
                    "partida_id": nueva_partida.id,
                    "jugador_x": jugador1.usuario.username,
                    "jugador_o": jugador2.usuario.username,
                    "turno_actual": nueva_partida.turno_actual.username
                }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"Error": "No se pudo crear la partida"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    

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

    def _validaciones_datos(self, partida_id:int, usuario: User, fila: int, columna:int):
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
        if Movimiento.objects.filter(partida=partida, celda__fila=fila, celda__columna=columna).exists():
            return Response(
                {"Error": "Esa casilla ya está ocupada"},
                status=status.HTTP_400_BAD_REQUEST
            )
        

        return partida, jugador
    
    def _verificar_ganador(self, matriz) -> bool:
        """
        Comprobamos que el tablero actual tiene un ganador después de
        realizar el movimiento.

        Arguments:
            matriz (array[array[str]]): El estado del tablero en ese momento

        Returns:
            hay_ganador (bool): Devuelve True si ya se ha encontrado un ganador
        """

        # 1. Comprobamos si hay alguna fila que esté completa con el mismo símbolo
        if any(
            fila[0] != "" and                        # Si la primera celda de una fila no está vacía
            all(celda == fila[0] for celda in fila)  # Si todas las celdas de esa fila son iguales
            for fila in matriz):
            return True
        
        # 2. Verificamos si hay alguna columna que esté completa con el mismo símbolo
        if any(
            columna[0] != "" and                          # Si la primera celda de una columna no está vacía
            all(celda == columna[0] for celda in columna) # Si todas las celdas de esa columna son iguales
            for columna in zip(*matriz)):                 # (zip se utiliza para iterar por columnas en vez de filas)
            return True
        
        # 3. Chequeamos que las diagonales del tablero estén completas con el mismo símbolo
        tamano_matriz = len(matriz)

        # Diagonal Principal
        primera_celda = matriz[0][0]
        if (
            primera_celda != "" and            # Si la primera celda no está vacía
            all(                               # Si todas las celdas en diagonal (de izq a derch)
               matriz[i][i] == primera_celda   # son iguales
               for i in range(tamano_matriz)
            )
        ):
            return True
        
        # Diagonal Inversa
        primera_celda_inversa = matriz[0][tamano_matriz - 1]
        if (
            primera_celda_inversa != "" and                                 # Si la primera celda no está vacía
            all(                                                            # Si todas las celdas en diagonal     
                matriz[i][tamano_matriz - 1 - i] == primera_celda_inversa   # (de derch a izq) son iguales
                for i in range(tamano_matriz)
            )
        ):
            return True
        
        return False
    
    def _verificar_empate(self, matriz) -> bool:
        """
        Comprobamos que la partida actual haya ocurrido un empate

        Arguments:
            matriz (array[array[str]]): El estado del tablero en ese momento

        Returns:
            hay_empate (bool): Devuelve True si ya no se puede continuar jugando
        """

        def _obtener_lineas():
            """
            Genera todas las líneas que se pueden realizar el tres en raya
            (3 filas, 3 columnas, 2 diagonales) con el tablero actual
            """
            tamano_matriz = len(matriz)

            # Obtener todas las filas de la matriz
            for fila in matriz:
                yield fila      # Envía al for fila por fila

            # Obtener todas las columnas de la matriz
            for columna in zip(*matriz):
                yield columna

            # Obtener la diagonal principal
            yield [matriz[i][i] for i in range(tamano_matriz)]

            # Obtener la diagonal inversa
            yield [matriz[i][tamano_matriz - 1 - i] for i in range(tamano_matriz)]

        # 1. Comprobamos que el tablero esté lleno
        if all(celda != "" for fila in matriz for celda in fila):
            return True
        
        # 2. Verificamos si hay alguna línea "viva"
        # Línea viva -> línea que no contiene símbolos de ambos jugadores
        if any(not ("X" in linea and "O" in linea) for linea in _obtener_lineas()):
            return False
        
        return True
    
    def _cambiar_turno(self, partida: Partida):
        """
        Actualizamos la partida cambiando el turno

        Arguments:
            partida (Partida): La partida con su estado actual
        """

        # Buscamos el otro jugador
        jugador_actual = partida.turno_actual
        siguiente_jugador = Jugador.objects.filter(partida=partida).exclude(usuario=jugador_actual).first()

        # Actualizamos la partida
        partida.turno_actual = siguiente_jugador.usuario
        partida.save()

    def post(self, request):

        # 1. OBTENCIÓN DE LOS DATOS RECIBIDOS
        partida_id = request.data.get('partida_id')
        fila = int(request.data.get('fila'))
        columna = int(request.data.get('columna'))

        # 2. VALIDACIONES

        validacion = self._validaciones_datos(partida_id, request.user, fila, columna)

        # Si devuelve un Response del error, se devuelve al usuario
        if isinstance(validacion, Response):
            return validacion
        
        # Sino, se recoge la partida y el jugador
        partida, jugador = validacion
        
        # 3. EJECUCIÓN DEL MOVIMIENTO

        # Obtención de la celda
        try:
            celda = Celda.objects.get(tablero=partida.tablero, fila=fila,
                                      columna=columna)
        except Celda.DoesNotExist:
            return Response(
                {"Error": "Esa celda no existe en el tablero"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Modificamos la celda asignando el símbolo del jugador
        celda.valor = jugador.simbolo
        celda.save()

        # Guardamos registro de log
        Movimiento.objects.create(
            partida=partida,
            jugador=request.user,
            celda=celda
        )

        # 4. LÓGICA DEL JUEGO

        # Comprobamos si ha habido algún ganador
        matriz = partida.matriz_tablero
        hay_ganador = self._verificar_ganador(matriz)

        # Si hay un ganador, finalizamos jugada
        if hay_ganador:
            partida.finalizada = True
            partida.ganador = request.user
            partida.save()
            return Response(
                {
                    "estado": "victoria",
                    "ganador": request.user.username,
                    "tablero": matriz
                },
                status=status.HTTP_200_OK
            )
        
        # Verificamos que se ha producido un empate
        hay_empate = self._verificar_empate(matriz)

        # Si hay empate, finalizamos la jugada
        if hay_empate:
            partida.finalizada = True
            partida.save()
            return Response(
                {
                    "estado": "empate",
                    "tablero": matriz
                },
                status=status.HTTP_200_OK
            )
        
        # Si se puede continuar la partida, actualizamos turnos
        self._cambiar_turno(partida)
        
        return Response(
            {
                "estado": "jugando",
                "turno_actual": partida.turno_actual.username,
                "tablero": matriz
            },
            status=status.HTTP_200_OK
        )
