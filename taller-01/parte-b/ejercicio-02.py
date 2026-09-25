#El código crea un hilo daemon que necesita 2 segundos, pero el programa principal solamente espera 0,5 segundos antes de terminar.
#Tiempo estimado 2 segundos

import threading
import time


def guardar():
    try:
        time.sleep(2)
        print("guardado")
    finally:
        print("archivo cerrado")


threading.Thread(target=guardar, daemon=True).start()
time.sleep(0.5)
print("fin")