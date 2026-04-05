import pytest
from rest_framework import status
from unittest.mock import MagicMock, patch
from rest_framework.response import Response
from django.contrib.auth.models import User
from tresenraya.models import Celda, Jugador, Partida
from tresenraya.views import CrearPartidaView, ListarPartidasView, RealizarMovimientoView, RegistroView

class TestRegistroViewUnitario:
    """
    Conjunto de pruebas unitarias para la vista de Registro.
    Se utiliza mockeo exhaustivo para evitar la dependencia de la base de datos
    y el sistema de autenticación real de Django.
    """

    @pytest.fixture
    def view(self):
        return RegistroView()

    @pytest.fixture
    def request_mock(self):
        """Simula un objeto request de DRF con datos de entrada."""
        
        request = MagicMock()
        request.data = {
            "username": "tester",
            "password": "password123"
        }
        return request

    @patch('tresenraya.views.RegistroSerializer')
    @patch('tresenraya.views.Token')
    def test_post_registro_exitoso(self, mock_token_model, mock_serializer_class, view, request_mock):
        """
        Verifica que un registro válido crea el usuario, genera un token 
        y devuelve una respuesta 201 con los datos correctos.
        """

        # Configuración del Serializer
        mock_serializer = mock_serializer_class.return_value
        mock_serializer.is_valid.return_value = True
        
        # Simulación del usuario creado
        mock_user = MagicMock()
        mock_user.username = "tester"
        mock_serializer.save.return_value = mock_user

        # Simulación del Token (get_or_create devuelve tupla: objeto, creado)
        mock_token = MagicMock()
        mock_token.key = "token_de_prueba_123"
        mock_token_model.objects.get_or_create.return_value = (mock_token, True)

        # Ejecución
        response = view.post(request_mock)

        # Aserciones
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["token"] == "token_de_prueba_123"
        assert response.data["username"] == "tester"
        mock_serializer.save.assert_called_once()
        mock_token_model.objects.get_or_create.assert_called_once_with(user=mock_user)

    @patch('tresenraya.views.RegistroSerializer')
    def test_post_registro_fallido_serializer_invalido(self, mock_serializer_class, view, request_mock):
        """
        Verifica que si los datos de entrada son inválidos, la vista devuelve 
        un error 400 y los detalles del error del serializer sin crear tokens.
        """

        # Configuración para que el serializer falle
        mock_serializer = mock_serializer_class.return_value
        mock_serializer.is_valid.return_value = False
        mock_serializer.errors = {"password": ["La contraseña es muy corta."]}

        # Ejecución
        response = view.post(request_mock)

        # Aserciones
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data
        mock_serializer.is_valid.assert_called_once()
        
        # Importante: Verificar que NO se llamó a la creación del token
        with patch('tresenraya.views.Token') as mock_token_model:
            assert mock_token_model.objects.get_or_create.called is False

    @patch('tresenraya.views.RegistroSerializer')
    @patch('tresenraya.views.Token')
    def test_post_registro_token_ya_existente(self, mock_token_model, mock_serializer_class, view, request_mock):
        """
        Verifica que la vista funciona correctamente incluso si el token ya 
        existía para ese usuario (created=False en get_or_create).
        """

        mock_serializer = mock_serializer_class.return_value
        mock_serializer.is_valid.return_value = True
        mock_user = MagicMock(username="tester")
        mock_serializer.save.return_value = mock_user

        # El token ya existe (created = False)
        mock_token = MagicMock(key="token_existente")
        mock_token_model.objects.get_or_create.return_value = (mock_token, False)

        response = view.post(request_mock)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["token"] == "token_existente"

class TestCrearPartidaUnitario:
    """Tests de lógica pura sin tocar la base de datos."""

    @pytest.fixture
    def view(self):
        return CrearPartidaView()

    @pytest.fixture
    def request_mock(self):
        request = MagicMock()
        request.user = MagicMock(username="usuario_logueado")
        request.data = {"oponente": "rival_test"}
        return request
    
    @patch('django.db.transaction.atomic')
    @patch('random.shuffle')
    @patch('tresenraya.models.Jugador.objects.create')
    @patch('tresenraya.models.Tablero.objects.create')
    @patch('tresenraya.models.Partida.objects.create')
    @patch('django.contrib.auth.models.User.objects.get')
    def test_post_creacion_partida_exitosa(
        self, 
        mock_user_get, 
        mock_partida_create, 
        mock_tablero_create, 
        mock_jugador_create,
        mock_shuffle,
        mock_atomic, # Añadido para la transacción
        view, 
        request_mock
    ):
        """
        Verifica el flujo completo de creación de una partida entre dos usuarios.
        
        Comprueba que se creen la partida, el tablero y los dos jugadores con 
        sus símbolos correspondientes.
        """
        # --- Configuración de Datos de Entrada ---
        request_mock.data = {'oponente': 'rival_test'}
        request_mock.user.username = "usuario_logueado"

        # --- Configuración de Mocks ---
        # Mock del oponente encontrado en la BD
        oponente_mock = MagicMock(spec=User)
        oponente_mock.username = "rival_test"
        mock_user_get.return_value = oponente_mock

        # Mock de la instancia de partida creada
        partida_instancia = MagicMock(spec=Partida)
        partida_instancia.id = 1
        mock_partida_create.return_value = partida_instancia

        # Mock de los objetos Jugador que devuelve el create
        jugador1_mock = MagicMock()
        jugador1_mock.usuario.username = "usuario_logueado"
        jugador2_mock = MagicMock()
        jugador2_mock.usuario.username = "rival_test"
        
        # El primer create devuelve jugador X, el segundo jugador O
        mock_jugador_create.side_effect = [jugador1_mock, jugador2_mock]

        # Forzamos el shuffle para que el orden sea predecible en el test
        # (El primer elemento será el turno_actual)
        mock_shuffle.side_effect = lambda x: x.sort(key=lambda u: u.username, reverse=True) 

        # --- Ejecución ---
        response = view.post(request_mock)

        # --- Aserciones ---
        assert response.status_code == status.HTTP_201_CREATED
        
        # 1. Verificar creación de modelos base
        mock_partida_create.assert_called_once()
        mock_tablero_create.assert_called_once_with(partida=partida_instancia)
        
        # 2. Verificar creación de los 2 jugadores (X y O)
        assert mock_jugador_create.call_count == 2
        
        # 3. Verificar asignación de turno y persistencia
        # En el código: nueva_partida.turno_actual = jugadores[0]
        assert partida_instancia.save.called
        
        # 4. Verificar estructura de la respuesta JSON
        assert response.data["partida_id"] == 1
        assert response.data["jugador_x"] == "usuario_logueado"
        assert response.data["jugador_o"] == "rival_test"
        assert "turno_actual" in response.data

    def test_post_sin_nombre_oponente(self, view, request_mock):
        """Verifica el error 400 si no se envía el campo 'oponente'."""

        request_mock.data = {}
        response = view.post(request_mock)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Debes especificar un oponente" in response.data["Error"]

    @patch('django.contrib.auth.models.User.objects.get')
    def test_post_oponente_no_existe(self, mock_user_get, view, request_mock):
        """Verifica el error 404 si el oponente no está registrado."""

        from django.contrib.auth.models import User
        mock_user_get.side_effect = User.DoesNotExist
        
        response = view.post(request_mock)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "El oponente dado no existe" in response.data["Error"]

    @patch('django.contrib.auth.models.User.objects.get')
    def test_post_jugar_contra_si_mismo(self, mock_user_get, view, request_mock):
        """Verifica que el usuario no pueda retarse a sí mismo."""

        user_mock = request_mock.user
        mock_user_get.return_value = user_mock # El oponente es el mismo que el user

        response = view.post(request_mock)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No puedes jugar contra ti mismo" in response.data["Error"]

    @patch('tresenraya.models.Partida.objects.create')
    @patch('django.contrib.auth.models.User.objects.get')
    def test_post_error_creacion_partida_excepcion_general(
        self, 
        mock_user_get, 
        mock_partida_create, 
        view, 
        request_mock
    ):
        """
        Verifica que si ocurre un error inesperado al crear la partida (p.ej. fallo de BD), 
        la vista capture la excepción y devuelva un error 500.
        """
        
        # --- Configuración de Mocks ---
        # 1. El oponente se encuentra correctamente
        request_mock.data = {'oponente': 'rival_test'}
        oponente_mock = MagicMock(spec=User)
        oponente_mock.username = "rival_test"
        mock_user_get.return_value = oponente_mock

        # 2. Forzamos una excepción genérica al intentar crear la partida
        # Esto simulará cualquier fallo inesperado dentro del bloque 'try'
        mock_partida_create.side_effect = Exception("Fallo crítico de base de datos")

        # --- Ejecución ---
        response = view.post(request_mock)

        # --- Aserciones ---
        # Verificamos que la respuesta sea un 500
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Verificamos el mensaje de error definido en tu código
        assert response.data["Error"] == "No se pudo crear la partida"

class TestListartresenrayaUnitario:

    @pytest.fixture
    def view(self):
        return ListarPartidasView()

    @pytest.fixture
    def request_mock(self):
        request = MagicMock()
        request.user = MagicMock(spec=User)
        request.user.id = 1
        request.user.pk = 1
        request.query_params = {}
        return request

    # Usamos patch en el Manager de Partida para evitar que toque la lógica de DB
    @patch('tresenraya.models.Partida.objects.filter')
    def test_get_error_parametro_finalizada_invalido(self, mock_filter, view, request_mock):
        """Verifica el error 422 si 'finalizada' no es true o false."""

        # Configuramos el mock para que devuelva otro mock (el queryset)
        mock_filter.return_value = MagicMock()
        request_mock.query_params = {'finalizada': 'talvez'}
        
        response = view.get(request_mock)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.data["Error"] == "El parámetro 'finalizada' debe ser 'true' o 'false'"

    @patch('tresenraya.models.Partida.objects.filter')
    @patch('django.contrib.auth.models.User.objects.get')
    def test_get_error_oponente_no_existe(self, mock_user_get, mock_filter, view, request_mock):
        """Verifica el error 404 si el oponente filtrado no existe."""
        
        # Evitamos que la primera línea de la vista falle
        mock_filter.return_value = MagicMock()
        
        # Configuramos el error del oponente
        mock_user_get.side_effect = User.DoesNotExist
        request_mock.query_params = {'oponente': 'fantasma'}
        
        response = view.get(request_mock)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["Error"] == "El oponente dado no existe"

    @patch('django.contrib.auth.models.User.objects.get')
    @patch('tresenraya.views.PartidaListadoSerializer')
    @patch('tresenraya.models.Partida.objects.filter')
    def test_get_llamada_correcta_con_filtros(self, mock_filter_base, mock_serializer, mock_user_get, view, request_mock):
        """Verifica que se llame al filtro base por el usuario de la petición."""
        
        mock_qs_finalizada = MagicMock()
        mock_qs_oponente = MagicMock()

        mock_filter_base.return_value = mock_qs_finalizada
        mock_qs_finalizada.filter.return_value = mock_qs_oponente
        
        oponente_mock = MagicMock()
        mock_user_get.return_value = oponente_mock
        mock_serializer.return_value.data = [{"id": 1}]

        request_mock.query_params = {
            'finalizada': 'true',
            'oponente': 'usuario_rival'
        }

        response = view.get(request_mock)

        assert response.status_code == status.HTTP_200_OK
        mock_filter_base.assert_called_once_with(jugador__usuario=request_mock.user)
        mock_qs_finalizada.filter.assert_called_once_with(finalizada=True)
        mock_qs_oponente.filter.assert_called_once_with(jugador__usuario=oponente_mock)

    @patch('tresenraya.views.PartidaListadoSerializer')
    @patch('tresenraya.views.Partida.objects.filter')
    def test_get_llamada_correcta_sin_filtros(self, mock_filter, mock_serializer, view, request_mock):
        """Verifica que se llame al filtro base por el usuario de la petición."""
        
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        mock_serializer.return_value.data = []

        response = view.get(request_mock)

        assert response.status_code == status.HTTP_200_OK
        # Verifica que el primer filtro sea por el usuario autenticado
        mock_filter.assert_called_once_with(jugador__usuario=request_mock.user)

class TestRealizarMovimientoUnitario:

    @pytest.fixture
    def view(self):
        return RealizarMovimientoView()

    @pytest.fixture
    def request_mock(self):
        request = MagicMock()
        request.user = MagicMock(spec=User)
        request.user.username = "jugador_1"
        request.data = {
            'partida_id': 1,
            'fila': 1,
            'columna': 1
        }
        return request

    # --- TESTS DE _validaciones_datos ---

    @patch('tresenraya.models.Partida.objects.get')
    def test_validaciones_partida_no_existe(self, mock_get_partida, view, request_mock):
        """Verifica que se devuelva un error 404 si el ID de la partida no existe en la base de datos."""

        mock_get_partida.side_effect = Partida.DoesNotExist
        response = view._validaciones_datos(1, request_mock.user, 1, 1)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["Error"] == "La partida dada no existe"

    @patch('tresenraya.models.Partida.objects.get')
    def test_validaciones_partida_finalizada(self, mock_get_partida, view, request_mock):
        """Verifica que no se permitan movimientos en partidas que ya han marcado el flag de finalizada."""

        partida_mock = MagicMock(spec=Partida)
        partida_mock.finalizada = True
        mock_get_partida.return_value = partida_mock
        
        response = view._validaciones_datos(1, request_mock.user, 1, 1)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["Error"] == "La partida dada ya ha finalizado"

    @patch('tresenraya.models.Jugador.objects.get')
    @patch('tresenraya.models.Partida.objects.get')
    def test_validaciones_usuario_no_en_partida(self, mock_get_partida, mock_get_jugador, view, request_mock):
        """Verifica que un usuario que no está registrado como jugador de la partida reciba un error 403."""

        mock_get_partida.return_value = MagicMock(finalizada=False)
        mock_get_jugador.side_effect = Jugador.DoesNotExist
        
        response = view._validaciones_datos(1, request_mock.user, 1, 1)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["Error"] == "No formas parte de esta partida"

    @patch('tresenraya.models.Jugador.objects.get')
    @patch('tresenraya.models.Partida.objects.get')
    def test_validaciones_no_es_su_turno(self, mock_get_partida, mock_get_jugador, view, request_mock):
        """Verifica que se bloquee el movimiento si el usuario autenticado no es el turno_actual de la partida."""

        otro_usuario = MagicMock(spec=User)
        mock_get_partida.return_value = MagicMock(finalizada=False, turno_actual=otro_usuario)
        mock_get_jugador.return_value = MagicMock()
        
        response = view._validaciones_datos(1, request_mock.user, 1, 1)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["Error"] == "No es tu turno"

    @patch('tresenraya.models.Jugador.objects.get')
    @patch('tresenraya.models.Partida.objects.get')
    def test_validaciones_coordenadas_fuera_limites(self, mock_get_partida, mock_get_jugador, view, request_mock):
        """Verifica que coordenadas menores a 0 o mayores a 2 devuelvan error 400."""

        mock_get_partida.return_value = MagicMock(finalizada=False, turno_actual=request_mock.user)
        mock_get_jugador.return_value = MagicMock()
        
        response = view._validaciones_datos(1, request_mock.user, -1, 0)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        response = view._validaciones_datos(1, request_mock.user, 1, 3)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('tresenraya.models.Movimiento.objects.filter')
    @patch('tresenraya.models.Jugador.objects.get')
    @patch('tresenraya.models.Partida.objects.get')
    def test_validaciones_casilla_ocupada(self, mock_get_partida, mock_get_jugador, mock_mov_filter, view, request_mock):
        """Verifica que no se pueda mover en una celda donde ya existe un movimiento previo."""

        mock_get_partida.return_value = MagicMock(finalizada=False, turno_actual=request_mock.user)
        mock_get_jugador.return_value = MagicMock()
        mock_mov_filter.return_value.exists.return_value = True
        
        response = view._validaciones_datos(1, request_mock.user, 1, 1)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["Error"] == "Esa casilla ya está ocupada"

    @patch('tresenraya.models.Movimiento.objects.filter')
    @patch('tresenraya.models.Jugador.objects.get')
    @patch('tresenraya.models.Partida.objects.get')
    def test_validaciones_datos_exitosas_devuelve_objetos(self, mock_get_partida, mock_get_jugador, mock_mov_filter, view, request_mock):
        """Verifica que si todos los datos son correctos, la función devuelva la partida y el jugador en lugar de una respuesta de error."""

        # Configuramos una partida activa donde el turno es del usuario que pide el movimiento
        partida_mock = MagicMock(spec=Partida)
        partida_mock.finalizada = False
        partida_mock.turno_actual = request_mock.user
        mock_get_partida.return_value = partida_mock

        # Configuramos un jugador que pertenece a esa partida
        jugador_mock = MagicMock(spec=Jugador)
        jugador_mock.usuario = request_mock.user
        mock_get_jugador.return_value = jugador_mock

        # Simulamos que la casilla está libre (el filtro de Movimiento devuelve False en .exists())
        mock_mov_filter.return_value.exists.return_value = False

        # Ejecutamos la función con coordenadas válidas (p.ej. 1, 1)
        resultado = view._validaciones_datos(1, request_mock.user, 1, 1)

        # Comprobamos que no sea un objeto Response y que contenga los objetos esperados
        assert not isinstance(resultado, Response)
        partida_resultado, jugador_resultado = resultado
        assert partida_resultado == partida_mock
        assert jugador_resultado == jugador_mock

    # --- TESTS DE _verificar_ganador ---

    def test_verificar_ganador_fila_superior(self, view):
        """Verifica que se detecte la victoria en la fila superior."""

        # Caso Fila Superior
        matriz_superior = [
            ["X", "X", "X"],
            ["O", "", "O"],
            ["", "", ""]
        ]
        assert view._verificar_ganador(matriz_superior) is True

    def test_verificar_ganador_fila_media(self, view):
        """Verifica que se detecte la victoria en la fila media."""

        # Caso Fila Media
        matriz_media = [
            ["X", "O", "X"],
            ["O", "O", "O"],
            ["", "X", ""]
        ]
        assert view._verificar_ganador(matriz_media) is True

    def test_verificar_ganador_fila_inferior(self, view):
        """Verifica que se detecte la victoria en la fila inferior)."""

        # Caso Fila Inferior
        matriz_inferior = [
            ["", "", "O"],
            ["O", "X", ""],
            ["X", "X", "X"]
        ]
        assert view._verificar_ganador(matriz_inferior) is True

    def test_verificar_ganador_columna_izq(self, view):
        """Verifica que se detecte la victoria en la columna izquierda"""

        # Caso Columna Izquierda
        matriz_izq = [
            ["O", "X", ""],
            ["O", "", ""],
            ["O", "X", "X"]
        ]
        assert view._verificar_ganador(matriz_izq) is True

    def test_verificar_ganador_columna_medio(self, view):
        """Verifica que se detecte la victoria en la columna medio"""

        # Caso Columna Medio
        matriz_medio = [
            ["O", "X", ""],
            ["", "X", ""],
            ["O", "X", "X"]
        ]
        assert view._verificar_ganador(matriz_medio) is True

    def test_verificar_ganador_columna_derch(self, view):
        """Verifica que se detecte la victoria en la columna derecha"""

        # Caso Columna Derecha
        matriz_derch = [
            ["O", "X", ""],
            ["O", "", ""],
            ["O", "X", "X"]
        ]
        assert view._verificar_ganador(matriz_derch) is True

    def test_verificar_ganador_diagonal_principal(self, view):
        """Verifica que se detecte la victoria cuando se completa la diagonal que va desde la posición [0][0] hasta la [2][2]."""

        matriz_diagonal = [
            ["X", "O", ""],
            ["", "X", "O"],
            ["", "", "X"]
        ]
        assert view._verificar_ganador(matriz_diagonal) is True

    def test_verificar_ganador_diagonal_inversa(self, view):
        """Verifica que la lógica detecte correctamente una victoria en la diagonal secundaria."""

        matriz = [
            ["", "O", "X"],
            ["", "X", ""],
            ["X", "", "O"]
        ]
        assert view._verificar_ganador(matriz) is True

    def test_verificar_ganador_vacio(self, view):
        """Verifica que no haya ganador en un tablero vacío."""

        matriz = [["", "", ""], ["", "", ""], ["", "", ""]]
        assert view._verificar_ganador(matriz) is False

    def test_verificar_ganador_fila_con_celdas_vacias(self, view):
        """Verifica que una fila compuesta solo por strings vacíos no se cuente como una victoria."""

        matriz_vacia = [
            ["", "", ""],
            ["X", "O", "X"],
            ["O", "X", "O"]
        ]
        # Aunque todos los elementos son iguales (son ""), el código verifica fila[0] != ""
        assert view._verificar_ganador(matriz_vacia) is False

    def test_verificar_ganador_columna_con_celdas_vacias(self, view):
        """Verifica que una columna compuesta solo por strings vacíos no se cuente como una victoria."""

        matriz_vacia = [
            ["", "O", "X"],
            ["", "O", "X"],
            ["", "X", "O"]
        ]
        # Aunque todos los elementos son iguales (son ""), el código verifica fila[0] != ""
        assert view._verificar_ganador(matriz_vacia) is False

    # --- TESTS DE _verificar_empate ---

    def test_verificar_empate_filas(self, view):
        """Verifica que se detecte el empate cuando todas las filas contienen símbolos de ambos jugadores y no hay líneas vivas."""

        matriz = [
            ["X", "X", ""],
            ["O", "O", "X"],
            ["X", "", "O"]
        ]
        assert view._verificar_empate(matriz) is False

    def test_verificar_empate_columnas(self, view):
        """Verifica que no se detecte el empate en las columnas."""

        matriz_columna = [
            ["X", "O", ""], # Fila 1: Bloqueada (X y O)
            ["O", "X", ""], # Fila 2: Bloqueada (O y X)
            ["X", "O", ""]  # Fila 3: Bloqueada (X y O)
        ]

        assert view._verificar_empate(matriz_columna) is False

    def test_verificar_empate_diagonal_principal(self, view):
        """erifica que no se detecte el empate en la diagonal principal"""

        matriz_diagonal_principal = [
            ["X", "O", "O"],
            ["O", "", "X"],
            ["O", "", "X"]
        ]
        
        assert view._verificar_empate(matriz_diagonal_principal) is False

    def test_verificar_empate_diagonal_inversa(self, view):
        """erifica que no se detecte el empate en la diagonal inversa"""

        matriz_diagonal_inversa = [
            ["O", "X", "O"],
            ["O", "", "X"],
            ["O", "", "X"]
        ]
        
        assert view._verificar_empate(matriz_diagonal_inversa) is False

    def test_verificar_empate_tablero_completamente_lleno(self, view):
        """Verifica que la primera condición de la función (tablero lleno) devuelva True inmediatamente."""

        matriz_llena = [
            ["X", "O", "X"],
            ["X", "X", "O"],
            ["O", "X", "O"]
        ]
        assert view._verificar_empate(matriz_llena) is True

    # --- TESTS DE _cambiar_turno ---

    @patch('tresenraya.models.Jugador.objects.filter')
    def test_cambiar_turno(self, mock_jugador_filter, view):
        """Verifica que el turno se transfiera correctamente al oponente."""

        usuario_actual = MagicMock(spec=User)
        usuario_siguiente = MagicMock(spec=User)
        partida = MagicMock(spec=Partida, turno_actual=usuario_actual)
        
        mock_jugador_filter.return_value.exclude.return_value.first.return_value = MagicMock(usuario=usuario_siguiente)
        
        view._cambiar_turno(partida)
        
        assert partida.turno_actual == usuario_siguiente
        partida.save.assert_called_once()

    # --- TESTS DEL MÉTODO POST ---

    @patch('tresenraya.models.Celda.objects.get')
    @patch.object(RealizarMovimientoView, '_validaciones_datos')
    def test_post_celda_no_existe(self, mock_val, mock_celda_get, view, request_mock):
        """Verifica el error si la celda solicitada no existe en el tablero (400 Bad Request)."""

        mock_val.return_value = (MagicMock(), MagicMock())
        mock_celda_get.side_effect = Celda.DoesNotExist
        
        response = view.post(request_mock)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["Error"] == "Esa celda no existe en el tablero"

    @patch.object(RealizarMovimientoView, '_verificar_empate', return_value=True)
    @patch.object(RealizarMovimientoView, '_verificar_ganador', return_value=False)
    @patch('tresenraya.models.Movimiento.objects.create')
    @patch('tresenraya.models.Celda.objects.get')
    @patch.object(RealizarMovimientoView, '_validaciones_datos')
    def test_post_empate_finaliza_partida(self, mock_val, mock_celda, mock_mov, mock_gan, mock_emp, view, request_mock):
        """Verifica que si la jugada provoca un empate, la partida se marque como finalizada."""

        partida_mock = MagicMock(spec=Partida)
        mock_val.return_value = (partida_mock, MagicMock(simbolo="O"))
        mock_celda.return_value = MagicMock()

        response = view.post(request_mock)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["estado"] == "empate"
        assert partida_mock.finalizada is True
        partida_mock.save.assert_called()

    @patch.object(RealizarMovimientoView, '_validaciones_datos')
    def test_post_error_en_validacion(self, mock_val, view, request_mock):
        """Verifica que si la función interna de validación devuelve un Response (error), el POST lo retorne directamente."""

        expected_response = Response({"Error": "Cualquier error"}, status=status.HTTP_400_BAD_REQUEST)
        mock_val.return_value = expected_response
        
        response = view.post(request_mock)
        
        assert response == expected_response
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch.object(RealizarMovimientoView, '_verificar_ganador', return_value=True)
    @patch('tresenraya.models.Movimiento.objects.create')
    @patch('tresenraya.models.Celda.objects.get')
    @patch.object(RealizarMovimientoView, '_validaciones_datos')
    def test_post_guarda_datos_en_victoria(self, mock_val, mock_celda_get, mock_mov_create, mock_ganador, view, request_mock):
        """Verifica que cuando hay un ganador, se actualice el flag 'finalizada', se asigne el 'ganador' en la BD y la respuesta contenga el estado correcto."""

        partida_mock = MagicMock(spec=Partida)
        partida_mock.matriz_tablero = [["X", "X", "X"], ["O", "", ""], ["O", "", ""]]
        jugador_mock = MagicMock(simbolo="X")
        
        mock_val.return_value = (partida_mock, jugador_mock)
        celda_mock = MagicMock(spec=Celda)
        mock_celda_get.return_value = celda_mock

        response = view.post(request_mock)

        # Verificación de persistencia
        assert partida_mock.finalizada is True
        assert partida_mock.ganador == request_mock.user
        partida_mock.save.assert_called()
        
        # Verificación de respuesta
        assert response.status_code == status.HTTP_200_OK
        assert response.data["estado"] == "victoria"
        assert response.data["ganador"] == "jugador_1"
        assert response.data["tablero"] == partida_mock.matriz_tablero

    @patch.object(RealizarMovimientoView, '_cambiar_turno')
    @patch.object(RealizarMovimientoView, '_verificar_empate', return_value=False)
    @patch.object(RealizarMovimientoView, '_verificar_ganador', return_value=False)
    @patch('tresenraya.models.Movimiento.objects.create')
    @patch('tresenraya.models.Celda.objects.get')
    @patch.object(RealizarMovimientoView, '_validaciones_datos')
    def test_post_continua_partida_y_cambia_turno(self, mock_val, mock_celda_get, mock_mov_create, mock_gan, mock_emp, mock_cambiar_turno, view, request_mock):
        """Verifica que si la partida continúa, se invoque al cambio de turno, se registre el movimiento y se devuelva el nuevo tablero con el turno actualizado."""

        # Setup de mocks
        partida_mock = MagicMock(spec=Partida)
        partida_mock.matriz_tablero = [["X", "", ""], ["", "", ""], ["", "", ""]]
        
        # Simulamos que tras el cambio de turno, el turno_actual es 'jugador_2'
        siguiente_usuario = MagicMock(spec=User)
        siguiente_usuario.username = "jugador_2"
        partida_mock.turno_actual = siguiente_usuario
        
        jugador_mock = MagicMock(simbolo="X")
        mock_val.return_value = (partida_mock, jugador_mock)
        
        celda_mock = MagicMock(spec=Celda)
        mock_celda_get.return_value = celda_mock

        response = view.post(request_mock)

        # Verificamos que se llamó a la lógica de cambio de turno
        mock_cambiar_turno.assert_called_once_with(partida_mock)
        
        # Verificamos que se creó el registro del movimiento en el log
        mock_mov_create.assert_called_once_with(
            partida=partida_mock,
            jugador=request_mock.user,
            celda=celda_mock
        )

        # Verificamos la respuesta al cliente
        assert response.status_code == status.HTTP_200_OK
        assert response.data["estado"] == "jugando"
        assert response.data["turno_actual"] == "jugador_2"
        assert response.data["tablero"] == partida_mock.matriz_tablero