from unittest.mock import MagicMock
import pytest
from django.core.exceptions import ValidationError
from tresenraya.models import Celda, Movimiento, Partida
from django.contrib.auth.models import User

class TestPartida:
    """Tests unitarios del método 'matriz_tablero'"""

    def test_matriz_tablero_reconstruccion_correcta(self):
        """Verifica que el tablero 3x3 se reconstruya fielmente basándose en los movimientos y símbolos de los jugadores."""

        # 1. Mock de la instancia de Partida
        partida = MagicMock()
        
        # 2. Mock de los Jugadores y sus símbolos
        jugador_x = MagicMock(simbolo="X")
        jugador_o = MagicMock(simbolo="O")

        # El código busca: jugador_set.get(usuario=mov.jugador)
        # Debemos manejar el argumento nominal 'usuario'
        def side_effect_jugadores(**kwargs):
            usuario = kwargs.get('usuario')
            if usuario == "user_x":
                return jugador_x
            return jugador_o

        partida.jugador_set.get.side_effect = side_effect_jugadores

        # 3. Mock de los Movimientos
        # Cada movimiento debe tener una celda con fila/columna y un usuario asociado
        mov1 = MagicMock(celda=MagicMock(fila=0, columna=0), jugador="user_x")
        mov2 = MagicMock(celda=MagicMock(fila=1, columna=1), jugador="user_o")
        mov3 = MagicMock(celda=MagicMock(fila=2, columna=2), jugador="user_x")

        # Mockeamos el encadenamiento: movimiento_set.select_related(...).all()
        movimientos_mock = [mov1, mov2, mov3]
        partida.movimiento_set.select_related.return_value.all.return_value = movimientos_mock

        # 4. Ejecución
        # Accedemos a la property. Al ser un mock, usamos fget para invocar la lógica real
        resultado = Partida.matriz_tablero.fget(partida)

        # 5. Verificación
        tablero_esperado = [
            ["X", "", ""],
            ["", "O", ""],
            ["", "", "X"]
        ]
        
        assert resultado == tablero_esperado
        assert len(resultado) == 3
        assert resultado[0][0] == "X"
        assert resultado[1][1] == "O"

    def test_matriz_tablero_vacia(self):
        """Verifica que si no existen movimientos grabados, se devuelva una matriz de 3x3 rellena de strings vacíos."""

        partida = MagicMock()
        
        # Simulamos que no hay movimientos (lista vacía)
        partida.movimiento_set.select_related.return_value.all.return_value = []
        
        # Ejecución
        resultado = Partida.matriz_tablero.fget(partida)
        
        # Verificación
        tablero_vacio = [["", "", ""], ["", "", ""], ["", "", ""]]
        assert resultado == tablero_vacio
        # Aseguramos que todas las celdas sean strings vacíos
        assert all(celda == "" for fila in resultado for celda in fila)

class TestMovimiento:
    """Tests unitarios del método 'clean'"""

    @pytest.fixture
    def mov_mock(self):
        # Creamos un mock que contendrá los atributos necesarios
        mov = MagicMock(spec=Movimiento)
        # Importante: Queremos ejecutar el método 'clean' REAL de la clase
        # pero sobre nuestro objeto mockeado.
        mov.clean = lambda: Movimiento.clean(mov)
        return mov

    def test_clean_celda_no_pertenece_a_partida(self, mov_mock):
        """Prueba que el usuario que no pertenece a la partida no puede mover."""

        # Configuramos las relaciones en el mock (aquí no hay validación de tipo)
        mov_mock.partida = MagicMock()
        mov_mock.jugador = MagicMock()
        
        # Celda -> Tablero -> Partida (distinta a mov_mock.partida)
        mov_mock.celda = MagicMock()
        mov_mock.celda.tablero.partida = MagicMock() 

        with pytest.raises(ValidationError) as excinfo:
            mov_mock.clean()
        
        assert "Esta celda no pertenece a esta partida" in str(excinfo.value)

    def test_clean_no_es_el_turno_del_jugador(self, mov_mock):
        """Prueba que el usuario no puede mover si no es su turno."""

        # Seteamos el mismo objeto partida para pasar el primer check
        mock_partida = MagicMock()
        mov_mock.partida = mock_partida
        mov_mock.celda.tablero.partida = mock_partida
        
        # Turno de alguien que no es el que mueve
        mov_mock.partida.turno_actual = "Jugador A"
        mov_mock.jugador = "Jugador B"

        with pytest.raises(ValidationError) as excinfo:
            mov_mock.clean()
        
        assert "No es el turno de este jugador" in str(excinfo.value)

    def test_clean_exitoso(self, mov_mock):
        """Prueba que el usuario puede mover correctamente."""

        # Configuración coherente
        mock_partida = MagicMock()
        mock_jugador = MagicMock()
        
        mov_mock.partida = mock_partida
        mov_mock.celda.tablero.partida = mock_partida
        mov_mock.partida.turno_actual = mock_jugador
        mov_mock.jugador = mock_jugador

        # No debe lanzar excepción
        mov_mock.clean()
