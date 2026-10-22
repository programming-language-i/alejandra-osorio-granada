"""Reporte exacto en una pasada: generadores y agregación SQLite en disco."""
import argparse
import re
import sqlite3
import tempfile
from contextlib import closing
from datetime import timedelta, timezone
from pathlib import Path
from typing import Iterator, TextIO

from .analisis.lectura import leer_mensajes
from .mensaje import Mensaje

PALABRAS = re.compile(r"[^\W\d_]+", re.UNICODE)


def mensajes(ruta: Path) -> Iterator[Mensaje]:
    for registro in leer_mensajes(ruta):
        if registro.timestamp.tzinfo is not None:
            yield Mensaje(*registro)


def claves(mensaje: Mensaje, zona: timezone) -> Iterator[tuple[str, str]]:
    """Transformación pura: autor, hora y palabras de un mensaje."""
    yield "autor", mensaje.emisor
    yield "hora", f"{mensaje.timestamp.astimezone(zona).hour:02d}"
    for palabra in map(lambda coincidencia: coincidencia.group(0), PALABRAS.finditer(mensaje.contenido.casefold())):
        yield "palabra", palabra


def generar(ruta: Path, salida: TextIO, desfase: int = -5) -> int:
    if not -12 <= desfase <= 14:
        raise ValueError("El desfase horario debe estar entre -12 y 14")
    zona = timezone(timedelta(hours=desfase))
    # La cardinalidad de autores y vocabulario crece en disco, no en contadores RAM.
    with tempfile.TemporaryDirectory(prefix="reporte_", dir=ruta.resolve().parent) as temporal:
        with closing(sqlite3.connect(str(Path(temporal) / "conteos.sqlite"))) as db:
            db.execute("PRAGMA cache_size = -2048")
            db.execute("PRAGMA temp_store = FILE")
            db.execute("CREATE TABLE conteos (grupo TEXT, clave TEXT, n INTEGER, PRIMARY KEY(grupo, clave))")
            total = 0
            for mensaje in mensajes(ruta):
                db.executemany("INSERT INTO conteos VALUES (?, ?, 1) ON CONFLICT(grupo, clave) DO UPDATE SET n=n+1",
                               claves(mensaje, zona))
                total += 1
                if total % 1000 == 0:
                    db.commit()
            db.commit()
            print(f"Mensajes válidos: {total}", file=salida)
            print(f"Horas en UTC{desfase:+d}. Incluye mensajes de canal y privados.", file=salida)
            print("Líneas dañadas o sin campos válidos se descartan.", file=salida)
            print("\nMensajes por persona:", file=salida)
            for nombre, cantidad in db.execute("SELECT clave,n FROM conteos WHERE grupo='autor' ORDER BY n DESC,clave"):
                print(f"{nombre}: {cantidad}", file=salida)
            print("\nMensajes por hora:", file=salida)
            for hora in range(24):
                fila = db.execute("SELECT n FROM conteos WHERE grupo='hora' AND clave=?", (f"{hora:02d}",)).fetchone()
                print(f"{hora:02d}:00: {fila[0] if fila else 0}", file=salida)
            print("\n20 palabras más frecuentes (incluye artículos y preposiciones):", file=salida)
            for palabra, cantidad in db.execute("SELECT clave,n FROM conteos WHERE grupo='palabra' ORDER BY n DESC,clave LIMIT 20"):
                print(f"{palabra}: {cantidad}", file=salida)
            return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ruta", nargs="?", type=Path,
                        default=Path(__file__).resolve().parent.parent / "datos/mensajes.log")
    parser.add_argument("--salida", type=Path)
    parser.add_argument("--desfase", type=int, default=-5, help="Desfase UTC; por defecto Colombia (-5)")
    args = parser.parse_args()
    if args.salida and args.salida.resolve() == args.ruta.resolve():
        parser.error("El reporte no puede sobrescribir la bitácora")
    try:
        if args.salida:
            args.salida.parent.mkdir(parents=True, exist_ok=True)
            with args.salida.open("w", encoding="utf-8") as salida:
                generar(args.ruta, salida, args.desfase)
            print(f"Reporte guardado en {args.salida}")
        else:
            import sys
            generar(args.ruta, sys.stdout, args.desfase)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"No se pudo generar el reporte: {error}\n")


if __name__ == "__main__":
    main()
