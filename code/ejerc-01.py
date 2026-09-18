import threading
import time

def imprimir_mensaje():
    for i in range (5):
        print("Hello")
        time.sleep(1)

def main():
    thread = threading.Thread()

if __name__ == "__main__":
    main()
    