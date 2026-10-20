"""Registro sincronizado y sesiones; conserva la interfaz del parcial."""
import hmac
import queue
import secrets
import socket
import threading
import time
from datetime import datetime, timezone

from .protocolo import enviar_mensaje

CANALES = frozenset({"general", "recepcion", "alistamiento", "despacho"})


class Sesion:
    def __init__(self, nombre: str, conexion: socket.socket, ip: str) -> None:
        self.nombre = nombre
        self.conexion = conexion
        self.ip = ip
        self.token = secrets.token_hex(24)
        self.canales = {"general"}
        self.actividad = time.monotonic()
        self.ultima_actividad = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._pendientes: queue.Queue[str] = queue.Queue(maxsize=128)
        self.cerrada = threading.Event()

    def enviar(self, texto: str) -> None:
        """Encola sin bloquear a los demás si esta estación deja de leer."""
        if self.cerrada.is_set():
            raise OSError("Sesión cerrada")
        try:
            self._pendientes.put_nowait(texto)
        except queue.Full as error:
            self.cerrar()
            raise OSError("Estación demasiado lenta") from error

    def despachar(self) -> None:
        """Único hilo que escribe en este socket: las tramas no se mezclan."""
        try:
            while not self.cerrada.is_set():
                try:
                    texto = self._pendientes.get(timeout=0.5)
                except queue.Empty:
                    continue
                enviar_mensaje(self.conexion, texto)
        except (OSError, ValueError):
            self.cerrar()

    def cerrar(self) -> None:
        self.cerrada.set()
        try:
            self.conexion.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


class RegistroClientes:
    def __init__(self) -> None:
        self._clientes: dict[str, socket.socket] = {}
        self._sesiones: dict[str, Sesion] = {}
        self._lock = threading.RLock()

    def insertar(self, nombre: str, conexion: socket.socket) -> bool:
        with self._lock:
            if nombre in self._clientes:
                return False
            self._clientes[nombre] = conexion
            return True

    def registrar(self, sesion: Sesion, saludo: str) -> bool:
        with self._lock:
            if not self.insertar(sesion.nombre, sesion.conexion):
                return False
            # El saludo queda primero en la cola antes de publicar la sesión.
            sesion.enviar(saludo)
            self._sesiones[sesion.nombre] = sesion
            return True

    def buscar(self, nombre: str) -> socket.socket | None:
        with self._lock:
            return self._clientes.get(nombre)

    def buscar_sesion(self, nombre: str) -> Sesion | None:
        with self._lock:
            sesion = self._sesiones.get(nombre)
            return sesion if sesion and not sesion.cerrada.is_set() else None

    def borrar(self, nombre: str) -> None:
        with self._lock:
            self._clientes.pop(nombre, None)
            self._sesiones.pop(nombre, None)

    def retirar(self, sesion: Sesion) -> None:
        with self._lock:
            if self._sesiones.get(sesion.nombre) is sesion:
                self.borrar(sesion.nombre)

    def destinatarios(self, excepto: str) -> list[tuple[str, socket.socket]]:
        with self._lock:
            return [(n, c) for n, c in self._clientes.items() if n != excepto]

    def cambiar_canal(self, sesion: Sesion, canal: str, unir: bool) -> list[str]:
        if canal not in CANALES:
            raise ValueError("Canal inexistente")
        if not unir and canal == "general":
            raise ValueError("No se puede abandonar #general")
        with self._lock:
            if unir:
                sesion.canales.add(canal)
            else:
                sesion.canales.discard(canal)
            return sorted(sesion.canales)

    def miembros(self, sesion: Sesion, canal: str) -> list[Sesion]:
        with self._lock:
            if canal not in CANALES or canal not in sesion.canales:
                raise ValueError("Debes unirte al canal antes de enviar")
            return [s for s in self._sesiones.values()
                    if s is not sesion and canal in s.canales and not s.cerrada.is_set()]

    def actividad(self, nombre: str, token: str, ip: str) -> bool:
        with self._lock:
            sesion = self._sesiones.get(nombre)
            if (sesion is None or sesion.ip != ip
                    or not hmac.compare_digest(sesion.token.encode(), token.encode("utf-8"))):
                return False
            sesion.actividad = time.monotonic()
            sesion.ultima_actividad = datetime.now(timezone.utc).isoformat(timespec="seconds")
            return True

    def listar(self) -> list[dict[str, object]]:
        with self._lock:
            ahora = time.monotonic()
            return [{"nombre": s.nombre,
                     "estado": "inactivo" if ahora - s.actividad > 15 else "activo",
                     "ultima_actividad": s.ultima_actividad,
                     "segundos_sin_actividad": round(ahora - s.actividad, 1),
                     "canales": sorted(s.canales)}
                    for s in self._sesiones.values() if not s.cerrada.is_set()]

    def cerrar_todas(self) -> None:
        with self._lock:
            sesiones = list(self._sesiones.values())
        for sesion in sesiones:
            sesion.cerrar()
