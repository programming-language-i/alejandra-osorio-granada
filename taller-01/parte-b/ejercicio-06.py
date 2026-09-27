#Tenemos class Contador(threading.Thread):  eventos = []
#Esto quiere decir que eventos pertenece a la clase, por lo que es compartido
#Pero self.total = 0 pertenece a cada instancia, cada hilo incrementa su propoo total 3 veces
#Es decir a.total = 3, b.total = 3, eventos = 6 elementos, salida 3 3 y 6
import threading


class Contador(threading.Thread):
    eventos = []

    def __init__(self, nombre):
        super().__init__(name=nombre)
        self.total = 0

    def run(self):
        for _ in range(3):
            self.total += 1
            self.eventos.append(self.name)


a, b = Contador("a"), Contador("b")
for h in (a, b):
    h.start()
for h in (a, b):
    h.join()
print(a.total, b.total, len(a.eventos))