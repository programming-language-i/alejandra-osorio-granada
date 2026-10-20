"""Cliente de consola con recepción y avisos de actividad en hilos separados."""
import argparse
import json
import socket
import threading

from .protocolo import enviar_mensaje, recibir_mensaje
from .registro import CANALES

AYUDA = """Texto: enviar al canal seleccionado.
/unir despacho       unirse al canal (también recepcion o alistamiento)
/canal despacho      seleccionar dónde escribir
/salir despacho      abandonar un canal
/privado Ana texto   enviar solo a Ana
/usuarios            ver estados y última actividad
/canales             ver los canales disponibles
/pausa               suspender avisos UDP para demostrar inactividad
/activo              reanudar avisos UDP
/ayuda               mostrar esta ayuda
/fin o 0             desconectarse"""


def crear_pedido(texto: str, canal: str = "general") -> dict[str, object]:
    if texto in ("/usuarios", "/canales"):
        return {"tipo": texto[1:]}
    if texto.startswith(("/unir ", "/salir ")):
        comando, nombre = texto.split(maxsplit=1)
        return {"tipo": comando[1:], "canal": nombre.strip().lstrip("#")}
    if texto.startswith("/privado "):
        partes = texto.split(maxsplit=2)
        if len(partes) != 3:
            raise ValueError("Uso: /privado nombre mensaje")
        return {"tipo": "privado", "destino": partes[1], "contenido": partes[2]}
    if texto.startswith("/"):
        raise ValueError("Comando desconocido; escribe /ayuda")
    return {"tipo": "mensaje", "canal": canal, "contenido": texto}


def mostrar(mensaje: dict[str, object]) -> str:
    tipo = mensaje.get("tipo")
    if tipo in ("mensaje", "privado"):
        etiqueta = "privado" if tipo == "privado" else f"#{mensaje.get('canal')}"
        return f"[{mensaje.get('timestamp')}] [{etiqueta}] {mensaje.get('emisor')}: {mensaje.get('contenido')}"
    if tipo == "usuarios":
        lineas = ["Usuarios conectados:"]
        usuarios = mensaje.get("usuarios")
        if isinstance(usuarios, list):
            for usuario in usuarios:
                if isinstance(usuario, dict):
                    lineas.append(f"  {usuario.get('nombre')}: {usuario.get('estado')} | última actividad UTC: {usuario.get('ultima_actividad')} | canales: {usuario.get('canales')}")
        return "\n".join(lineas)
    if tipo == "canales":
        return f"{mensaje.get('detalle', 'Canales')}: {mensaje.get('canales')}"
    return f"{tipo}: {mensaje.get('detalle', '')}"


def recibir(conexion: socket.socket, detener: threading.Event) -> None:
    try:
        while not detener.is_set():
            texto = recibir_mensaje(conexion)
            if texto is None:
                break
            mensaje = json.loads(texto)
            if isinstance(mensaje, dict):
                print("\n" + mostrar(mensaje), flush=True)
                print("> ", end="", flush=True)
    except (OSError, ValueError, RecursionError):
        pass
    finally:
        detener.set()
        print("\nConexión cerrada. Pulsa Enter para terminar.", flush=True)


def actividad(host: str, puerto: int, nombre: str, token: str,
              detener: threading.Event, pausa: threading.Event) -> None:
    datos = json.dumps({"tipo": "actividad", "nombre": nombre, "token": token}).encode("utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        while not detener.is_set():
            if not pausa.is_set():
                try:
                    udp.sendto(datos, (host, puerto))
                except OSError:
                    print("\nNo se pudo enviar el aviso de actividad UDP", flush=True)
            detener.wait(5)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nombre")
    parser.add_argument("puerto", nargs="?", type=int, default=8000)
    parser.add_argument("--udp", type=int, default=8001)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    detener, pausa = threading.Event(), threading.Event()
    with socket.create_connection((args.host, args.puerto), timeout=10) as conexion:
        enviar_mensaje(conexion, json.dumps({"tipo": "registro", "nombre": args.nombre}, ensure_ascii=False))
        texto = recibir_mensaje(conexion)
        if texto is None:
            raise OSError("El servidor cerró antes de confirmar el registro")
        respuesta = json.loads(texto)
        if not isinstance(respuesta, dict) or respuesta.get("tipo") != "ok":
            print(f"Registro rechazado: {respuesta}")
            return
        token = respuesta.get("token")
        nombre = respuesta.get("nombre")
        if not isinstance(token, str) or not isinstance(nombre, str):
            raise ValueError("Registro sin datos de sesión válidos")
        conexion.settimeout(None)
        threading.Thread(target=recibir, args=(conexion, detener), daemon=True).start()
        hilo_udp = threading.Thread(target=actividad,
                                    args=(args.host, args.udp, nombre, token, detener, pausa), daemon=True)
        hilo_udp.start()
        print(f"Conectado como {nombre} en #general.\n{AYUDA}")
        canal = "general"
        try:
            while not detener.is_set():
                texto = input(f"#{canal}> ").strip()
                if texto in ("/fin", "0") or detener.is_set():
                    break
                if not texto:
                    continue
                if texto == "/ayuda":
                    print(AYUDA)
                    continue
                if texto in ("/pausa", "/activo"):
                    if texto == "/pausa":
                        pausa.set()
                        print("Avisos suspendidos; aparecerás inactivo después de 15 segundos.")
                    else:
                        pausa.clear()
                        print("Avisos reanudados; el siguiente llegará en menos de 5 segundos.")
                    continue
                if texto.startswith("/canal "):
                    candidato = texto.split(maxsplit=1)[1].lstrip("#")
                    if candidato not in CANALES:
                        print("Canal inexistente")
                    else:
                        canal = candidato
                        print(f"Escribirás en #{canal}. Usa /unir {canal} si aún no eres miembro.")
                    continue
                try:
                    enviar_mensaje(conexion, json.dumps(crear_pedido(texto, canal), ensure_ascii=False))
                except ValueError as error:
                    print(error)
        finally:
            detener.set()
            hilo_udp.join(timeout=1)


def ejecutar() -> None:
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nCliente terminado")
    except (OSError, ValueError, RecursionError) as error:
        print(f"No se pudo continuar: {error}")


if __name__ == "__main__":
    ejecutar()
