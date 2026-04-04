import pytest
from unittest.mock import MagicMock, patch
from django.contrib.auth.models import User
from tresenraya.serializers import PartidaListadoSerializer, RegistroSerializer

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

class TestPartidaListadoSerializerUnitario:
    """Tests unitarios para el serializador de listado de partidas."""

    @pytest.fixture
    def partida_mock(self):
        """Crea un mock de una instancia de Partida con sus relaciones."""

        partida = MagicMock()
        partida.id = 1
        partida.finalizada = False
        partida.fecha_creacion = "2024-01-01T12:00:00Z"
        
        # Mock de campos ReadOnly (turno_actual y ganador)
        partida.turno_actual.username = "usuario1"
        partida.ganador.username = "usuario2"
        
        # Mock para el SerializerMethodField (get_jugadores)
        mock_jugadores_qs = MagicMock()
        mock_jugadores_qs.values_list.return_value = ["usuario1", "usuario2"]
        partida.jugador_set = mock_jugadores_qs
        
        return partida

    def test_serializer_retorna_campos_esperados(self, partida_mock):
        """Verifica que el serializer devuelva los datos en el formato correcto."""
        
        serializer = PartidaListadoSerializer(instance=partida_mock)
        data = serializer.data

        # Verificación de campos simples
        assert data['id'] == 1
        assert data['finalizada'] is False
        
        # Verificación de ReadOnlyFields (source)
        assert data['turno_actual_nombre'] == "usuario1"
        assert data['ganador_nombre'] == "usuario2"
        
        # Verificación del SerializerMethodField
        assert data['jugadores'] == ["usuario1", "usuario2"]
        # Validamos que se llamó correctamente a la query de Django
        partida_mock.jugador_set.values_list.assert_called_once_with(
            'usuario__username', flat=True
        )

    def test_serializer_con_ganador_nulo(self, partida_mock):
        """Verifica el comportamiento cuando no hay ganador (partida en curso)."""
        
        # Configuramos el mock para que el ganador sea None
        del partida_mock.ganador
        partida_mock.ganador = None
        
        serializer = PartidaListadoSerializer(instance=partida_mock)
        data = serializer.data
        
        # Comprobamos que no devuelve ganador_nombre
        assert 'ganador_nombre' not in data

    def test_get_jugadores_llamada_metodo(self, partida_mock):
        """Verifica específicamente la lógica interna del método get_jugadores."""
        
        serializer = PartidaListadoSerializer()
        resultado = serializer.get_jugadores(partida_mock)
        
        assert resultado == ["usuario1", "usuario2"]
        partida_mock.jugador_set.values_list.assert_called_with(
            'usuario__username', flat=True
        )