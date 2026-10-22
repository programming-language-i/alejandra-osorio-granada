"""Un único borde de escritura; funciones de decisión inyectadas."""
import os
import queue
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from .mensaje import Mensaje

TIPOS_GUARDADOS = frozenset({"mensaje", "privado"})
T = TypeVar("T")


def se_guarda(mensaje: Mensaje) -> bool:
    return mensaje.tipo in TIPOS_GUARDADOS


def a_linea(mensaje: Mensaje) -> str:
    return mensaje.a_json()


def escribir(cola: "queue.Queue[T | None]", ruta: str | Path,
             serializar: Callable[[T], str], decidir: Callable[[T], bool],
             confirmar: Callable[[T, OSError | None], None] | None = None) -> None:
    """Centinela None; fsync antes de confirmar; siempre libera al productor."""
    archivo = None
    error_apertura: OSError | None = None
    fallida = False
    try:
        try:
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
            archivo = open(ruta, "a+b", buffering=0)
            if archivo.tell():
                archivo.seek(-1, os.SEEK_END)
                if archivo.read(1) != b"\n":
                    archivo.write(b"\n")
                    os.fsync(archivo.fileno())
        except OSError as error:
            error_apertura = error
        while True:
            elemento = cola.get()
            try:
                if elemento is None:
                    return
                error_actual = error_apertura
                if error_actual is None:
                    try:
                        if fallida or archivo is None:
                            raise OSError("Bitácora bloqueada por un error de disco")
                        if decidir(elemento):
                            linea = serializar(elemento)
                            if "\n" in linea or "\r" in linea:
                                raise ValueError("El serializador debe producir una sola línea")
                            datos = (linea + "\n").encode("utf-8")
                            archivo.seek(0, os.SEEK_END)
                            inicio = archivo.tell()
                            try:
                                escritos = 0
                                while escritos < len(datos):
                                    cantidad = archivo.write(datos[escritos:])
                                    if not cantidad:
                                        raise OSError("Escritura incompleta")
                                    escritos += cantidad
                                archivo.flush()
                                os.fsync(archivo.fileno())
                            except OSError:
                                try:
                                    archivo.truncate(inicio)
                                    os.fsync(archivo.fileno())
                                except OSError:
                                    fallida = True
                                raise
                    except (OSError, ValueError, TypeError) as error:
                        error_actual = OSError(str(error))
                if confirmar is not None:
                    confirmar(elemento, error_actual)
                elif error_actual is not None:
                    raise error_actual
            finally:
                cola.task_done()
    finally:
        if archivo is not None:
            archivo.close()
