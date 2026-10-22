"""Fachada compatible: el cliente espera a que el escritor confirme fsync."""
import json
import queue
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .mensaje import Mensaje
from .persistencia import escribir, se_guarda


@dataclass
class Solicitud:
    mensaje: Mensaje
    linea: str
    lista: threading.Event = field(default_factory=threading.Event)
    error: OSError | None = None


def serializar_solicitud(solicitud: Solicitud) -> str:
    return solicitud.linea


def guardar_solicitud(solicitud: Solicitud) -> bool:
    return se_guarda(solicitud.mensaje)


def confirmar_solicitud(solicitud: Solicitud, error: OSError | None) -> None:
    solicitud.error = error
    solicitud.lista.set()


class Bitacora:
    def __init__(self, ruta: Path) -> None:
        self.ruta = ruta
        self._cola: queue.Queue[Solicitud | None] = queue.Queue(maxsize=128)
        self._hilo: threading.Thread | None = None
        self._lock = threading.Lock()
        self._cerrada = False

    def guardar(self, mensaje: Mensaje | dict[str, object]) -> None:
        if isinstance(mensaje, dict):
            convertido = Mensaje.desde_json(json.dumps(mensaje, ensure_ascii=False))
            if convertido is None:
                raise ValueError("Mensaje inválido")
            mensaje = convertido
        # Serialización pura antes de encolar; el timestamp ya viene fijado.
        solicitud = Solicitud(mensaje, mensaje.a_json())
        with self._lock:
            if self._cerrada:
                raise OSError("Bitácora cerrada")
            if self._hilo is None:
                self._hilo = threading.Thread(target=escribir,
                    args=(self._cola, self.ruta, serializar_solicitud,
                          guardar_solicitud, confirmar_solicitud), daemon=False,
                    name="escritor-bitacora")
                self._hilo.start()
            self._cola.put(solicitud)
        solicitud.lista.wait()
        if solicitud.error is not None:
            raise solicitud.error

    def cerrar(self) -> None:
        with self._lock:
            if not self._cerrada:
                self._cerrada = True
                if self._hilo is not None:
                    self._cola.put(None)
            hilo = self._hilo
        if hilo is not None:
            hilo.join()
