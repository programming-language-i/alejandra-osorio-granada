#Error no estas utilizando if __name__ == "__main__":
#Con métodos de creación de procesos que vuelven a importar el módulo, puede provocar creación recursiva de procesos o en efecto errores, durante el inicio. 

from concurrent.futures import ProcessPoolExecutor


def cuadrado(n):
    return n * n


if __name__ == "__main__":
    with ProcessPoolExecutor(max_workers=2) as pool:
        print(list(pool.map(cuadrado, range(4))))

