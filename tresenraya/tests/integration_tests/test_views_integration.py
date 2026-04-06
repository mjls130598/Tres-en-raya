import pytest
from django.urls import reverse
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

from tresenraya.models import Celda, Jugador, Movimiento, Partida, Tablero

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

@pytest.mark.django_db
class TestRealizarMovimientoView:
    """
        Tests para asegurar que se pueden realizar movimientos, 
        indicar el ganador de la partida o si ha habido empate
    """

    @pytest.fixture
    def setup_juego(self, api_client):
        """Configura el entorno de prueba con usuarios, partida, tablero y el cliente API."""
        u1 = User.objects.create_user(username="jugador1", password="pass123")
        u2 = User.objects.create_user(username="jugador2", password="pass123")
        
        partida = Partida.objects.create(turno_actual=u1)
        Jugador.objects.create(usuario=u1, partida=partida, simbolo="X")
        Jugador.objects.create(usuario=u2, partida=partida, simbolo="O")
        Tablero.objects.create(partida=partida)
        
        url = reverse('jugada')
        
        return api_client, partida, u1, u2, url

    # --- TESTS DE VALIDACIÓN ---

    def test_error_partida_no_existe(self, setup_juego):
        """Prueba que la API devuelva 404 si el ID de la partida no se encuentra en la base de datos."""

        client, _, u1, _, url = setup_juego
        client.force_authenticate(user=u1)
        
        response = client.post(url, {'partida_id': 999, 'fila': 0, 'columna': 0})
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['Error'] == "La partida dada no existe"

    def test_error_no_es_tu_turno(self, setup_juego):
        """Verifica que un jugador no pueda realizar un movimiento si el turno_actual de la partida pertenece al contrincante."""

        client, partida, _, u2, url = setup_juego
        client.force_authenticate(user=u2) # El turno inicial es de u1
        
        data = {'partida_id': partida.id, 'fila': 0, 'columna': 0}
        response = client.post(url, data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['Error'] == "No es tu turno"

    def test_error_casilla_ya_ocupada(self, setup_juego):
        """Valida que no se pueda marcar una celda que ya tiene un movimiento registrado previamente."""

        client, partida, u1, _, url = setup_juego
        client.force_authenticate(user=u1)
        
        celda = Celda.objects.get(tablero=partida.tablero, fila=0, columna=0)
        Movimiento.objects.create(partida=partida, jugador=u1, celda=celda)
        
        response = client.post(url, {'partida_id': partida.id, 'fila': 0, 'columna': 0})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['Error'] == "Esa casilla ya está ocupada"

    # --- TESTS DE LÓGICA DE JUEGO ---

    def test_movimiento_exitoso_y_cambio_turno(self, setup_juego):
        """Comprueba que tras un movimiento válido se crea el registro de Movimiento y el turno de la partida rota al siguiente jugador."""

        client, partida, u1, u2, url = setup_juego
        client.force_authenticate(user=u1)
        
        data = {'partida_id': partida.id, 'fila': 1, 'columna': 1}
        response = client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['estado'] == "jugando"
        
        partida.refresh_from_db()
        assert partida.turno_actual == u2
        assert Movimiento.objects.filter(partida=partida, jugador=u1).exists()

    def test_victoria_diagonal(self, setup_juego):
        """Verifica que el sistema detecta una línea diagonal completa, marca la partida como finalizada y asigna correctamente al ganador."""

        client, partida, u1, _, url = setup_juego
        tablero = partida.tablero
        
        # Preparamos 2 marcas en la diagonal principal para u1 (X)
        Movimiento.objects.create(partida=partida, jugador=u1, 
                                 celda=Celda.objects.get(tablero=tablero, fila=0, columna=0))
        Movimiento.objects.create(partida=partida, jugador=u1, 
                                 celda=Celda.objects.get(tablero=tablero, fila=1, columna=1))
        
        client.force_authenticate(user=u1)
        # Tercer movimiento para completar la diagonal
        response = client.post(url, {'partida_id': partida.id, 'fila': 2, 'columna': 2})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['estado'] == "victoria"
        
        partida.refresh_from_db()
        assert partida.finalizada is True
        assert partida.ganador == u1

    def test_error_coordenadas_fuera_rango(self, setup_juego):
        """Asegura que el sistema rechace movimientos con filas o columnas menores a 0 o mayores a 2."""

        client, partida, u1, _, url = setup_juego
        client.force_authenticate(user=u1)
        
        response = client.post(url, {'partida_id': partida.id, 'fila': 3, 'columna': 0})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['Error'] == "Coordenadas fuera del tablero"


@pytest.mark.django_db
class TestListarMovimientosIntegration:
    """Test para asegurar que se devuelve todos los movimientos de una partida"""

    @pytest.fixture
    def setup_datos(self):
        """Crea una partida con jugadores y movimientos reales."""

        # 1. Usuarios
        u1 = User.objects.create_user(username="jugador1", password="pass123")
        u2 = User.objects.create_user(username="jugador2", password="pass456")
        u_extra = User.objects.create_user(username="fisgon", password="pass789")
        
        # 2. Partida y Tablero (Tablero crea las celdas automáticamente)
        partida = Partida.objects.create(turno_actual=u1)
        tablero = Tablero.objects.create(partida=partida)
        
        # 3. Registrar a los jugadores en la partida
        Jugador.objects.create(usuario=u1, partida=partida, simbolo="X")
        Jugador.objects.create(usuario=u2, partida=partida, simbolo="O")
        
        # 4. Crear un movimiento real
        # Recuperamos la celda (0,0) creada por el save() del tablero
        celda = Celda.objects.get(tablero=tablero, fila=0, columna=0)
        celda.valor = "X"
        celda.save()
        
        Movimiento.objects.create(
            partida=partida, 
            jugador=u1, 
            celda=celda
        )
        
        return {
            "partida": partida,
            "jugador1": u1,
            "jugador2": u2,
            "fisgon": u_extra
        }

    def test_get_movimientos_exito(self, api_client, setup_datos):
        """Verifica que un jugador de la partida puede ver los movimientos."""

        partida = setup_datos["partida"]
        user = setup_datos["jugador1"]
        
        api_client.force_authenticate(user=user)
        url = reverse('movimientos', kwargs={'partida_id': partida.id})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["estado"] == "jugando"
        assert len(response.data["movimientos"]) == 1
        assert response.data["movimientos"][0]["simbolo"] == "X"
        assert response.data["movimientos"][0]["posicion"] == [0, 0]

    def test_get_movimientos_error_403_ajeno(self, api_client, setup_datos):
        """Un usuario que no está en la partida no puede ver los movimientos."""

        partida = setup_datos["partida"]
        user_ajeno = setup_datos["fisgon"]
        
        api_client.force_authenticate(user=user_ajeno)
        url = reverse('movimientos', kwargs={'partida_id': partida.id})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["Error"] == "No puedes ver los movimientos de esa partida"

    def test_get_movimientos_error_404_inexistente(self, api_client, setup_datos):
        """Error si la partida_id no existe en la DB."""

        api_client.force_authenticate(user=setup_datos["jugador1"])
        url = reverse('movimientos', kwargs={'partida_id': 9999})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_estado_partida_finalizada(self, api_client, setup_datos):
        """Verifica que el estado cambia a 'ganada' si la partida termina."""

        partida = setup_datos["partida"]
        user = setup_datos["jugador1"]
        
        # Simulamos fin de partida
        partida.finalizada = True
        partida.ganador = user
        partida.save()
        
        api_client.force_authenticate(user=user)
        url = reverse('movimientos', kwargs={'partida_id': partida.id})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["estado"] == "ganada"

@pytest.mark.django_db
class TestUltimoMovimientoIntegracion:
    """Tests para asegurar que la recuperación del último movimiento en DB es precisa."""

    @pytest.fixture
    def setup_datos(self):
        # 1. Usuarios
        me = User.objects.create_user(username="me", password="123")
        friend = User.objects.create_user(username="friend", password="123")
        stranger = User.objects.create_user(username="stranger", password="123")

        # 2. Partida A (Con movimientos)
        p_a = Partida.objects.create(turno_actual=me)
        t_a = Tablero.objects.create(partida=p_a)
        Jugador.objects.create(usuario=me, partida=p_a, simbolo="X")
        Jugador.objects.create(usuario=friend, partida=p_a, simbolo="O")

        # Movimiento 1 (Antiguo)
        c1 = Celda.objects.get(tablero=t_a, fila=0, columna=0)
        c1.valor = "X"
        c1.save()
        Movimiento.objects.create(partida=p_a, jugador=me, celda=c1)

        # Movimiento 2 (El Último)
        c2 = Celda.objects.get(tablero=t_a, fila=1, columna=1)
        c2.valor = "O"
        c2.save()
        m_ultimo = Movimiento.objects.create(partida=p_a, jugador=friend, celda=c2)

        # 3. Partida B (Sin movimientos aún)
        p_b = Partida.objects.create(turno_actual=me)
        Tablero.objects.create(partida=p_b)
        Jugador.objects.create(usuario=me, partida=p_b, simbolo="X")

        # 4. Partida C (Ajena)
        p_c = Partida.objects.create()
        Tablero.objects.create(partida=p_c)
        Jugador.objects.create(usuario=friend, partida=p_c, simbolo="X")
        Jugador.objects.create(usuario=stranger, partida=p_c, simbolo="O")

        return {
            "me": me, 
            "friend": friend, 
            "p_a": p_a, 
            "p_b": p_b, 
            "p_c": p_c,
            "m_ultimo": m_ultimo
        }

    def test_obtener_ultimo_movimiento_exito(self, api_client, setup_datos):
        """Verifica que se recupera correctamente el movimiento más reciente."""
        data = setup_datos
        api_client.force_authenticate(user=data["me"])
        
        url = reverse('ultimo_movimiento', kwargs={'partida_id': data["p_a"].id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["estado"] == "jugando"
        assert response.data["movimiento"]["posicion"] == [1, 1]

    def test_error_partida_sin_movimientos(self, api_client, setup_datos):
        """Verifica el error 400 cuando la partida no tiene historial."""
        data = setup_datos
        api_client.force_authenticate(user=data["me"])
        
        url = reverse('ultimo_movimiento', kwargs={'partida_id': data["p_b"].id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["Error"] == "Esta partida no tiene ningún movimiento aún"

    def test_error_acceso_denegado_partida_ajena(self, api_client, setup_datos):
        """Un usuario no puede ver el último movimiento de una partida donde no juega."""
        data = setup_datos
        api_client.force_authenticate(user=data["me"])
        
        # Intento acceder a la Partida C (Friend vs Stranger)
        url = reverse('ultimo_movimiento', kwargs={'partida_id': data["p_c"].id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["Error"] == "No puedes ver los movimientos de esa partida"

    def test_obtener_ultimo_movimiento_partida_finalizada(self, api_client, setup_datos):
        """Verifica el estado de la respuesta cuando la partida ha terminado."""
        data = setup_datos
        p_a = data["p_a"]
        p_a.finalizada = True
        p_a.ganador = data["me"]
        p_a.save()

        api_client.force_authenticate(user=data["me"])
        url = reverse('ultimo_movimiento', kwargs={'partida_id': p_a.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["estado"] == "ganada"