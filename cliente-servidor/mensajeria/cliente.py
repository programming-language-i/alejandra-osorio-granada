import socket
import threading

HOST = "127.0.0.1"
PORT = 8000


def recibir_mensaje(conexion):
    while True:
        try:
            datos = conexion.recv(1024)

            if not datos:
                print("\nSe perdió la conexión")
                break

            print(f"\nMensaje: {datos.decode()}")
            print("> ", end="", flush=True)

        except ConnectionResetError:
            print("\nConexión terminada")
            break


nombre = input("Ingresa el nombre del cliente: ").strip()

while not nombre:
    nombre = input("Ingresa tu nombre: ").strip()


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente:
    cliente.connect((HOST, PORT))

    print(f"Conectado al servidor como {nombre}")
    print("Escribe un mensaje. Usa '0' para salir")

    hilo = threading.Thread(
        target=recibir_mensaje,
        args=(cliente,),
        daemon=True
    )
    hilo.start()

    while True:
        mensaje = input("> ")

        if mensaje == "0":
            break

        cliente.sendall(f"{nombre}: {mensaje}".encode())