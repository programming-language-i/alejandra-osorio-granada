import time
from concurrent.futures import ThreadPoolExecutor


def consultar(producto):
    time.sleep(1)
    return f"Producto {producto}: consulta terminada"


def main():
    productos = range(1, 6)

    inicio = time.perf_counter()

    with ThreadPoolExecutor(max_workers=5) as pool:
        resultados = list(pool.map(consultar, productos))

    for resultado in resultados:
        print(resultado)

    duracion = time.perf_counter() - inicio
    print(f"Tiempo total: {duracion:.1f} s")


if __name__ == "__main__":
    main()