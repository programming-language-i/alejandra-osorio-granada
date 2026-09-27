#El error es: class Tarea(threading.Thread):    def start(self): ya que se escribio start() cuando debería escribir run()
#Por eso vemos t0 lista, t1 lista, t2 lista, 3.0 s
#Depués t.join()
#Termina generando un error: RuntimeError: cannot join thread before it is started
#Nunca se ejecuto el verdadero threading.Thread.start() por lo que el hilo nunca fue iniciado
#Con la corrección los 3 se pueden solapar
import threading
import time


class Tarea(threading.Thread):
    def run(self):
        time.sleep(1)
        print(self.name, "lista")


inicio = time.perf_counter()

tareas = [Tarea(name=f"t{i}") for i in range(3)]

for t in tareas:
    t.start()

print(f"{time.perf_counter() - inicio:.1f} s")

for t in tareas:
    t.join()