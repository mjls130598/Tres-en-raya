import pytest
from rest_framework import status
from unittest.mock import MagicMock, patch
from tresenraya.views import CrearPartidaView, RegistroView

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