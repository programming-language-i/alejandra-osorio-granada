import json
import socket
import sys
import threading
from datetime import datetime

from mensajeria.protocolo import enviar_mensaje, recibir_mensaje
from mensajeria.registro import RegistroClientes

HOST = "127.0.0.1"
PUERTO = 8000

_lock_envios = threading.Lock()


def responder_error(conexion: socket.socket, detalle: str) -> None:
    """Envías una trama de error estructurada en formato JSON al cliente."""
    payload = json.dumps({"tipo": "error", "detalle": detalle}, ensure_ascii=False)
    with _lock_envios:
        try:
            enviar_mensaje(conexion, payload)
        except OSError:
            pass


def atender(
    conexion: socket.socket,
    direccion: tuple[str, int],
    registro: RegistroClientes,
) -> None:
    """Atiende a UN cliente en su propio hilo manejando tramas JSON."""
    nombre = None
    registrado = False

    try:
        # El saludo inicial sigue siendo texto plano (nombre de usuario)
        nombre = recibir_mensaje(conexion)

        if nombre is None:
            return

        if not nombre.strip():
            with _lock_envios:
                enviar_mensaje(conexion, "ERROR")
            return

        with _lock_envios:
            registrado = registro.insertar(nombre, conexion)

            if not registrado:
                enviar_mensaje(conexion, "ERROR: nombre en uso")
                return

            enviar_mensaje(conexion, "OK")

        print(f"{nombre} conectado desde {direccion}")

        # Bucle principal de recepción de tramas JSON
        while True:
            texto = recibir_mensaje(conexion)

            if texto is None:
                break

            # 1. Validar que la trama sea un JSON válido
            try:
                pedido = json.loads(texto)
            except (json.JSONDecodeError, TypeError):
                # Un JSON dañado se ignora o se notifica, pero no corta la conexión
                continue

            if not isinstance(pedido, dict):
                responder_error(conexion, "El pedido debe ser un objeto JSON")
                continue

            tipo = pedido.get("tipo")

            # 2. Manejo de tipo "mensaje" (broadcast general)
            if tipo == "mensaje":
                contenido = pedido.get("contenido")
                if not isinstance(contenido, str) or not contenido:
                    responder_error(conexion, "El mensaje requiere el campo 'contenido'")
                    continue

                # Preparar trama con emisor real y timestamp ISO 8601
                respuesta = {
                    "tipo": "mensaje",
                    "emisor": nombre,  # Se sobrescribe para evitar falsificación
                    "canal": "general",
                    "contenido": contenido,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
                payload = json.dumps(respuesta, ensure_ascii=False)

                # Reenviar a todos menos al emisor
                with _lock_envios:
                    for dest_nombre, dest_conexion in registro.destinatarios(excepto=nombre):
                        try:
                            enviar_mensaje(dest_conexion, payload)
                        except OSError:
                            continue

            # 3. Manejo de tipo "privado"
            elif tipo == "privado":
                destino = pedido.get("destino")
                contenido = pedido.get("contenido")

                if not isinstance(contenido, str) or not contenido:
                    responder_error(conexion, "El mensaje privado requiere 'contenido'")
                    continue

                if not isinstance(destino, str) or not destino:
                    responder_error(conexion, "El mensaje privado requiere 'destino'")
                    continue

                # No se pueden enviar privados a uno mismo
                if destino == nombre:
                    responder_error(conexion, "No puede enviarse un privado a sí mismo")
                    continue

                # Buscar la conexión del destinatario pasando excepto=""
                dest_conexion = None
                with _lock_envios:
                    destinatarios_dict = dict(registro.destinatarios(excepto=""))
                    dest_conexion = destinatarios_dict.get(destino)

                if dest_conexion is None:
                    responder_error(conexion, f"El destinatario '{destino}' no está conectado")
                    continue

                respuesta = {
                    "tipo": "privado",
                    "emisor": nombre,  # Se sobrescribe para evitar falsificación
                    "destino": destino,
                    "contenido": contenido,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
                payload = json.dumps(respuesta, ensure_ascii=False)

                # Enviar solo al cliente de destino
                with _lock_envios:
                    try:
                        enviar_mensaje(dest_conexion, payload)
                    except OSError:
                        pass

            # 4. Tipo de pedido desconocido
            else:
                responder_error(conexion, f"Tipo de pedido desconocido: '{tipo}'")

    except (OSError, UnicodeDecodeError) as error:
        print(f"Error con el cliente {direccion}: {error}")

    finally:
        if registrado:
            registro.borrar(nombre)
            print(f"{nombre} desconectado")

        conexion.close()


def main() -> None:
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else PUERTO
    registro = RegistroClientes()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.bind((HOST, puerto))
        servidor.listen()
        print(f"escuchando en {HOST}:{puerto}")

        while True:
            conexion, direccion = servidor.accept()

            hilo = threading.Thread(
                target=atender,
                args=(conexion, direccion, registro),
                daemon=True,
            )
            hilo.start()


if __name__ == "_main_":
    try:
        main()
    except KeyboardInterrupt:
        print("\nservidor detenido")
    
