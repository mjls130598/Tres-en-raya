import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

@pytest.mark.django_db
class TestRegistroViewIntegracion:
    """
    Tests de integración para RegistroView.
    Simula peticiones HTTP reales al endpoint de registro.
    """

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def url_registro(self):
        return reverse('signup') 

    def test_flujo_completo_registro_exitoso(self, api_client, url_registro):
        """
        Verifica que una petición POST válida crea el usuario, el token 
        y devuelve el JSON esperado con status 201.
        """

        payload = {
            "username": "nuevo_jugador",
            "password": "password_seguro",
            "email": "jugador@test.com"
        }

        response = api_client.post(url_registro, payload, format='json')

        # 1. Verificar respuesta HTTP
        assert response.status_code == status.HTTP_201_CREATED
        assert "token" in response.data
        assert response.data["username"] == "nuevo_jugador"

        # 2. Verificar Base de Datos
        user = User.objects.get(username="nuevo_jugador")
        assert Token.objects.filter(user=user).exists()
        assert Token.objects.get(user=user).key == response.data["token"]

    def test_registro_fallido_datos_invalidos(self, api_client, url_registro):
        """
        Verifica que el endpoint rechaza peticiones con datos incompletos
        y no crea usuarios ni tokens accidentalmente.
        """

        payload_incompleto = {"username": "solo_nombre"} # Falta password

        response = api_client.post(url_registro, payload_incompleto, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert User.objects.count() == 0
        assert Token.objects.count() == 0

@pytest.mark.django_db
class TestLoginIntegracion:
    """
    Tests de integración para el flujo de inicio de sesión y 
    obtención de tokens de autenticación.
    """

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def usuario_creado(self):
        """Crea un usuario real en la base de datos para las pruebas."""
        return User.objects.create_user(
            username="jugador_pro", 
            password="password_seguro_123",
            email="pro@test.com"
        )

    @pytest.fixture
    def url_login(self):
        """
        Obtiene la URL del endpoint de login. 
        Asegúrate de que en urls.py tengas: path('login/', ..., name='login')
        """
        return reverse('login')

    def test_login_exitoso_genera_token(self, api_client, usuario_creado, url_login):
        """
        Verifica que un usuario con credenciales correctas recibe un token
        y un código de estado 200.
        """
        payload = {
            "username": "jugador_pro",
            "password": "password_seguro_123"
        }

        response = api_client.post(url_login, payload, format='json')

        # Comprobamos respuesta HTTP
        assert response.status_code == status.HTTP_200_OK
        assert "token" in response.data
        
        # Comprobamos persistencia del Token en la base de datos
        token_db = Token.objects.get(user=usuario_creado)
        assert response.data["token"] == token_db.key

    def test_login_fallido_contrasena_incorrecta(self, api_client, usuario_creado, url_login):
        """
        Verifica que el sistema rechaza el acceso si la contraseña no coincide,
        devolviendo 400 o 401 según tu configuración.
        """
        payload = {
            "username": "jugador_pro",
            "password": "clave_erronea"
        }

        response = api_client.post(url_login, payload, format='json')

        # DRF suele devolver 400 Bad Request o 401 Unauthorized para login fallido
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED]
        assert "token" not in response.data

    def test_login_usuario_inexistente(self, api_client, url_login):
        """
        Verifica que el sistema no genera tokens para usuarios que no
        están registrados en la base de datos.
        """
        payload = {
            "username": "fantasma",
            "password": "password123"
        }

        response = api_client.post(url_login, payload, format='json')

        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED]
        assert Token.objects.count() == 0

    def test_reutilizacion_de_token_existente(self, api_client, usuario_creado, url_login):
        """
        Verifica que si un usuario ya tiene un token asignado, el login
        devuelve el mismo token en lugar de fallar o crear uno nuevo duplicado.
        """
        # Creamos un token previo manualmente
        token_previo = Token.objects.create(user=usuario_creado)

        payload = {
            "username": "jugador_pro",
            "password": "password_seguro_123"
        }

        response = api_client.post(url_login, payload, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data["token"] == token_previo.key
        assert Token.objects.filter(user=usuario_creado).count() == 1