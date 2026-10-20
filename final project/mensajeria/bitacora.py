"""Bitácora JSONL: un mensaje completo por línea, persistido antes de confirmar."""
import json
import os
import threading
from pathlib import Path


class Bitacora:
    def __init__(self, ruta: Path) -> None:
        self.ruta = ruta
        ruta.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._fallida = False
        # Una caída durante una escritura podría dejar una última línea parcial.
        # Se preserva su contenido y se separa de los nuevos registros.
        with ruta.open("a+b") as archivo:
            if archivo.tell():
                archivo.seek(-1, os.SEEK_END)
                if archivo.read(1) != b"\n":
                    archivo.seek(0, os.SEEK_END)
                    archivo.write(b"\n")
                    archivo.flush()
                    os.fsync(archivo.fileno())

    def guardar(self, mensaje: dict[str, object]) -> None:
        linea = (json.dumps(mensaje, ensure_ascii=False) + "\n").encode("utf-8")
        with self._lock:
            if self._fallida:
                raise OSError("Bitácora bloqueada por un error de disco anterior")
            # Sin buffer para poder deshacer incluso una escritura parcial.
            with self.ruta.open("a+b", buffering=0) as archivo:
                inicio = archivo.tell()
                try:
                    escritos = 0
                    while escritos < len(linea):
                        cantidad = archivo.write(linea[escritos:])
                        if not cantidad:
                            raise OSError("Escritura incompleta de la bitácora")
                        escritos += cantidad
                    archivo.flush()
                    os.fsync(archivo.fileno())
                except OSError:
                    try:
                        archivo.truncate(inicio)
                        os.fsync(archivo.fileno())
                    except OSError:
                        # No concatenar futuros mensajes con una línea dañada.
                        self._fallida = True
                    raise
