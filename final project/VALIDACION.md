# Validación del proyecto final

Fecha: 15 de octubre de 2026. Se trabajó en la carpeta del parcial anterior; los originales se conservaron en respaldo/.

## Resultado

- Python de ejecución: 3.14.
- Revisión de tipos para Python 3.10: python -m mypy --python-version 3.10 mensajeria.
- Resultado mypy: Success: no issues found in 7 source files.
- Pruebas: python -m unittest discover -s pruebas -v.
- Resultado: 10 pruebas correctas, aproximadamente 19 segundos.

Las pruebas cubren: tres clientes simultáneos; rechazo de nombres repetidos; autoría impuesta por el servidor; mensajes generales; unión y salida de canales; aislamiento de privados; JSON, Unicode y tipos inválidos; desconexión a mitad de trama; longitud excesiva; envíos concurrentes sin mezcla; inactividad tras 15 segundos; rechazo de avisos UDP con token incorrecto; reactivación válida; persistencia tras reinicio; recuperación de una última línea incompleta; rechazo del mensaje ante fallo de disco; reversión de una escritura cuando falla fsync; framing fragmentado y caracteres UTF-8.

## Prueba de volumen

Comando: python pruebas/probar_volumen.py.

- 100000 mensajes, con 100000 autores y 100002 palabras diferentes.
- Conteos verificados: total, palabras frecuentes y hora local esperada.
- Tiempo con 1000 mensajes: 0,30 segundos.
- Tiempo con 100000 mensajes: 21,12 segundos.
- Pico de memoria Python con 1000 mensajes: 297876 bytes.
- Pico de memoria Python con 100000 mensajes: 297817 bytes.

tracemalloc mide memoria Python, no toda la memoria nativa del proceso. SQLite tiene una caché configurada de 2 MiB y almacena agregaciones y datos temporales en disco. Los tiempos dependen del equipo. Los datos de prueba se generan y eliminan en carpetas temporales separadas de la bitácora de operación.

## Correspondencia con el enunciado

| Requisito funcional | Implementación |
| --- | --- |
| 01 Identidad única | Registro sincronizado y rechazo de nombres repetidos |
| 02 Canal común | general obligatorio para todas las sesiones |
| 03 Concurrencia | Hilo receptor y despachador por sesión, sin máximo fijo de estaciones |
| 04 Tolerancia a fallos | Limpieza por desconexión y colas de salida independientes |
| 05 Registro de conectados | /usuarios: nombre, estado, última actividad y canales |
| 06 Autoría y hora | Emisor de la sesión y timestamp UTC del servidor |
| 07 Bitácora persistente | JSONL con escritura sincronizada antes de confirmar o entregar |
| 08 Disponibilidad | UDP cada 5 segundos; inactivo tras más de 15 segundos sin aviso |
| 09 Reporte | Mensajes por persona, hora y palabras frecuentes |
| 10 Volumen | Lectura por generadores y conteos exactos en SQLite en disco |
| 11 Canales por área | general, recepcion, alistamiento, despacho; unión y salida |
| 12 Privados | Entrega solo al destinatario conectado |

Restricciones técnicas cubiertas: localhost TCP 8000 y UDP 8001 por defecto; biblioteca estándar; JSON y UTF-8; prefijo de longitud para TCP; SO_REUSEADDR; descarte o cierre de la estación con datos inválidos sin detener el servicio; clases separadas y anotaciones de tipos.

La prueba se ejecutó en un solo equipo usando localhost. No se probó en una LAN física ni con un intérprete Python 3.10. Para la sustentación sigue LEEME.md y revisa especialmente el protocolo, los locks, los hilos, la bitácora y los generadores del reporte.
