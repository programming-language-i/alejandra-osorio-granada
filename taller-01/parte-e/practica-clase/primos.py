import math
from concurrent.futures import ProcessPoolExecutor


def es_primo(n):
    if n < 2:
        return n, False

    limite = math.isqrt(n)

    for divisor in range(2, limite + 1):
        if n % divisor == 0:
            return n, False

    return n, True


def main():
    numeros = [
        2,
        5,
        6,
        11,
        23,
        29,
        30
    ]

    with ProcessPoolExecutor(max_workers=4) as pool:
        resultados = list(pool.map(es_primo, numeros))

    for numero, primo in resultados:
        print(numero, "es primo" if primo else "no es primo")


if __name__ == "__main__":
    main()