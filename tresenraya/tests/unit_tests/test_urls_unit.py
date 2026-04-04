import pytest
from django.urls import reverse, resolve
from rest_framework.authtoken.views import obtain_auth_token
from tresenraya.views import CrearPartidaView, ListarPartidasView, RegistroView

class TestUrlsUnitario:
    """
    Tests de resolución de URLs. 
    Verifican que el nombre de la URL y la ruta física apunten a la vista correcta.
    """

    def test_signup_url_resolves(self):
        """Verifica la ruta de registro de usuarios."""

        url = reverse('signup')
        # Comprobamos que '/api/signup/' resuelve a RegistroView
        assert resolve(url).func.view_class == RegistroView
        assert url == '/api/signup/'

    def test_login_url_resolves(self):
        """Verifica la ruta de obtención de token (login)."""
        
        url = reverse('login')
        # obtain_auth_token es una función de vista, no una clase
        assert resolve(url).func == obtain_auth_token
        assert url == '/api/login/'

    def test_nueva_partida_url_resolves(self):
        """Verifica la ruta de creación de partidas."""

        url = reverse('nueva_partida')
        resolver = resolve(url)
        assert resolver.func.view_class == CrearPartidaView
        assert resolver.view_name == 'nueva_partida'

    def test_get_partidas_url_resolves(self):
        """Verifica la ruta de listado de partidas."""

        url = reverse('get_partidas')
        resolver = resolve(url)
        assert resolver.func.view_class == ListarPartidasView
        assert resolver.view_name == 'get_partidas'

    @pytest.mark.parametrize("url_name", ['signup', 'login', 'nueva_partida', 'get_partidas'])
    def test_urls_names_exist(self, url_name):
        """
        Test de regresión rápido para asegurar que todos los nombres 
        definidos en urlpatterns existen y son reversibles.
        """

        url = reverse(url_name)
        assert url is not None