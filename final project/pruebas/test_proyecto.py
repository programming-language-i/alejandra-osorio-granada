"""Pruebas de integración. Ejecutar: python -m unittest discover -s pruebas -v."""
import io
import json
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from mensajeria.bitacora import Bitacora
from mensajeria.protocolo import MAX_TRAMA, enviar_mensaje, recibir_mensaje
from mensajeria.reporte import generar
from mensajeria.registro import Sesion
from mensajeria.servidor_json import ServidorMensajeria

RAIZ = Path(__file__).resolve().parent.parent


def puerto_libre(tipo=socket.SOCK_STREAM):
    with socket.socket(socket.AF_INET, tipo) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Integracion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporal = tempfile.TemporaryDirectory(prefix="prueba_", dir=RAIZ)
        cls.ruta = Path(cls.temporal.name) / "bitacora.jsonl"
        cls.puerto = puerto_libre()
        cls.udp = puerto_libre(socket.SOCK_DGRAM)
        cls.arrancar()

    @classmethod
    def arrancar(cls):
        cls.proceso = subprocess.Popen([sys.executable, str(RAIZ / "servidor_json.py"),
            str(cls.puerto), "--udp", str(cls.udp), "--bitacora", str(cls.ruta)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for _ in range(100):
            if cls.proceso.poll() is not None:
                raise RuntimeError(cls.proceso.stderr.read().decode(errors="replace"))
            try:
                with socket.create_connection(("127.0.0.1", cls.puerto), timeout=.1):
                    return
            except OSError:
                time.sleep(.05)
        raise RuntimeError("El servidor no arrancó")

    @classmethod
    def parar(cls):
        cls.proceso.terminate()
        cls.proceso.wait(timeout=5)
        cls.proceso.stdout.close()
        cls.proceso.stderr.close()

    @classmethod
    def tearDownClass(cls):
        cls.parar()
        cls.temporal.cleanup()

    def setUp(self):
        self.sockets = []
        self.prefijo = uuid.uuid4().hex[:8]

    def tearDown(self):
        for sock in self.sockets:
            sock.close()

    def conectar(self, nombre):
        sock = socket.create_connection(("127.0.0.1", self.puerto), timeout=3)
        self.sockets.append(sock)
        self.enviar(sock, {"tipo": "registro", "nombre": nombre})
        return sock, self.recibir(sock)

    def cliente(self, sufijo):
        nombre = self.prefijo + sufijo
        sock, respuesta = self.conectar(nombre)
        self.assertEqual(respuesta["tipo"], "ok")
        return sock, nombre, respuesta["token"]

    def enviar(self, sock, dato):
        enviar_mensaje(sock, json.dumps(dato, ensure_ascii=True))

    def recibir(self, sock):
        texto = recibir_mensaje(sock)
        self.assertIsNotNone(texto)
        return json.loads(texto)

    def sin_mensaje(self, sock):
        sock.settimeout(.15)
        with self.assertRaises(socket.timeout):
            sock.recv(1)
        sock.settimeout(3)

    def test_general_autoria_bitacora_y_duplicado(self):
        a, nombre, _ = self.cliente("Ana")
        b, _, _ = self.cliente("Beto")
        c, _, _ = self.cliente("Carla")
        _, respuesta = self.conectar(nombre)
        self.assertEqual(respuesta["tipo"], "error")
        self.enviar(a, {"tipo": "mensaje", "contenido": "café operación", "emisor": "falso", "timestamp": "ayer"})
        self.assertEqual(self.recibir(a)["tipo"], "ok")
        for destino in (b, c):
            recibido = self.recibir(destino)
            self.assertEqual(recibido["emisor"], nombre)
            self.assertEqual(recibido["contenido"], "café operación")
            self.assertNotEqual(recibido["timestamp"], "ayer")
        filas = [json.loads(l) for l in self.ruta.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sum(f["emisor"] == nombre for f in filas), 1)

    def test_canales_entrada_salida_y_privados(self):
        a, _, _ = self.cliente("Ana")
        b, nombre_b, _ = self.cliente("Beto")
        c, _, _ = self.cliente("Carla")
        self.enviar(a, {"tipo": "mensaje", "canal": "despacho", "contenido": "no permitido"})
        self.assertEqual(self.recibir(a)["tipo"], "error")
        for sock in (a, b):
            self.enviar(sock, {"tipo": "unir", "canal": "despacho"})
            self.assertIn("despacho", self.recibir(sock)["canales"])
        self.enviar(a, {"tipo": "mensaje", "canal": "despacho", "contenido": "pedido listo"})
        self.assertEqual(self.recibir(a)["tipo"], "ok")
        self.assertEqual(self.recibir(b)["canal"], "despacho")
        self.sin_mensaje(c)
        self.enviar(b, {"tipo": "salir", "canal": "despacho"})
        self.recibir(b)
        self.enviar(a, {"tipo": "mensaje", "canal": "despacho", "contenido": "otro pedido"})
        self.recibir(a)
        self.sin_mensaje(b)
        self.enviar(a, {"tipo": "privado", "destino": nombre_b, "contenido": "solo Beto"})
        self.assertEqual(self.recibir(a)["tipo"], "ok")
        self.assertEqual(self.recibir(b)["tipo"], "privado")
        self.sin_mensaje(c)
        for pedido in ({"tipo": "salir", "canal": "general"},
                       {"tipo": "privado", "destino": "ausente", "contenido": "hola"}):
            self.enviar(a, pedido)
            self.assertEqual(self.recibir(a)["tipo"], "error")

    def test_entradas_invalidas_y_desconexion_parcial(self):
        a, _, _ = self.cliente("Ana")
        b, _, _ = self.cliente("Beto")
        for texto in ("{", "[]", "[" * 1100, '{"tipo":"mensaje","contenido":"\\ud800"}',
                      '{"tipo":"mensaje","contenido":{}}', '{"tipo":"raro"}'):
            enviar_mensaje(a, texto)
            self.assertEqual(self.recibir(a)["tipo"], "error")
        a.sendall(struct.pack("!I", 1) + b"\xff")
        self.assertEqual(self.recibir(a)["tipo"], "error")
        roto, _, _ = self.cliente("Roto")
        roto.sendall(struct.pack("!I", 100) + b"{")
        roto.close()
        enorme, _, _ = self.cliente("Enorme")
        enorme.sendall(struct.pack("!I", MAX_TRAMA + 1))
        self.assertIsNone(recibir_mensaje(enorme))
        self.enviar(a, {"tipo": "mensaje", "contenido": "sigue funcionando"})
        self.assertEqual(self.recibir(a)["tipo"], "ok")
        self.assertEqual(self.recibir(b)["contenido"], "sigue funcionando")

    def test_mensajes_concurrentes_sin_mezclarse(self):
        clientes = [self.cliente(str(i)) for i in range(3)]
        errores = []
        barrera = threading.Barrier(3)

        def trabajo(sock, nombre):
            try:
                barrera.wait(timeout=3)
                for i in range(5):
                    self.enviar(sock, {"tipo": "mensaje", "contenido": f"{nombre}:{i}"})
                respuestas = [self.recibir(sock) for _ in range(15)]
                self.assertEqual(sum(r["tipo"] == "ok" for r in respuestas), 5)
                self.assertEqual(sum(r["tipo"] == "mensaje" for r in respuestas), 10)
            except Exception as error:
                errores.append(error)

        hilos = [threading.Thread(target=trabajo, args=(s, n)) for s, n, _ in clientes]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(timeout=10)
            self.assertFalse(hilo.is_alive())
        self.assertFalse(errores, errores)

    def test_udp_inactividad_y_token(self):
        a, nombre, token = self.cliente("Ana")
        time.sleep(15.3)

        def estado():
            self.enviar(a, {"tipo": "usuarios"})
            return next(u for u in self.recibir(a)["usuarios"] if u["nombre"] == nombre)["estado"]

        self.assertEqual(estado(), "inactivo")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            for datos in (b"{", b"[]", json.dumps({"tipo": "actividad", "nombre": nombre, "token": "incorrecto"}).encode()):
                udp.sendto(datos, ("127.0.0.1", self.udp))
            time.sleep(.1)
            self.assertEqual(estado(), "inactivo")
            udp.sendto(json.dumps({"tipo": "actividad", "nombre": nombre, "token": token}).encode(), ("127.0.0.1", self.udp))
            time.sleep(.1)
            self.assertEqual(estado(), "activo")

    def test_z_persistencia_tras_reinicio(self):
        a, nombre, _ = self.cliente("Persistente")
        self.enviar(a, {"tipo": "mensaje", "contenido": "persistente"})
        self.assertEqual(self.recibir(a)["tipo"], "ok")
        self.parar()
        self.arrancar()
        filas = [json.loads(l) for l in self.ruta.read_text(encoding="utf-8").splitlines()]
        self.assertTrue(any(f["emisor"] == nombre for f in filas))
        nuevo, _, _ = self.cliente("Nuevo")
        self.enviar(nuevo, {"tipo": "usuarios"})
        self.assertEqual(self.recibir(nuevo)["tipo"], "usuarios")


class ProtocoloYReporte(unittest.TestCase):
    def test_fallo_fsync_revierte_registro_y_permite_reintentar(self):
        with tempfile.TemporaryDirectory(dir=RAIZ) as temporal:
            bitacora = Bitacora(Path(temporal) / "bitacora.jsonl")
            mensaje = {"tipo": "mensaje", "emisor": "Ana", "contenido": "pedido listo", "timestamp": "2026-10-15T15:00:00+00:00"}
            with patch("mensajeria.persistencia.os.fsync", side_effect=[OSError("Disco lleno"), None]):
                with self.assertRaises(OSError):
                    bitacora.guardar(mensaje)
            self.assertEqual(bitacora.ruta.read_bytes() if bitacora.ruta.exists() else b"", b"")
            bitacora.guardar(mensaje)
            self.assertEqual(generar(bitacora.ruta, io.StringIO()), 1)
            bitacora.cerrar()

    def test_fallo_de_disco_no_entrega_ni_confirma(self):
        with tempfile.TemporaryDirectory(dir=RAIZ) as temporal:
            bitacora = Bitacora(Path(temporal) / "bitacora.jsonl")
            servidor = ServidorMensajeria(bitacora)
            a, b = socket.socketpair()
            self.addCleanup(a.close)
            self.addCleanup(b.close)
            emisor = Sesion("Ana", a, "127.0.0.1")
            receptor = Sesion("Beto", b, "127.0.0.1")
            servidor.registro.registrar(emisor, "OK")
            servidor.registro.registrar(receptor, "OK")
            with patch.object(bitacora, "guardar", side_effect=OSError("Disco lleno")), patch.object(servidor, "responder") as responder:
                servidor.procesar(emisor, {"tipo": "mensaje", "contenido": "no debe entregarse"})
            responder.assert_called_once()
            sesion, respuesta = responder.call_args.args
            self.assertIs(sesion, emisor)
            self.assertEqual(respuesta["tipo"], "error")
            self.assertEqual(bitacora.ruta.read_bytes() if bitacora.ruta.exists() else b"", b"")
            bitacora.cerrar()

    def test_framing_fragmentado_y_utf8(self):
        a, b = socket.socketpair()
        self.addCleanup(a.close)
        self.addCleanup(b.close)
        cuerpo = "operación café".encode("utf-8")
        trama = struct.pack("!I", len(cuerpo)) + cuerpo
        hilo = threading.Thread(target=lambda: [a.sendall(bytes([n])) for n in trama])
        hilo.start()
        self.assertEqual(recibir_mensaje(b), "operación café")
        hilo.join(timeout=3)

    def test_bitacora_recupera_ultima_linea_incompleta(self):
        with tempfile.TemporaryDirectory(dir=RAIZ) as temporal:
            ruta = Path(temporal) / "bitacora.jsonl"
            ruta.write_bytes(b'{"tipo":')
            bitacora = Bitacora(ruta)
            mensaje = {"tipo": "mensaje", "emisor": "Ana", "contenido": "café", "timestamp": "2026-10-15T15:00:00+00:00"}
            bitacora.guardar(mensaje)
            salida = io.StringIO()
            self.assertEqual(generar(ruta, salida), 1)
            self.assertIn("10:00: 1", salida.getvalue())
            self.assertIn("café: 1", salida.getvalue())
            bitacora.cerrar()


if __name__ == "__main__":
    unittest.main()
