"""Modelo inmutable. Convertir datos no lee el reloj ni realiza E/S."""
import json
from datetime import datetime
from typing import NamedTuple, cast


class Mensaje(NamedTuple):
    tipo: str
    emisor: str
    canal: str | None
    destino: str | None
    contenido: str
    timestamp: datetime

    def a_dict(self) -> dict[str, object]:
        return {"tipo": self.tipo, "emisor": self.emisor, "canal": self.canal,
                "destino": self.destino, "contenido": self.contenido,
                "timestamp": self.timestamp.isoformat(timespec="seconds")}

    def a_json(self) -> str:
        return json.dumps(self.a_dict(), ensure_ascii=False)

    @staticmethod
    def desde_json(linea: str) -> "Mensaje | None":
        try:
            datos = cast(object, json.loads(linea))
            if not isinstance(datos, dict):
                return None
            tipo, emisor = datos.get("tipo"), datos.get("emisor")
            canal = datos.get("canal", "general" if tipo == "mensaje" else None)
            destino = datos.get("destino")
            contenido, fecha = datos.get("contenido"), datos.get("timestamp")
            if not all(isinstance(x, str) for x in (tipo, emisor, contenido, fecha)):
                return None
            if not isinstance(tipo, str) or not isinstance(emisor, str) or not isinstance(contenido, str) or not isinstance(fecha, str):
                return None
            if canal is not None and not isinstance(canal, str):
                return None
            if destino is not None and not isinstance(destino, str):
                return None
            if not emisor.strip() or not contenido.strip() or len(emisor) > 40 or len(contenido) > 4000:
                return None
            emisor.encode("utf-8")
            contenido.encode("utf-8")
            if tipo == "mensaje" and (not canal or destino is not None):
                return None
            if tipo == "privado" and (not destino or canal is not None):
                return None
            return Mensaje(tipo, emisor, canal, destino, contenido, datetime.fromisoformat(fecha))
        except (ValueError, TypeError, KeyError, RecursionError):
            return None
