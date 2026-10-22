"""Borde del reporte: abre mediante leer_mensajes, llama a métricas e imprime."""
import argparse
from pathlib import Path
from typing import TextIO

from .lectura import leer_mensajes
from .metricas import mensajes_por_hora, palabras_frecuentes, top_emisores


def reporte(ruta: str | Path, salida: TextIO, n: int = 20) -> None:
    # Cada flujo se consume una vez; se vuelve a abrir, sin materializar el log.
    print("Emisores:", top_emisores(leer_mensajes(ruta), n), file=salida)
    print("Mensajes por hora (zona del timestamp):", mensajes_por_hora(leer_mensajes(ruta)), file=salida)
    print("Palabras frecuentes:", palabras_frecuentes(leer_mensajes(ruta), n), file=salida)


def main() -> None:
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ruta", nargs="?", type=Path,
                        default=Path(__file__).resolve().parents[2] / "datos/mensajes.log")
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    if args.salida and args.salida.resolve() == args.ruta.resolve():
        parser.error("El reporte no puede sobrescribir el log")
    try:
        if args.salida:
            args.salida.parent.mkdir(parents=True, exist_ok=True)
            with args.salida.open("w", encoding="utf-8") as salida:
                reporte(args.ruta, salida)
            print(f"Reporte guardado en {args.salida}")
        else:
            reporte(args.ruta, sys.stdout)
    except OSError as error:
        parser.exit(1, f"No se pudo generar el reporte: {error}\n")


if __name__ == "__main__":
    main()
