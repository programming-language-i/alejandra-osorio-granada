"""Borde del reloj: el servidor fija autor y fecha una sola vez."""
from datetime import datetime, timezone

from .mensaje import Mensaje


def crear_mensaje(tipo: str, emisor: str, contenido: str,
                  canal: str | None = None, destino: str | None = None) -> Mensaje:
    return Mensaje(tipo, emisor, canal, destino, contenido,
                   datetime.now(timezone.utc).replace(microsecond=0))
