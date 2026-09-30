"""
PARCIAL 1 - Ejercicio E1 (30 pts)
Estación meteorológica: un hilo por sensor

Complete los TODO. Cada sensor es un HILO creado por HERENCIA de
threading.Thread y guarda SU PROPIO estado (sus lecturas y su promedio).
La lectura i de un sensor tarda TIEMPO_LECTURA segundos y vale  base + i.

Requisitos:
  1. class Sensor(threading.Thread), que llama a super().__init__().
  2. Sobrescribe run(), NO start().
  3. Estado por instancia: self.lecturas (lista) y self.promedio. Sin variables
     globales para los resultados.
  4. Los 3 sensores corren EN PARALELO: primero start() a todos y después join().
  5. El programa imprime exactamente esto, con el tiempo total ~1.5 s (el sensor
     más lento) y no ~3.6 s (la suma):

        T1: 5 lecturas, promedio 22.0
        H1: 3 lecturas, promedio 61.0
        P1: 4 lecturas, promedio 1001.5
        Tiempo total: 1.5 s
"""
import threading
import time

# (nombre, cantidad de lecturas, valor base)
SENSORES = [("T1", 5, 20), ("H1", 3, 60), ("P1", 4, 1000)]
TIEMPO_LECTURA = 0.3


class Sensor(threading.Thread):

    # TODO 1
    def __init__(self, nombre, cantidad, base):
        super().__init__()
        self.nombre = nombre
        self.cantidad = cantidad
        self.base = base
        self.lecturas = []
        self.promedio = None

    # TODO 2
    def run(self):
        for i in range(self.cantidad):
            time.sleep(TIEMPO_LECTURA)
            self.lecturas.append(self.base + i)

        self.promedio = sum(self.lecturas) / len(self.lecturas)


inicio = time.perf_counter()

# TODO 3
sensores = []

for nombre, cantidad, base in SENSORES:
    sensor = Sensor(nombre, cantidad, base)
    sensores.append(sensor)

# Primero arrancamos TODOS
for sensor in sensores:
    sensor.start()

# Después esperamos TODOS
for sensor in sensores:
    sensor.join()


# TODO 4
for sensor in sensores:
    print(
        f"{sensor.nombre}: {len(sensor.lecturas)} lecturas, "
        f"promedio {sensor.promedio}"
    )


print(f"Tiempo total: {time.perf_counter() - inicio:.1f} s")
