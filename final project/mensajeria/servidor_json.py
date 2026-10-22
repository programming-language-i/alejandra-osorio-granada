"""Servidor final: TCP, canales, privados, persistencia y disponibilidad UDP."""
import argparse
import json
import socket
import threading
from pathlib import Path

from .bitacora import Bitacora
from .conexion import crear_mensaje
from .protocolo import enviar_mensaje, recibir_mensaje
from .registro import CANALES, RegistroClientes, Sesion

HOST = "127.0.0.1"
PUERTO = 8000
PUERTO_UDP = 8001


def texto_valido(valor: object, campo: str, limite: int) -> str:
    if not isinstance(valor, str) or not valor.strip() or len(valor) > limite:
        raise ValueError(f"{campo}: se requieren entre 1 y {limite} caracteres")
    try:
        valor.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError(f"{campo}: Unicode inválido") from error
    return valor


def decodificar(texto: str) -> dict[str, object]:
    try:
        dato = json.loads(texto)
    except (ValueError, RecursionError) as error:
        raise ValueError("JSON inválido") from error
    if not isinstance(dato, dict):
        raise ValueError("Se requiere un objeto JSON")
    return dato


class ServidorMensajeria:
    def __init__(self, bitacora: Bitacora) -> None:
        self.registro = RegistroClientes()
        self.bitacora = bitacora
        self._detener = threading.Event()
        self._lock_hilos = threading.Lock()
        self._hilos: set[threading.Thread] = set()
        self._conexiones: set[socket.socket] = set()

    def responder(self, sesion: Sesion, mensaje: dict[str, object]) -> None:
        sesion.enviar(json.dumps(mensaje, ensure_ascii=False))

    def procesar(self, sesion: Sesion, pedido: dict[str, object]) -> None:
        tipo = pedido.get("tipo")
        if tipo == "usuarios":
            self.responder(sesion, {"tipo": "usuarios", "usuarios": self.registro.listar()})
            return
        if tipo == "canales":
            self.responder(sesion, {"tipo": "canales", "canales": sorted(CANALES)})
            return
        if tipo in ("unir", "salir", "unirse", "dejar"):
            canal = texto_valido(pedido.get("canal"), "canal", 20).lstrip("#")
            canales = self.registro.cambiar_canal(sesion, canal, tipo in ("unir", "unirse"))
            self.responder(sesion, {"tipo": "canales", "canales": canales,
                                   "detalle": f"{tipo}: #{canal}"})
            return
        if tipo not in ("mensaje", "privado"):
            raise ValueError("Tipo de pedido desconocido")
        contenido = texto_valido(pedido.get("contenido"), "contenido", 4000)
        canal_mensaje: str | None = None
        destino_mensaje: str | None = None
        if tipo == "mensaje":
            canal = texto_valido(pedido.get("canal", "general"), "canal", 20).lstrip("#")
            destinos = self.registro.miembros(sesion, canal)
            canal_mensaje = canal
        else:
            destino = texto_valido(pedido.get("destino"), "destino", 40)
            if destino == sesion.nombre:
                raise ValueError("No puedes enviarte un privado a ti mismo")
            receptor = self.registro.buscar_sesion(destino)
            if receptor is None:
                raise ValueError("El destinatario no está conectado")
            destinos = [receptor]
            destino_mensaje = destino
        mensaje = crear_mensaje(str(tipo), sesion.nombre, contenido, canal_mensaje, destino_mensaje)
        # Nada se entrega ni se confirma hasta terminar fsync.
        try:
            self.bitacora.guardar(mensaje)
        except OSError:
            self.responder(sesion, {"tipo": "error", "detalle": "No se pudo guardar; mensaje rechazado"})
            return
        entregados = 0
        for receptor in destinos:
            try:
                self.responder(receptor, mensaje.a_dict())
                entregados += 1
            except OSError:
                receptor.cerrar()
        self.responder(sesion, {"tipo": "ok", "detalle": "Mensaje guardado",
                               "destinatarios_encolados": entregados})

    def atender(self, conexion: socket.socket, direccion: tuple[str, int]) -> None:
        sesion: Sesion | None = None
        registrada = False
        try:
            conexion.settimeout(10)
            saludo = recibir_mensaje(conexion)
            if saludo is None:
                return
            pedido = decodificar(saludo)
            if pedido.get("tipo") != "registro":
                raise ValueError("La primera trama debe ser un registro JSON")
            nombre = texto_valido(pedido.get("nombre"), "nombre", 40).strip()
            if any(c.isspace() or not c.isprintable() for c in nombre):
                raise ValueError("El nombre no debe contener espacios ni caracteres de control")
            sesion = Sesion(nombre, conexion, direccion[0])
            respuesta = json.dumps({"tipo": "ok", "nombre": nombre, "token": sesion.token,
                                   "canales": ["general"]}, ensure_ascii=False)
            registrada = self.registro.registrar(sesion, respuesta)
            if not registrada:
                raise ValueError("Nombre en uso")
            conexion.settimeout(None)
            threading.Thread(target=sesion.despachar, daemon=True).start()
            while not sesion.cerrada.is_set():
                try:
                    texto = recibir_mensaje(conexion)
                except UnicodeDecodeError:
                    self.responder(sesion, {"tipo": "error", "detalle": "UTF-8 inválido"})
                    continue
                if texto is None:
                    break
                try:
                    self.procesar(sesion, decodificar(texto))
                except ValueError as error:
                    self.responder(sesion, {"tipo": "error", "detalle": str(error)})
        except (OSError, ValueError, RecursionError) as error:
            if not registrada:
                try:
                    enviar_mensaje(conexion, json.dumps({"tipo": "error", "detalle": str(error)}))
                except OSError:
                    pass
        finally:
            if sesion is not None:
                if registrada:
                    self.registro.retirar(sesion)
                sesion.cerrar()
            conexion.close()
            with self._lock_hilos:
                self._conexiones.discard(conexion)
                self._hilos.discard(threading.current_thread())

    def recibir_actividad(self, udp: socket.socket, detener: threading.Event) -> None:
        while not detener.is_set():
            try:
                datos, direccion = udp.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                pedido = decodificar(datos.decode("utf-8"))
                if pedido.get("tipo") != "actividad":
                    continue
                nombre = texto_valido(pedido.get("nombre"), "nombre", 40)
                token = texto_valido(pedido.get("token"), "token", 48)
                self.registro.actividad(nombre, token, direccion[0])
            except (ValueError, RecursionError):
                continue

    def detener(self) -> None:
        self._detener.set()

    def ejecutar(self, host: str, puerto: int, puerto_udp: int) -> None:
        detener = self._detener
        with socket.socket() as tcp, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tcp.bind((host, puerto))
            udp.bind((host, puerto_udp))
            udp.settimeout(0.5)
            tcp.listen()
            tcp.settimeout(0.2)
            hilo_udp = threading.Thread(target=self.recibir_actividad, args=(udp, detener), daemon=True)
            hilo_udp.start()
            print(f"Servidor listo en {host}: TCP {puerto}, UDP {puerto_udp}", flush=True)
            try:
                while not detener.is_set():
                    try:
                        conexion, direccion = tcp.accept()
                    except socket.timeout:
                        continue
                    hilo = threading.Thread(target=self.atender, args=(conexion, direccion), daemon=True)
                    with self._lock_hilos:
                        self._hilos.add(hilo)
                        self._conexiones.add(conexion)
                    hilo.start()
            finally:
                detener.set()
                self.registro.cerrar_todas()
                with self._lock_hilos:
                    conexiones = tuple(self._conexiones)
                    hilos = tuple(self._hilos)
                for conexion in conexiones:
                    try:
                        conexion.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                for hilo in hilos:
                    hilo.join()
                # Primero terminan los productores; después centinela y join del escritor.
                self.bitacora.cerrar()
                hilo_udp.join(timeout=1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("puerto", nargs="?", type=int, default=PUERTO)
    parser.add_argument("--udp", type=int, default=PUERTO_UDP)
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--bitacora", type=Path,
                        default=Path(__file__).resolve().parent.parent / "datos/mensajes.log")
    args = parser.parse_args()
    try:
        ServidorMensajeria(Bitacora(args.bitacora)).ejecutar(args.host, args.puerto, args.udp)
    except KeyboardInterrupt:
        print("\nServidor detenido")


if __name__ == "__main__":
    main()
