"""Cliente del servidor JSON. Uso: python cliente_json.py Ana [puerto]."""
import json
import socket
import sys
import threading

from mensajeria.protocolo import enviar_mensaje, recibir_mensaje

HOST = "127.0.0.1"
PUERTO = 8000


def mostrar(texto: str) -> None:
    try:
        mensaje = json.loads(texto)
    except ValueError:
        print(texto)
        return
    if not isinstance(mensaje, dict):
        print(mensaje)
    elif mensaje.get("tipo") == "error":
        print(f"Error: {mensaje.get('detalle')}")
    else:
        etiqueta = "privado" if mensaje.get("tipo") == "privado" else "#general"
        print(f"[{mensaje.get('timestamp', '')}] [{etiqueta}] {mensaje.get('emisor', '')}: {mensaje.get('contenido', '')}")


def recibir(conexion: socket.socket, detener: threading.Event) -> None:
    try:
        while not detener.is_set():
            texto = recibir_mensaje(conexion)
            if texto is None:
                break
            print()
            mostrar(texto)
            print("> ", end="", flush=True)
    except (OSError, ValueError, UnicodeDecodeError):
        pass
    finally:
        detener.set()
        print("\nServidor desconectado. Pulsa Enter para terminar.")


def crear_pedido(texto: str) -> dict[str, str]:
    if texto.startswith("/privado "):
        partes = texto.split(maxsplit=2)
        if len(partes) != 3:
            raise ValueError("Uso: /privado nombre mensaje")
        return {"tipo": "privado", "destino": partes[1], "contenido": partes[2]}
    if texto.startswith("/"):
        raise ValueError("Comando desconocido. Usa /privado nombre mensaje o /fin")
    return {"tipo": "mensaje", "contenido": texto}


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python cliente_json.py <nombre> [puerto]")
        return
    nombre = sys.argv[1]
    puerto = int(sys.argv[2]) if len(sys.argv) > 2 else PUERTO
    detener = threading.Event()
    with socket.create_connection((HOST, puerto)) as conexion:
        # Conserva el saludo del parcial: nombre y confirmación OK, ambos con framing.
        enviar_mensaje(conexion, nombre)
        respuesta = recibir_mensaje(conexion)
        if respuesta != "OK":
            print(f"Registro rechazado: {respuesta}")
            return
        print(f"Conectado como {nombre}. Texto: general; /privado nombre mensaje; /fin o 0: salir.")
        threading.Thread(target=recibir, args=(conexion, detener), daemon=True).start()
        try:
            while not detener.is_set():
                texto = input("> ")
                if texto in ("0", "/fin") or detener.is_set():
                    break
                if not texto.strip():
                    continue
                try:
                    pedido = crear_pedido(texto)
                    enviar_mensaje(conexion, json.dumps(pedido, ensure_ascii=False))
                except ValueError as error:
                    print(error)
        finally:
            detener.set()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nCliente terminado")
    except (OSError, ValueError, UnicodeDecodeError) as error:
        print(f"No se pudo continuar: {error}")
