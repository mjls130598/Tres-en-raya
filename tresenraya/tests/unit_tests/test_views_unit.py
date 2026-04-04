import pytest
from rest_framework import status
from unittest.mock import MagicMock, patch
from django.contrib.auth.models import User
from tresenraya.views import CrearPartidaView, ListarPartidasView, RegistroView

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
    
    @patch('random.shuffle')
    @patch('tresenraya.models.Celda.objects.create') 
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
        mock_celda_create,
        mock_shuffle,
        view, 
        request_mock
    ):
        """
        Verifica el flujo completo de creación:
        1. Creación de objetos.
        2. Mezcla aleatoria de jugadores.
        3. Creación de las 9 celdas.
        """
        # --- Configuración de Mocks ---
        # Mock del oponente
        oponente_mock = MagicMock()
        oponente_mock.username = "rival_test"
        mock_user_get.return_value = oponente_mock

        # Mock de la partida (debe tener un ID y un método save)
        partida_instancia = MagicMock(id=1)
        mock_partida_create.return_value = partida_instancia

        # Mock de los jugadores creados
        jugador1_mock = MagicMock()
        jugador1_mock.usuario.username = "usuario_logueado"
        jugador2_mock = MagicMock()
        jugador2_mock.usuario.username = "rival_test"
        mock_jugador_create.side_effect = [jugador1_mock, jugador2_mock]

        # Forzamos el shuffle para que el primer jugador sea siempre el logueado
        # y así el test sea determinista.
        def mock_shuffle_logic(lista):
            lista[0], lista[1] = request_mock.user, oponente_mock
        mock_shuffle.side_effect = mock_shuffle_logic

        # --- Ejecución ---
        response = view.post(request_mock)

        # --- Aserciones ---
        assert response.status_code == status.HTTP_201_CREATED
        
        # 1. Verificar que se crearon los objetos base
        mock_partida_create.assert_called_once()
        mock_tablero_create.assert_called_once_with(partida=partida_instancia)
        
        # 2. Verificar que se crearon exactamente 2 jugadores
        assert mock_jugador_create.call_count == 2
        
        # 3. Verificar la lógica de asignación de turno (jugador 0 tras el shuffle)
        assert partida_instancia.turno_actual == request_mock.user
        partida_instancia.save.assert_called()

        # 4. Verificar la creación de la cuadrícula (3x3 = 9 celdas)
        assert mock_celda_create.call_count == 9
        
        # 5. Verificar estructura de la respuesta
        assert response.data["partida_id"] == 1
        assert "jugador_x" in response.data
        assert "jugador_o" in response.data
        assert response.data["turno_actual"] == "usuario_logueado"

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