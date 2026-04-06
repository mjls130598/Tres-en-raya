import pytest
from django.contrib.auth.models import User
from tresenraya.models import Celda, Jugador, Movimiento, Partida, Tablero
from tresenraya.serializers import MovimientoVisualizacionSerializer, RegistroSerializer

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

@pytest.mark.django_db
class TestMovimientoVisualizacionIntegration:
    """Tests de integración para MovimientoVisualizacionSerializer."""

    @pytest.fixture
    def setup_partida_con_movimientos(self):
        """Setup: Crea una partida, un tablero y una secuencia de movimientos."""
        
        # 1. Crear Usuario y Partida
        usuario = User.objects.create_user(username="jugador1")
        partida = Partida.objects.create(turno_actual=usuario)
        
        # 2. Crear Jugador (necesario para la property matriz_tablero del modelo)
        Jugador.objects.create(usuario=usuario, partida=partida, simbolo="X")
        
        # 3. Crear Tablero (Esto crea automáticamente las 9 celdas vía save())
        tablero = Tablero.objects.create(partida=partida)
        
        # 4. RECUPERAR celdas existentes en lugar de crear nuevas
        celda_00 = Celda.objects.get(tablero=tablero, fila=0, columna=0)
        celda_00.valor = "X"
        celda_00.save()
        mov1 = Movimiento.objects.create(partida=partida, jugador=usuario, celda=celda_00)
        
        celda_11 = Celda.objects.get(tablero=tablero, fila=1, columna=1)
        celda_11.valor = "O"
        celda_11.save()
        mov2 = Movimiento.objects.create(partida=partida, jugador=usuario, celda=celda_11)
        
        return mov1, mov2

    def test_serializer_data_con_db(self, setup_partida_con_movimientos):
        """Verifica que el serializer extraiga correctamente datos de objetos reales."""
        mov1, mov2 = setup_partida_con_movimientos
        
        # Serializamos el segundo movimiento
        serializer = MovimientoVisualizacionSerializer(instance=mov2)
        data = serializer.data

        # Verificación de integración de campos relacionados
        assert data['jugador_nombre'] == "jugador1"
        assert data['simbolo'] == "O"
        assert data['posicion'] == [1, 1]
        
        # Verificación de que la fecha es un string (ISO format)
        assert isinstance(data['instante'], str)

    def test_get_tablero_recrea_estado_historico(self, setup_partida_con_movimientos):
        """
        Verifica que get_tablero devuelva el estado del tablero 
        en ese punto exacto del tiempo.
        """
        mov1, mov2 = setup_partida_con_movimientos
        
        # Caso 1: Tablero tras el primer movimiento
        serializer1 = MovimientoVisualizacionSerializer(instance=mov1)
        tablero1 = serializer1.data['tablero']
        assert tablero1[0][0] == "X"
        assert tablero1[1][1] == ""  # El segundo movimiento aún no existía

        # Caso 2: Tablero tras el segundo movimiento
        serializer2 = MovimientoVisualizacionSerializer(instance=mov2)
        tablero2 = serializer2.data['tablero']
        assert tablero2[0][0] == "X"
        assert tablero2[1][1] == "O"

    def test_aislamiento_entre_partidas(self):
        """Verifica que el tablero no incluya movimientos de otras partidas."""
        user = User.objects.create_user(username="tester_unique")
    
        # --- PARTIDA A ---
        p1 = Partida.objects.create()
        # Al crear el tablero, el método save() ya crea las 9 celdas automáticamente
        t1 = Tablero.objects.create(partida=p1)
        
        # Recuperamos la celda (0,0) que ya existe para t1 y le asignamos valor
        c1 = Celda.objects.get(tablero=t1, fila=0, columna=0)
        c1.valor = "X"
        c1.save()
        
        # Registramos el movimiento en la Partida A
        Movimiento.objects.create(partida=p1, jugador=user, celda=c1)

        # --- PARTIDA B ---
        p2 = Partida.objects.create()
        t2 = Tablero.objects.create(partida=p2)
        
        # Recuperamos la celda (0,0) del tablero t2 (es una instancia distinta a t1)
        c2 = Celda.objects.get(tablero=t2, fila=0, columna=0)
        c2.valor = "O"
        c2.save()
        
        # Registramos el movimiento en la Partida B
        mov_p2 = Movimiento.objects.create(partida=p2, jugador=user, celda=c2)

        # --- VERIFICACIÓN ---
        # Serializamos el movimiento de la Partida B
        serializer = MovimientoVisualizacionSerializer(instance=mov_p2)
        tablero_renderizado = serializer.data['tablero']
        
        # 1. El tablero debe mostrar el valor de la partida B en (0,0)
        assert tablero_renderizado[0][0] == "O"
        
        # 2. El tablero NO debe contener "X" porque pertenece a la Partida A
        for fila in tablero_renderizado:
            for celda_valor in fila:
                assert celda_valor != "X", f"Se encontró una 'X' de otra partida en el tablero: {tablero_renderizado}"