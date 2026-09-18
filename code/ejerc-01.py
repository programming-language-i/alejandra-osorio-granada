import threading
import time

def imprimir_mensaje():
    for i in range (5):
        print(f"{i}Hello")
        time.sleep(1)

def main():
    thread = threading.Thread(target=imprimir_mensaje)

    thread.start()
    thread.join()

    print("Finalizo")

if __name__ == "__main__":
    main()
