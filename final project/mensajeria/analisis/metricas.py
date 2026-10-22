"""Funciones puras: datos de entrada -> resultado; sin red, archivo ni reloj."""
import re
from collections import Counter
from collections.abc import Iterable, Iterator
from functools import partial
from operator import attrgetter

from .lectura import Registro


def top_emisores(registros: Iterable[Registro], n: int) -> list[tuple[str, int]]:
    return Counter(map(attrgetter("emisor"), registros)).most_common(max(n, 0))


def mensajes_por_hora(registros: Iterable[Registro]) -> dict[int, int]:
    conteos = Counter(map(lambda registro: registro.timestamp.hour, registros))
    return {hora: conteos[hora] for hora in range(24)}


def palabras_frecuentes(registros: Iterable[Registro], n: int) -> list[tuple[str, int]]:
    palabras = (palabra for registro in registros
                for palabra in re.findall(r"[^\W\d_]+", registro.contenido.lower()))
    return Counter(palabras).most_common(max(n, 0))


def es_de(emisor: str, registro: Registro) -> bool:
    return registro.emisor == emisor


def de_emisor(emisor: str, registros: Iterable[Registro]) -> Iterator[Registro]:
    return filter(partial(es_de, emisor), registros)
