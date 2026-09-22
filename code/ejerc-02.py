import threading
import time

def imprimir_mensaje(numero, temperatura):
    for i in range(5):
        print(f"Hilo {numero}: {numero} - {temperatura}°C")
        time.sleep(1)

def main():
    h1 = threading.Thread(target=imprimir_mensaje, args=(1, 30))
    h2 = threading.Thread(target=imprimir_mensaje, args=(2, 40))
    h3 = threading.Thread(target=imprimir_mensaje, args=(3, 50))
    h4 = threading.Thread(target=imprimir_mensaje, args=(4, 60))

    h1.start()
    h2.start()
    h3.start()
    h4.start()

    h1.join()
    h2.join()
    h3.join()
    h4.join()

    print("Finalizo")

if __name__ == "__main__":
    main()