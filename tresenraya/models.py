from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# Entidad "PARTIDA"
class Partida(models.Model):
    """Representa la sesión de juego y sus metadatos."""

    # Relaciones con USER
    turno_actual = models.ForeignKey(
        User,
        related_name="turno_actual",
        on_delete=models.SET_NULL,
        null=True,
        blank=True)
    ganador = models.ForeignKey(
        User,
        related_name="ganador",
        on_delete=models.SET_NULL,
        null=True,
        blank=True)

    finalizada = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    @property
    def matriz_tablero(self):
        """Reconstruye el estado del tablero (3x3) basado en los movimientos."""
        
        tablero = [["" for _ in range(3)] for _ in range(3)]
        movimientos = self.movimiento_set.select_related('celda', 'jugador').all()

        for mov in movimientos:
            jugador = self.jugador_set.get(usuario=mov.jugador)
            tablero[mov.celda.fila][mov.celda.columna] = jugador.simbolo

        return tablero


# Relación USER - PARTIDA: "JUGADOR"
class Jugador(models.Model):
    """Vincula usuarios a una partida con un rol específico (X u O)."""

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE)
    simbolo = models.CharField(max_length=1) # 'X' ó 'O'

    class Meta:
        unique_together = ('partida', 'simbolo') # Para que no haya en una misma partida el mismo tipo de jugador

# Entidad "TABLERO"
class Tablero(models.Model):
    """El contenedor físico de la partida."""

    partida = models.OneToOneField(Partida, on_delete=models.CASCADE, related_name="tablero")

    def save(self, *args, **kwargs):
        """Creación de todas las celdas del tablero"""

        es_nuevo = self.pk is None
        super().save(*args, **kwargs)

        if es_nuevo:
            # Creación de las nueve celdas
            celdas_a_crear = [
                Celda(tablero=self, fila=f, columna=c)
                for f in range(3)
                for c in range(3)
            ]
            Celda.objects.bulk_create(celdas_a_crear)

# Entidad "CELDA"
class Celda(models.Model):
    """Coordenadas únicas dentro de un tablero."""

    tablero = models.ForeignKey(Tablero, on_delete=models.CASCADE)
    fila = models.IntegerField()
    columna = models.IntegerField()
    valor = models.CharField(max_length=1, default= '', blank=True)

    class Meta:
        unique_together = ('tablero', 'fila', 'columna') # Para que cada partida sea única

# Entidad "MOVIMIENTO"
class Movimiento(models.Model):
    """El log de los eventos"""
    
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE)
    jugador = models.ForeignKey(User, on_delete=models.CASCADE)
    celda = models.OneToOneField(Celda, on_delete=models.CASCADE)
    instante = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['instante']

    def clean(self):
        # 1. Validar que el tablero pertenece a la partida
        if self.celda.tablero.partida != self.partida:
            raise ValidationError("Esta celda no pertenece a esta partida.")
        
        # 2. Validar que es el turno del jugador
        if self.partida.turno_actual != self.jugador:
            raise ValidationError("No es el turno de este jugador")
        
    def coordenadas(self):
        return f"({self.celda.fila}, {self.celda.columna})" 