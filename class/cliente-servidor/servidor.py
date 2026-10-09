import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(("127.0.0.1", 8080))
    servidor.listen()
    print("Servidor escuchando", servidor.getsockname())
    conexion, direccion = servidor.accept()
    with conexion:
        print("Conexión desde", direccion)
        datos = conexion.recv(1024)
        print("Recibido:", datos)
        conexion.sendall(datos.upper())