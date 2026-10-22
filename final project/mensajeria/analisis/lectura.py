"""Conversión pura de líneas y borde generador de lectura."""
from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from ..mensaje import Mensaje


class Registro(NamedTuple):
    tipo: str
    emisor: str
    canal: str | None
    destino: str | None
    contenido: str
    timestamp: datetime


def desde_linea(linea: str) -> Registro | None:
    mensaje = Mensaje.desde_json(linea)
    if mensaje is None or mensaje.tipo not in ("mensaje", "privado"):
        return None
    return Registro(*mensaje)


def registros(lineas: Iterable[str]) -> Iterator[Registro]:
    return filter(None, map(desde_linea, lineas))


def leer_mensajes(ruta: str | Path) -> Iterator[Registro]:
    # Límite de línea: evita reservar memoria ilimitada por un log dañado.
    with open(ruta, "rb") as archivo:
        def lineas() -> Iterator[str]:
            while True:
                linea = archivo.readline(65537)
                if not linea:
                    return
                if len(linea) > 65536:
                    while not linea.endswith(b"\n"):
                        linea = archivo.readline(65537)
                        if not linea:
                            return
                    continue
                try:
                    yield linea.decode("utf-8")
                except UnicodeDecodeError:
                    continue
        yield from registros(lineas())
