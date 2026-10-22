"""Verificaciones de la guía. --puras no abre archivos, red ni hilos."""
import argparse
import queue
import socket
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from mensajeria.analisis.lectura import Registro, desde_linea, leer_mensajes, registros
from mensajeria.analisis.metricas import de_emisor, mensajes_por_hora, palabras_frecuentes, top_emisores
from mensajeria.bitacora import Bitacora
from mensajeria.mensaje import Mensaje
from mensajeria.persistencia import a_linea, escribir, se_guarda
from mensajeria.protocolo import enviar_mensaje, recibir_mensaje
from mensajeria.servidor_json import ServidorMensajeria, decodificar

RAIZ = Path(__file__).resolve().parent


def verificar_puras() -> None:
    m = Mensaje("mensaje", "Ana", "general", None, "Pedido listo",
                datetime(2026, 10, 20, 8, tzinfo=timezone.utc))
    otro = m._replace(emisor="Beto", contenido="Pedido urgente")
    privado = m._replace(tipo="privado", canal=None, destino="Beto", contenido="listo.",
                         timestamp=datetime(2026, 10, 20, 9, tzinfo=timezone.utc))
    # Si una función pura intenta abrir o imprimir, esta prueba falla.
    with patch("builtins.open", side_effect=AssertionError("Efecto archivo")), patch("builtins.print", side_effect=AssertionError("Efecto pantalla")):
        assert m.a_json() == m.a_json()
        assert "\n" not in m.a_json()
        assert Mensaje.desde_json(m.a_json()) == m
        assert desde_linea(m.a_json()) == Registro(*m)
        assert desde_linea(privado.a_json()) == Registro(*privado)
        for mala in ("", "{", "5", "[]", '{"emisor":"Ana"}',
                     '{"tipo":"mensaje","emisor":"Ana","contenido":"hola","timestamp":"ayer"}'):
            assert desde_linea(mala) is None
        assert se_guarda(m) and se_guarda(privado)
        for tipo in ("unirse", "dejar", "error"):
            assert not se_guarda(m._replace(tipo=tipo))
        lineas = (m.a_json(), "{", otro.a_json(), "basura", privado.a_json())
        flujo = registros(lineas)
        assert not isinstance(flujo, list)
        datos = tuple(flujo)
        assert len(datos) == len(lineas) - 2
        assert tuple(flujo) == ()
        antes = tuple(datos)
        assert top_emisores(datos, 3) == top_emisores(datos, 3) == [("Ana", 2), ("Beto", 1)]
        assert mensajes_por_hora(datos) == mensajes_por_hora(datos)
        assert mensajes_por_hora(datos)[8] == 2
        assert mensajes_por_hora(datos)[9] == 1
        assert palabras_frecuentes(datos, 2) == palabras_frecuentes(datos, 2) == [("pedido", 2), ("listo", 2)]
        assert datos == antes
        assert len(tuple(de_emisor("Ana", datos))) == 2
        assert top_emisores((), 3) == []
        assert palabras_frecuentes(datos, 0) == []
        assert m.emisor == "Ana" and otro.emisor == "Beto"


def verificar_escritor() -> None:
    m = Mensaje("mensaje", "Ana", "general", None, "recepción\nlínea dos",
                datetime(2026, 10, 20, 8, tzinfo=timezone.utc))
    with tempfile.TemporaryDirectory(dir=RAIZ) as temporal:
        ruta = Path(temporal) / "mensajes.log"
        cola: queue.Queue[Mensaje | None] = queue.Queue()
        hilo = threading.Thread(target=escribir, args=(cola, ruta, a_linea, se_guarda), daemon=False)
        hilo.start()
        for _ in range(10):
            cola.put(m)
        for tipo in ("unirse", "dejar", "error"):
            cola.put(m._replace(tipo=tipo))
        cola.put(None)
        hilo.join(timeout=10)
        assert not hilo.is_alive()
        with ruta.open(encoding="utf-8") as archivo:
            assert sum(1 for _ in archivo) == 10
        with ruta.open("a", encoding="utf-8") as archivo:
            archivo.write("{\nbasura\n")
        assert sum(1 for _ in leer_mensajes(ruta)) == 10


def puerto_libre(tipo: socket.SocketKind = socket.SOCK_STREAM) -> int:
    with socket.socket(socket.AF_INET, tipo) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def verificar_chat() -> None:
    import json
    with tempfile.TemporaryDirectory(dir=RAIZ) as temporal:
        ruta = Path(temporal) / "datos/mensajes.log"
        bitacora = Bitacora(ruta)
        servidor = ServidorMensajeria(bitacora)
        puerto = puerto_libre()
        udp = puerto_libre(socket.SOCK_DGRAM)
        errores: list[BaseException] = []

        def ejecutar() -> None:
            try:
                servidor.ejecutar("127.0.0.1", puerto, udp)
            except BaseException as error:
                errores.append(error)

        hilo = threading.Thread(target=ejecutar, daemon=False)
        clientes: list[socket.socket] = []
        hilo.start()

        def recibir(sock: socket.socket) -> dict[str, object]:
            texto = recibir_mensaje(sock)
            assert texto is not None
            return decodificar(texto)

        try:
            for nombre in ("Ana", "Beto"):
                for intento in range(100):
                    try:
                        sock = socket.create_connection(("127.0.0.1", puerto), timeout=3)
                        break
                    except OSError:
                        if intento == 99:
                            raise
                        time.sleep(.05)
                clientes.append(sock)
                enviar_mensaje(sock, json.dumps({"tipo": "registro", "nombre": nombre}))
                assert recibir(sock)["tipo"] == "ok"
            a, b = clientes
            enviar_mensaje(a, '{"tipo":"unirse","canal":"despacho"}')
            assert recibir(a)["tipo"] == "canales"
            enviar_mensaje(a, '{"tipo":"desconocido"}')
            assert recibir(a)["tipo"] == "error"
            for i in range(10):
                enviar_mensaje(a, json.dumps({"tipo": "mensaje", "contenido": f"pedido {i}"}))
                assert recibir(a)["tipo"] == "ok"
                assert recibir(b)["contenido"] == f"pedido {i}"
        finally:
            for sock in clientes:
                sock.close()
            servidor.detener()
            hilo.join(timeout=15)
            bitacora.cerrar()
        assert not hilo.is_alive(), "El cierre no debe dejar al escritor esperando"
        assert not errores, errores
        with ruta.open(encoding="utf-8") as archivo:
            assert sum(1 for _ in archivo) == 10
        assert sum(1 for _ in leer_mensajes(ruta)) == 10


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puras", action="store_true")
    args = parser.parse_args()
    verificar_puras()
    print("OK: funciones puras, ida/vuelta, líneas dañadas y datos sin modificar")
    if not args.puras:
        verificar_escritor()
        verificar_chat()
        print("OK: escritor con centinela y cierre; 2 clientes, 10 mensajes, unirse y error = 10 líneas")


if __name__ == "__main__":
    main()
