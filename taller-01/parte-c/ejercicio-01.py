#RuntimeError: thread.__init__() not called
#Se creó un __init__() pero no se inicializó la clase
import threading


class Descarga(threading.Thread):
    def __init__(self, archivo):
        super().__init__()
        self.archivo = archivo

    def run(self):
        print("descargando", self.archivo)

Descarga("a.zip").start()





