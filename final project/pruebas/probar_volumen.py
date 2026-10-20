"""Prueba opcional de 100000 mensajes. Ejecutar: python pruebas/probar_volumen.py."""
import json
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from mensajeria.reporte import generar


def letras(numero: int) -> str:
    resultado = ""
    for _ in range(5):
        resultado = chr(97 + numero % 26) + resultado
        numero //= 26
    return resultado


def medir(cantidad: int, carpeta: Path) -> tuple[float, int]:
    ruta = carpeta / f"mensajes_{cantidad}.jsonl"
    with ruta.open("w", encoding="utf-8") as archivo:
        for i in range(cantidad):
            archivo.write(json.dumps({"tipo": "mensaje", "emisor": f"operario{i:06}",
                "contenido": f"pedido listo palabra{letras(i)}", "timestamp": "2026-10-15T15:00:00+00:00"}) + "\n")
    inicio = time.perf_counter()
    tracemalloc.start()
    salida = carpeta / f"reporte_{cantidad}.txt"
    with salida.open("w", encoding="utf-8") as archivo:
        total = generar(ruta, archivo)
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert total == cantidad
    with salida.open(encoding="utf-8") as archivo:
        assert archivo.readline().strip() == f"Mensajes válidos: {cantidad}"
        texto = archivo.read()
    assert f"pedido: {cantidad}" in texto
    assert f"listo: {cantidad}" in texto
    assert f"10:00: {cantidad}" in texto
    return time.perf_counter() - inicio, pico


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="volumen_", dir=RAIZ) as temporal:
        carpeta = Path(temporal)
        tiempo_pequeno, pico_pequeno = medir(1000, carpeta)
        tiempo_grande, pico_grande = medir(100000, carpeta)
        assert pico_grande < pico_pequeno + 2 * 1024 * 1024
        print(json.dumps({"mensajes": 100000, "autores_distintos": 100000,
            "palabras_distintas": 100002, "tiempo_1000_s": round(tiempo_pequeno, 2),
            "tiempo_100000_s": round(tiempo_grande, 2), "pico_python_1000_bytes": pico_pequeno,
            "pico_python_100000_bytes": pico_grande,
            "nota": "tracemalloc mide memoria Python; SQLite mantiene una caché de 2 MiB y agregaciones en disco"}, indent=2))


if __name__ == "__main__":
    main()
