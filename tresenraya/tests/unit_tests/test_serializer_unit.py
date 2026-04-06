import pytest
from unittest.mock import MagicMock, patch
from django.contrib.auth.models import User
from tresenraya.serializers import MovimientoVisualizacionSerializer, PartidaListadoSerializer, RegistroSerializer

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

class TestMovimientoVisualizacionSerializerUnitario:
    """Tests unitarios puros para el serializador de visualización de movimientos."""

    @pytest.fixture
    def movimiento_mock(self):
        """Crea un mock de una instancia de Movimiento con sus relaciones."""
        movimiento = MagicMock()
        movimiento.instante = "2024-01-01T12:00:00Z"
        
        # Mock de ReadOnlyFields (source)
        movimiento.jugador.username = "jugador1"
        movimiento.celda.valor = "X"
        movimiento.coordenadas = "(1, 2)"
        
        # Necesario para la lógica de get_tablero
        movimiento.partida = MagicMock()
        
        return movimiento

    def test_serializer_retorna_campos_esperados(self, movimiento_mock):
        """Verifica que el serializer devuelva los campos básicos correctamente."""
        
        # Mockeamos el método get_tablero para que no ejecute lógica de DB en este test
        with patch.object(MovimientoVisualizacionSerializer, 'get_tablero', return_value=[[""]*3]*3):
            serializer = MovimientoVisualizacionSerializer(instance=movimiento_mock)
            data = serializer.data

            assert data['instante'] == "2024-01-01T12:00:00Z"
            assert data['jugador_nombre'] == "jugador1"
            assert data['simbolo'] == "X"
            assert data['posicion'] == "(1, 2)"
            assert 'tablero' in data

    def test_get_tablero_recreacion_logica(self, movimiento_mock):
        """Verifica la lógica de reconstrucción de la matriz en get_tablero."""
        
        # 1. Preparamos movimientos antiguos simulados
        mov1 = MagicMock()
        mov1.celda.fila = 0
        mov1.celda.columna = 0
        mov1.celda.valor = "X"

        mov2 = MagicMock()
        mov2.celda.fila = 1
        mov2.celda.columna = 1
        mov2.celda.valor = "O"

        # 2. Mockeamos el QuerySet y el método filter de Movimiento
        mock_queryset = [mov1, mov2]
        
        # Usamos patch para interceptar la llamada a la base de datos
        with patch('tresenraya.models.Movimiento.objects.filter') as mock_filter:
            # Configuramos el encadenamiento de filter().select_related()
            mock_filter.return_value.select_related.return_value = mock_queryset
            
            serializer = MovimientoVisualizacionSerializer()
            matriz_result = serializer.get_tablero(movimiento_mock)

            # 3. Verificaciones de la matriz
            # Celda (0,0) debe ser X
            assert matriz_result[0][0] == "X"
            # Celda (1,1) debe ser O
            assert matriz_result[1][1] == "O"
            # Celda (2,2) debe estar vacía
            assert matriz_result[2][2] == ""
            
            # 4. Verificar que se llamó al ORM con los filtros correctos
            mock_filter.assert_called_once_with(
                partida=movimiento_mock.partida,
                instante__lte=movimiento_mock.instante
            )

    def test_get_tablero_matriz_vacia(self, movimiento_mock):
        """Verifica que devuelve una matriz vacía si no hay movimientos previos."""
        
        with patch('tresenraya.models.Movimiento.objects.filter') as mock_filter:
            mock_filter.return_value.select_related.return_value = []
            
            serializer = MovimientoVisualizacionSerializer()
            matriz = serializer.get_tablero(movimiento_mock)
            
            expected_empty = [["", "", ""], ["", "", ""], ["", "", ""]]
            assert matriz == expected_empty