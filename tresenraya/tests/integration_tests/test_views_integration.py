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