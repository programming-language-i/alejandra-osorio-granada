# Tiempo estimado 2 segundos
#La división procude error, pero como se utiliza el pool de hilos se ejecuta de forma concurrente
from concurrent.futures import ThreadPoolExecutor


def dividir(a, b):
    return a / b


with ThreadPoolExecutor() as pool:
    futuro = pool.submit(dividir, 1, 0)
print("listo")