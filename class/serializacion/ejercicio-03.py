import json

mensaje = {
    "emisor": "felipe",
    "contenido": "hola felipe llegaste tarde",
    "etiquetas": ("a","b")
}

texto = json.dumps(mensaje,ensure_ascii=False)

print(texto)

copia = json.loads(texto)
print(f"Texto cargado: {copia}")

print("\n")

print(f"Son iguales: {mensaje == copia}")


