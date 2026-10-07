import socket
import threading

HOST = "127.0.0.1"
PORT = 8000

clientes = []
nombres = {}
lock = threading.Lock()


def enviar_mensajes(mensaje, cliente_actual=None):
    print("Funcion de atecion de mensajes")
    with lock:
        for cliente in clientes:
            if cliente != cliente_actual:
                try:
                    cliente.sendall(mensaje)
                except OSError:
                    print("Error")


def atender_clientes(conexion, direccion):
    nombre = conexion.recv(1024).decode()
    conexion.sendall(b"OK")

    print(f"Cliente conectado: {direccion}")
    print(f"Nombre del cliente: {nombre}")

    with lock:
        clientes.append(conexion)
        nombres[conexion] = nombre

    try:
        while True:
            datos = conexion.recv(1024)

            if not datos:
                break

            print(f"[{direccion}] [{nombre}] {datos.decode()}")

            enviar_mensajes(datos, conexion)

    except ConnectionResetError:
        print(f"Desconexion de cliente {direccion}")
    finally:
        with lock:
            if conexion in clientes:
                clientes.remove(conexion)
            nombres.pop(conexion, None)
        conexion.close()

        print(f"Cliente desconectado: {direccion}")


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    servidor.bind((HOST, PORT))
    servidor.listen()

    print(f"Servidor escuchando en {HOST}:{PORT}")

    while True:
        conexion, direccion = servidor.accept()

        hilo = threading.Thread(target=atender_clientes, args=(conexion, direccion))

        hilo.start()