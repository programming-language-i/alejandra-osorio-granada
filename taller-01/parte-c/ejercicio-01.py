import threading


class Descarga(threading.Thread):
    def __init__(self, archivo):
        self.archivo = archivo

    def run(self):
        print("descargando", self.archivo)


Descarga("a.zip").start()