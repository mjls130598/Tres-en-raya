from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from .views import CrearPartidaView, ListarMovimientosView, ListarPartidasView, RealizarMovimientoView, RegistroView, UltimoMovimientoView

urlpatterns = [
    path('api/signup/', RegistroView.as_view(), name='signup'),
    path('api/login/', obtain_auth_token, name='login'),
    path('api/nueva_partida/', CrearPartidaView.as_view(), name='nueva_partida'),
    path('api/partidas/', ListarPartidasView.as_view(), name='get_partidas'),
    path('api/jugada/', RealizarMovimientoView.as_view(), name='jugada'),
    path('api/partidas/<int:partida_id>/movimientos/', ListarMovimientosView.as_view(), name='movimientos'),
    path('api/partidas/<int:partida_id>/ultimo_movimiento/', UltimoMovimientoView.as_view(), name='ultimo_movimiento'),
]