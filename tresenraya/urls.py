from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from .views import CrearPartidaView, RegistroView

urlpatterns = [
    path('api/signup/', RegistroView.as_view(), name='signup'),
    path('api/login/', obtain_auth_token, name='login'),
    path('api/nueva_partida/', CrearPartidaView.as_view(), name='nueva_partida')
]