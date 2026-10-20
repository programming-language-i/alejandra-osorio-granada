import socket
import threading


class RegistroClientes:
    def __init__(self) -> None:
        self._clientes: dict[str, socket.socket] = {}
        self._lock = threading.Lock()

    def insertar(self, nombre: str, conexion: socket.socket) -> bool:
        with self._lock:
            if nombre in self._clientes:
                return False

            self._clientes[nombre] = conexion
            return True

    def buscar(self, nombre: str) -> socket.socket | None:
        with self._lock:
            return self._clientes.get(nombre)

    def borrar(self, nombre: str) -> None:
        with self._lock:
            self._clientes.pop(nombre, None)

    def destinatarios(self, excepto: str) -> list[tuple[str, socket.socket]]:
        with self._lock:
            return [
                (nombre, conexion)
                for nombre, conexion in self._clientes.items()
                if nombre != excepto
            ]

            
    