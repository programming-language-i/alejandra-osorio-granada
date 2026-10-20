# Proyecto final: avance sobre el parcial anterior

## Etapa 1: comunicación JSON

Desde una terminal ubicada en esta carpeta:

```powershell
python servidor_json.py
```

Abre tres terminales adicionales en la misma carpeta:

```powershell
python cliente_json.py Ana
python cliente_json.py Beto
python cliente_json.py Carla
```

Ejecuta cada comando de cliente en una terminal distinta.

Escribe texto para enviarlo a los demás. Para enviar un privado: `/privado Beto mensaje de prueba`. Para salir: `/fin` o `0`.

El cliente original `cliente.py` se conserva para usarlo con `servidor.py`. Para el servidor JSON utiliza `cliente_json.py`. El saludo inicial mantiene el protocolo del parcial: nombre y confirmación OK dentro de tramas con longitud; los mensajes posteriores del cliente JSON sí son objetos JSON.

## Qué cambió

- Se creó el paquete mensajeria para resolver las importaciones existentes.
- protocolo.py y registro.py de la carpeta principal reexportan las implementaciones del paquete; así no hay dos implementaciones independientes.
- Se corrigió el punto de entrada __main__ del servidor JSON.
- Se añadió SO_REUSEADDR a ambos servidores.
- Se eliminó la impresión de depuración del protocolo y se limitó cada trama a 65536 bytes.
- Se añadió el cliente JSON para mensajes generales y privados.
- El servidor JSON notifica JSON inválido y limita el contenido a 4000 caracteres.
- Los originales quedaron guardados en respaldo, en una subcarpeta fechada.

## Verificado

Framing fragmentado, caracteres UTF-8, desconexión a mitad de trama, tres clientes simultáneos, rechazo de nombres repetidos, mensaje general, aislamiento de privados, emisor impuesto por el servidor, JSON inválido y continuidad tras desconexión de un cliente.

## Siguientes etapas pendientes

1. Canales general, recepcion, alistamiento y despacho, con unión y salida.
2. Bitácora JSONL persistente antes de aceptar cada mensaje.
3. Estado, última actividad y avisos UDP en el puerto 8001; inactividad después de 15 segundos.
4. Reporte por persona, hora y palabras, con procesamiento de unas 100000 entradas sin cargar la bitácora completa.
5. Revisión de arquitectura, pruebas de estos requisitos y comprobación con mypy.

La versión todavía no cumple todos los requisitos del proyecto final. Esta etapa conserva y hace ejecutable el trabajo del parcial; no copia encima el proyecto independiente generado anteriormente.
