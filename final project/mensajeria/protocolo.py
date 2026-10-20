"""Framing del parcial: cuatro bytes de longitud big-endian y cuerpo UTF-8."""
import socket
import struct

MAX_TRAMA = 65536


def recibir_exacto(sock: socket.socket, n: int) -> bytes | None:
    """Acumula fragmentos; devuelve None si la conexión termina antes."""
    if n < 0 or n > MAX_TRAMA:
        raise ValueError("Longitud fuera del límite permitido")
    buffer = bytearray()
    while len(buffer) < n:
        chunk = sock.recv(n - len(buffer))
        if not chunk:
            return None
        buffer.extend(chunk)
    return bytes(buffer)


def enviar_mensaje(sock: socket.socket, texto: str) -> None:
    cuerpo = texto.encode("utf-8")
    if len(cuerpo) > MAX_TRAMA:
        raise ValueError("La trama supera el máximo de 65536 bytes")
    sock.sendall(struct.pack("!I", len(cuerpo)) + cuerpo)


def recibir_mensaje(sock: socket.socket) -> str | None:
    prefijo = recibir_exacto(sock, 4)
    if prefijo is None:
        return None
    longitud = struct.unpack("!I", prefijo)[0]
    if longitud > MAX_TRAMA:
        raise ValueError("La trama supera el máximo de 65536 bytes")
    cuerpo = recibir_exacto(sock, longitud)
    return None if cuerpo is None else cuerpo.decode("utf-8")
