import pytest
from unittest.mock import MagicMock, patch
from django.contrib.auth.models import User
from tresenraya.serializers import RegistroSerializer

@pytest.mark.django_db
class TestRegistroSerializerUnitario:
    """
    Conjunto de pruebas para validar la lógica del RegistroSerializer
    sin interactuar con la base de datos de Django.
    """

    def test_serializer_con_datos_validos(self):
        """
        Verifica que el serializer es válido cuando se le proporcionan
        todos los campos requeridos correctamente.
        """

        datos_entrada = {
            "username": "usuario_test",
            "password": "password_seguro_123",
            "email": "test@example.com"
        }
        serializer = RegistroSerializer(data=datos_entrada)
        assert serializer.is_valid() is True

        assert serializer.is_valid() is True

    def test_serializer_password_es_write_only(self):
        """
        Valida que el campo 'password' tiene la configuración 'write_only',
        asegurando que no se incluya en la representación de salida (JSON).
        """

        mock_user = MagicMock(spec=User)
        mock_user.username = "usuario_test"
        mock_user.email = "test@example.com"
        # La contraseña nunca debería serializarse en el dict de salida
        
        serializer = RegistroSerializer(instance=mock_user)
        
        assert "password" not in serializer.data
        assert serializer.data["username"] == "usuario_test"

    def test_serializer_faltan_campos_requeridos(self):
        """
        Prueba que el serializer no sea válido si falta el campo 'username',
        devolviendo el error correspondiente.
        """

        datos_incompletos = {
            "password": "password123"
        }
        
        serializer = RegistroSerializer(data=datos_incompletos)
        
        assert serializer.is_valid() is False
        assert "username" in serializer.errors

    @patch('django.contrib.auth.models.User.objects.create_user')
    def test_metodo_create_usa_create_user(self, mock_create_user):
        """
        Verifica que el método create del serializer llama internamente a
        User.objects.create_user para garantizar el hash de la contraseña.
        """

        datos_validados = {
            "username": "new_user",
            "password": "secret_password",
            "email": "new@example.com"
        }
        serializer = RegistroSerializer()
        
        # Simulamos un usuario retornado por create_user
        mock_user = MagicMock(spec=User)
        mock_create_user.return_value = mock_user

        resultado = serializer.create(datos_validados)

        # Comprobamos que se llamó a create_user con los argumentos desempaquetados
        mock_create_user.assert_called_once_with(**datos_validados)
        assert resultado == mock_user