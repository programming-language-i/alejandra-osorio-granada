#Imprime hola
#Después imprime false
#finalmente imprime hilo.start
#No puede haber: hilo.start(), hilo.join(), hilo.start()
#Se debe crear otro objeto: hilo2 = threading.Thread(target=print, args=("hola",)), hilo2.start()



import threading

hilo = threading.Thread(target=print, args=("hola",))
hilo.start()
hilo.join()
print(hilo.is_alive())
hilo.start()