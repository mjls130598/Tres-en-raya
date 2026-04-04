import pytest
from django.contrib.auth.models import User
from tresenraya.serializers import RegistroSerializer

@pytest.mark.django_db
class TestRegistroSerializerIntegracion:
    """
    Tests de integración para RegistroSerializer.
    Valida la interacción real con el modelo User y la base de datos.
    """

    def test_creacion_real_usuario_encriptado(self):
        """
        Verifica que el serializer crea un usuario real en la base de datos
        y que la contraseña se guarda encriptada (no en texto plano).
        """

        datos = {
            "username": "integracion_user",
            "password": "password123",
            "email": "int@example.com"
        }
        serializer = RegistroSerializer(data=datos)
        
        assert serializer.is_valid()
        user = serializer.save()

        # Verificamos persistencia
        assert User.objects.filter(username="integracion_user").exists()
        # Verificamos que la contraseña NO sea "password123" (está hasheada)
        assert user.password != "password123"
        assert user.check_password("password123") is True

    def test_error_unicidad_username(self):
        """
        Valida que el serializer falle si intenta registrar un username que ya existe.
        """

        User.objects.create_user(username="existente", password="old_password")
        
        datos_duplicados = {
            "username": "existente",
            "password": "new_password123",
            "email": "otro@example.com"
        }
        serializer = RegistroSerializer(data=datos_duplicados)
        
        assert serializer.is_valid() is False
        assert "username" in serializer.errors