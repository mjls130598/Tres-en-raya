import pytest
from django.urls import reverse, resolve
from rest_framework.authtoken.views import obtain_auth_token
from tresenraya.views import CrearPartidaView, ListarMovimientosView, ListarPartidasView, RankingView, RealizarMovimientoView, RegistroView, UltimoMovimientoView

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

    def test_jugada_url_resolves(self):
        """Verifica la ruta de listado de partidas."""

        url = reverse('jugada')
        resolver = resolve(url)
        assert resolver.func.view_class == RealizarMovimientoView
        assert resolver.view_name == 'jugada'

    def test_movimientos_url_resolves(self):
        """Verifica la ruta de listado de partidas."""

        partida_id = 1
        url = reverse('movimientos', kwargs={'partida_id': partida_id})
        resolver = resolve(url)
        assert resolver.func.view_class == ListarMovimientosView
        assert resolver.view_name == 'movimientos'
        assert 'partida_id' in resolver.kwargs
        assert resolver.kwargs['partida_id'] == partida_id

    def test_ultimo_movimiento_url_resolves(self):
        """Verifica la ruta de listado de partidas."""

        partida_id = 1
        url = reverse('ultimo_movimiento', kwargs={'partida_id': partida_id})
        resolver = resolve(url)
        assert resolver.func.view_class == UltimoMovimientoView
        assert resolver.view_name == 'ultimo_movimiento'
        assert 'partida_id' in resolver.kwargs
        assert resolver.kwargs['partida_id'] == partida_id

    def test_ranking_url_resolves(self):
        """Verifica la ruta de listado de partidas."""

        url = reverse('ranking')
        resolver = resolve(url)
        assert resolver.func.view_class == RankingView
        assert resolver.view_name == 'ranking'

    @pytest.mark.parametrize("url_name, kwargs", [
        ('signup', {}),
        ('login', {}),
        ('nueva_partida', {}),
        ('get_partidas', {}),
        ('jugada', {}),
        # Estas dos ahora reciben el ID que esperan:
        ('movimientos', {'partida_id': 1}),
        ('ultimo_movimiento', {'partida_id': 1}),
        ('ranking', {})
    ])
    def test_urls_names_exist(self, url_name, kwargs):
        """
        Verifica que las URLs existen y son reversibles, 
        manejando parámetros dinámicos cuando es necesario.
        """
        url = reverse(url_name, kwargs=kwargs)
        assert url is not None