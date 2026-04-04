import pytest
from django.urls import reverse
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

from tresenraya.models import Celda, Jugador, Partida, Tablero

@pytest.mark.django_db
class TestRegistroViewIntegracion:
    """
    Tests de integración para RegistroView.
    Simula peticiones HTTP reales al endpoint de registro.
    """

    @pytest.fixture
    def url_registro(self):
        return reverse('signup') 

    def test_flujo_completo_registro_exitoso(self, api_client, url_registro):
        """
        Verifica que una petición POST válida crea el usuario, el token 
        y devuelve el JSON esperado con status 201.
        """

        payload = {
            "username": "nuevo_jugador",
            "password": "password_seguro",
            "email": "jugador@test.com"
        }

        response = api_client.post(url_registro, payload, format='json')

        # 1. Verificar respuesta HTTP
        assert response.status_code == status.HTTP_201_CREATED
        assert "token" in response.data
        assert response.data["username"] == "nuevo_jugador"

        # 2. Verificar Base de Datos
        user = User.objects.get(username="nuevo_jugador")
        assert Token.objects.filter(user=user).exists()
        assert Token.objects.get(user=user).key == response.data["token"]

    def test_registro_fallido_datos_invalidos(self, api_client, url_registro):
        """
        Verifica que el endpoint rechaza peticiones con datos incompletos
        y no crea usuarios ni tokens accidentalmente.
        """

        payload_incompleto = {"username": "solo_nombre"} # Falta password

        response = api_client.post(url_registro, payload_incompleto, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert User.objects.count() == 0
        assert Token.objects.count() == 0

@pytest.mark.django_db
class TestLoginIntegracion:
    """
    Tests de integración para el flujo de inicio de sesión y 
    obtención de tokens de autenticación.
    """

    @pytest.fixture
    def usuario_creado(self):
        """Crea un usuario real en la base de datos para las pruebas."""
        return User.objects.create_user(
            username="jugador_pro", 
            password="password_seguro_123",
            email="pro@test.com"
        )

    @pytest.fixture
    def url_login(self):
        """
        Obtiene la URL del endpoint de login. 
        Asegúrate de que en urls.py tengas: path('login/', ..., name='login')
        """

        return reverse('login')

    def test_login_exitoso_genera_token(self, api_client, usuario_creado, url_login):
        """
        Verifica que un usuario con credenciales correctas recibe un token
        y un código de estado 200.
        """
        
        payload = {
            "username": "jugador_pro",
            "password": "password_seguro_123"
        }

        response = api_client.post(url_login, payload, format='json')

        # Comprobamos respuesta HTTP
        assert response.status_code == status.HTTP_200_OK
        assert "token" in response.data
        
        # Comprobamos persistencia del Token en la base de datos
        token_db = Token.objects.get(user=usuario_creado)
        assert response.data["token"] == token_db.key

    def test_login_fallido_contrasena_incorrecta(self, api_client, usuario_creado, url_login):
        """
        Verifica que el sistema rechaza el acceso si la contraseña no coincide,
        devolviendo 400 o 401 según tu configuración.
        """

        payload = {
            "username": "jugador_pro",
            "password": "clave_erronea"
        }

        response = api_client.post(url_login, payload, format='json')

        # DRF suele devolver 400 Bad Request o 401 Unauthorized para login fallido
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED]
        assert "token" not in response.data

    def test_login_usuario_inexistente(self, api_client, url_login):
        """
        Verifica que el sistema no genera tokens para usuarios que no
        están registrados en la base de datos.
        """

        payload = {
            "username": "fantasma",
            "password": "password123"
        }

        response = api_client.post(url_login, payload, format='json')

        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED]
        assert Token.objects.count() == 0

    def test_reutilizacion_de_token_existente(self, api_client, usuario_creado, url_login):
        """
        Verifica que si un usuario ya tiene un token asignado, el login
        devuelve el mismo token en lugar de fallar o crear uno nuevo duplicado.
        """
        
        # Creamos un token previo manualmente
        token_previo = Token.objects.create(user=usuario_creado)

        payload = {
            "username": "jugador_pro",
            "password": "password_seguro_123"
        }

        response = api_client.post(url_login, payload, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data["token"] == token_previo.key
        assert Token.objects.filter(user=usuario_creado).count() == 1

@pytest.mark.django_db
class TestCrearPartidaIntegracion:
    """Tests de flujo completo con persistencia en BBDD."""

    @pytest.fixture
    def setup_usuarios(self):
        user1 = User.objects.create_user(username="user1", password="pass")
        user2 = User.objects.create_user(username="user2", password="pass")
        return user1, user2

    def test_creacion_partida_completa_exitosa(self, api_client, setup_usuarios):
        """
        Verifica que se crean correctamente todos los objetos relacionados:
        1 Partida, 1 Tablero, 2 Jugadores y 9 Celdas.
        """
        user1, user2 = setup_usuarios
        api_client.force_authenticate(user=user1)
        url = reverse('nueva_partida') # Ajusta al nombre en tu urls.py

        payload = {"oponente": "user2"}
        response = api_client.post(url, payload, format='json')

        # 1. Verificar Status 201
        assert response.status_code == status.HTTP_201_CREATED
        partida_id = response.data['partida_id']

        # 2. Verificar Partida y Tablero
        partida = Partida.objects.get(id=partida_id)
        assert Tablero.objects.filter(partida=partida).exists()

        # 3. Verificar Jugadores (X y O)
        jugadores = Jugador.objects.filter(partida=partida)
        assert jugadores.count() == 2
        simbolos = [j.simbolo for j in jugadores]
        assert "X" in simbolos
        assert "O" in simbolos

        # 4. Verificar Celdas (3x3 = 9)
        tablero = Tablero.objects.get(partida=partida)
        assert Celda.objects.filter(tablero=tablero).count() == 9

        # 5. Verificar Turno Inicial
        assert partida.turno_actual in [user1, user2]
        assert response.data['turno_actual'] == partida.turno_actual.username

    def test_creacion_partida_asigna_simbolos_correctos(self, api_client, setup_usuarios):
        """Verifica que los usuarios en la respuesta coinciden con los creados."""
        user1, user2 = setup_usuarios
        api_client.force_authenticate(user=user1)
        
        response = api_client.post(reverse('nueva_partida'), {"oponente": "user2"})
        
        usernames_res = [response.data['jugador_x'], response.data['jugador_o']]
        assert "user1" in usernames_res
        assert "user2" in usernames_res

@pytest.mark.django_db
class TestListarPartidasIntegracion:
    """Tests para asegurar que el filtrado en base de datos es preciso."""

    @pytest.fixture
    def setup_datos(self):
        # Usuarios
        me = User.objects.create_user(username="me", password="123")
        friend = User.objects.create_user(username="friend", password="123")
        stranger = User.objects.create_user(username="stranger", password="123")

        # Partida 1: Mía contra Friend (Finalizada)
        p1 = Partida.objects.create(finalizada=True)
        Jugador.objects.create(usuario=me, partida=p1, simbolo="X")
        Jugador.objects.create(usuario=friend, partida=p1, simbolo="O")

        # Partida 2: Mía contra Stranger (En curso)
        p2 = Partida.objects.create(finalizada=False)
        Jugador.objects.create(usuario=me, partida=p2, simbolo="X")
        Jugador.objects.create(usuario=stranger, partida=p2, simbolo="O")

        # Partida 3: De otros (No debo verla)
        p3 = Partida.objects.create(finalizada=True)
        Jugador.objects.create(usuario=friend, partida=p3, simbolo="X")
        Jugador.objects.create(usuario=stranger, partida=p3, simbolo="O")

        return me, friend, stranger

    def test_listar_solo_mis_partidas(self, api_client, setup_datos):
        """Verifica que el usuario logueado no vea partidas de terceros."""

        me, _, _ = setup_datos
        api_client.force_authenticate(user=me)
        
        response = api_client.get(reverse('get_partidas'))
        
        assert response.status_code == status.HTTP_200_OK
        # Debo ver 2 partidas (p1 y p2), no la p3.
        assert len(response.data) == 2

    def test_filtrar_por_finalizada(self, api_client, setup_datos):
        """Verifica el filtro ?finalizada=true."""

        me, _, _ = setup_datos
        api_client.force_authenticate(user=me)
        
        response = api_client.get(reverse('get_partidas'), {'finalizada': 'true'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        # La partida devuelta debe ser la p1 (finalizada)

    def test_filtrar_por_oponente(self, api_client, setup_datos):
        """Verifica el filtro ?oponente=friend."""

        me, friend, _ = setup_datos
        api_client.force_authenticate(user=me)
        
        response = api_client.get(reverse('get_partidas'), {'oponente': 'friend'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        # Solo debe aparecer la partida donde participa 'friend'