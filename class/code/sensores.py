import threading
import time

def sensor(numero, temperatura ):
    print(f"{numero} sensor")

    for i in range(1, 6):
        print(f"{numero} - {i+1}: temperatura {temperatura} centigrados")
        time.sleep(1)

    print("termino")

if __name__ == "__main__":
    threads = [
        threading.Thread(target=sensor, args=("sensor 1", 30)),
        threading.Thread(target=sensor, args=("sensor 2", 40)),
        threading.Thread(target=sensor, args=("sensor 3", 50)),
        threading.Thread(target=sensor, args=("sensor 4", 60)),
        threading.Thread(target=sensor, args=("sensor 5", 70)),

    ]

    for thread in threads:
        thread.start()

    for thread in threads:
            thread.join()

    print("finalizo proceso")
