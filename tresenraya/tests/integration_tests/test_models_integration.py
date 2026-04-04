import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from tresenraya.models import Partida, Jugadores, Tablero, Celda, Movimiento

@pytest.mark.django_db
class TestIntegracionModel:

    @pytest.fixture
    def setup_partida(self):
        """Configura el escenario inicial con usuarios, partida, jugadores y tablero 3x3."""

        u1 = User.objects.create_user(username="jugador1")
        u2 = User.objects.create_user(username="jugador2")
        
        partida = Partida.objects.create(turno_actual=u1, ganador=u2)
        
        Jugadores.objects.create(usuario=u1, partida=partida, simbolo="X")
        Jugadores.objects.create(usuario=u2, partida=partida, simbolo="O")
        
        tablero = Tablero.objects.create(partida=partida)
        celdas = []
        for f in range(3):
            for c in range(3):
                celdas.append(Celda.objects.create(tablero=tablero, fila=f, columna=c))
        
        return partida, u1, u2, celdas

    def test_creacion_partida_y_jugadores(self, setup_partida):
        """Verifica la correcta instanciación de la partida y sus relaciones iniciales."""

        partida, u1, u2, _ = setup_partida
        assert Partida.objects.count() == 1
        assert Jugadores.objects.filter(partida=partida).count() == 2
        assert partida.tablero is not None

    def test_unique_together_simbolo_partida(self, setup_partida):
        """Valida que no se puedan duplicar símbolos en una misma partida."""

        partida, u1, _, _ = setup_partida
        with pytest.raises(IntegrityError):
            Jugadores.objects.create(usuario=u1, partida=partida, simbolo="X")

    def test_movimiento_valido_y_matriz_tablero(self, setup_partida):
        """Comprueba que un movimiento registra correctamente el símbolo en la matriz del tablero."""

        partida, u1, _, celdas = setup_partida
        celda_centro = celdas[4]
        
        mov = Movimiento(partida=partida, jugador=u1, celda=celda_centro)
        mov.full_clean()
        mov.save()

        matriz = partida.matriz_tablero
        assert matriz[1][1] == "X"

    def test_error_turno_incorrecto(self, setup_partida):
        """Asegura que un jugador no pueda mover si no es su turno actual."""

        partida, _, u2, celdas = setup_partida
        mov = Movimiento(partida=partida, jugador=u2, celda=celdas[0])
        
        with pytest.raises(ValidationError, match="No es el turno de este jugador"):
            mov.full_clean()

    def test_error_celda_otra_partida(self, setup_partida):
        """Valida que no se permitan movimientos en celdas que pertenecen a otros tableros."""

        partida1, u1, _, _ = setup_partida
        
        u3 = User.objects.create_user(username="u3")
        partida2 = Partida.objects.create(turno_actual=u3, ganador=u3)
        tablero2 = Tablero.objects.create(partida=partida2)
        celda_ajena = Celda.objects.create(tablero=tablero2, fila=0, columna=0)

        mov = Movimiento(partida=partida1, jugador=u1, celda=celda_ajena)
        
        with pytest.raises(ValidationError, match="Esta celda no pertenece a esta partida"):
            mov.full_clean()

    def test_unique_together_celda_coordenadas(self, setup_partida):
        """Verifica la restricción de unicidad de coordenadas (fila, columna) por tablero."""
        
        _, _, _, celdas = setup_partida
        tablero = celdas[0].tablero
        with pytest.raises(IntegrityError):
            Celda.objects.create(tablero=tablero, fila=0, columna=0)