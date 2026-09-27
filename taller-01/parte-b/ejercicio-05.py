#El padre tiene resultados = []
#Cada proceso esta realizando un resultados.append(n * n) pero la salida sera []
#Los procesos no comparten automáticamente la misma memoria, es decir cada proceso tiene su copia de reustaldos. 
#Por ejemplo: Proceso 0 → [0], Proceso 1 → [1], Proceso 2 → [4], Proceso 3 → [9]
#Los cambios de los hijos no modifican la lista del proceso padre.

import multiprocessing

resultados = []


def calcular(n):
    resultados.append(n * n)


if __name__ == "__main__":
    procesos = [multiprocessing.Process(target=calcular, args=(n,)) for n in range(4)]
    for p in procesos:
        p.start()
    for p in procesos:
        p.join()
    print(resultados)