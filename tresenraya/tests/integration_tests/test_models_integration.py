import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from tresenraya.models import Partida, Jugador, Tablero, Celda, Movimiento

@pytest.mark.django_db
class TestIntegracionModel:

    @pytest.fixture
    def setup_partida(self):
        """Configura el escenario inicial optimizado."""
        u1 = User.objects.create_user(username="jugador1")
        u2 = User.objects.create_user(username="jugador2")
        
        # Al crear la partida, asignamos turno al u1
        partida = Partida.objects.create(turno_actual=u1)
        
        # Creamos los jugadores vinculados
        j1 = Jugador.objects.create(usuario=u1, partida=partida, simbolo="X")
        j2 = Jugador.objects.create(usuario=u2, partida=partida, simbolo="O")
        
        # IMPORTANTE: El modelo Tablero ya crea las celdas en su save()
        tablero = Tablero.objects.create(partida=partida)
        
        return partida, u1, u2, tablero

    def test_creacion_partida_y_jugadores(self, setup_partida):
        """Verifica la correcta instanciación de la partida y sus relaciones iniciales."""

        partida, u1, u2, _ = setup_partida
        assert Partida.objects.count() == 1
        assert Jugador.objects.filter(partida=partida).count() == 2
        assert partida.tablero is not None

    def test_unique_together_simbolo_partida(self, setup_partida):
        """Valida que no se puedan duplicar símbolos en una misma partida."""

        partida, u1, _, _ = setup_partida
        with pytest.raises(IntegrityError):
            Jugador.objects.create(usuario=u1, partida=partida, simbolo="X")

    def test_movimiento_valido_y_matriz_tablero(self, setup_partida):
        """Comprueba que un movimiento registra correctamente el símbolo en la matriz."""
        partida, u1, _, tablero = setup_partida
        celda_centro = Celda.objects.get(tablero=tablero, fila=1, columna=1)
        
        mov = Movimiento(partida=partida, jugador=u1, celda=celda_centro)
        mov.full_clean()
        mov.save()

        matriz = partida.matriz_tablero
        assert matriz[1][1] == "X"
        assert matriz[0][0] == "" 

    def test_error_turno_incorrecto(self, setup_partida):
        """Asegura que un jugador no pueda mover si no es su turno actual."""
        partida, _, u2, tablero = setup_partida
        celda = Celda.objects.get(tablero=tablero, fila=0, columna=0)
        
        # El turno actual en el setup es u1, intentamos mover con u2
        mov = Movimiento(partida=partida, jugador=u2, celda=celda)
        
        with pytest.raises(ValidationError, match="No es el turno de este jugador"):
            mov.full_clean()

    def test_error_celda_otra_partida(self, setup_partida):
        """Valida que no se permitan movimientos en celdas de otros tableros."""
        partida1, u1, _, _ = setup_partida
        
        # Crear otra partida y su tablero
        u3 = User.objects.create_user(username="u3")
        partida2 = Partida.objects.create(turno_actual=u3)
        tablero2 = Tablero.objects.create(partida=partida2)
        celda_ajena = Celda.objects.filter(tablero=tablero2).first()

        # Intentar mover en partida 1 usando una celda de partida 2
        mov = Movimiento(partida=partida1, jugador=u1, celda=celda_ajena)
        
        with pytest.raises(ValidationError, match="Esta celda no pertenece a esta partida"):
            mov.full_clean()
        
        with pytest.raises(ValidationError, match="Esta celda no pertenece a esta partida"):
            mov.full_clean()
            
    def test_orden_movimientos_instante(self, setup_partida):
        """Verifica que los movimientos se recuperan en orden cronológico."""
        partida, u1, _, tablero = setup_partida
        c1 = Celda.objects.get(tablero=tablero, fila=0, columna=0)
        c2 = Celda.objects.get(tablero=tablero, fila=0, columna=1)
        
        Movimiento.objects.create(partida=partida, jugador=u1, celda=c1)
        # Cambiamos turno manualmente para el test
        partida.turno_actual = u1 
        Movimiento.objects.create(partida=partida, jugador=u1, celda=c2)
        
        movimientos = Movimiento.objects.filter(partida=partida)
        assert movimientos.count() == 2
        assert movimientos[0].celda == c1
        assert movimientos[1].celda == c2

    def test_cascada_eliminacion_partida(self, setup_partida):
        """Si se borra una partida, se deben borrar sus jugadores, tablero y celdas."""
        partida, _, _, _ = setup_partida
        partida_id = partida.id
        
        Partida.objects.filter(id=partida_id).delete()
        
        assert Jugador.objects.filter(partida_id=partida_id).count() == 0
        assert Tablero.objects.filter(partida_id=partida_id).count() == 0
        assert Celda.objects.count() == 0

    def test_celda_unica_por_movimiento(self, setup_partida):
        """Verifica que no se puede usar la misma celda dos veces (OneToOneField en Movimiento)."""
        partida, u1, _, tablero = setup_partida
        celda = Celda.objects.get(tablero=tablero, fila=0, columna=0)
        
        Movimiento.objects.create(partida=partida, jugador=u1, celda=celda)
        
        with pytest.raises(IntegrityError):
            # Intentar crear otro movimiento en la misma celda
            Movimiento.objects.create(partida=partida, jugador=u1, celda=celda)