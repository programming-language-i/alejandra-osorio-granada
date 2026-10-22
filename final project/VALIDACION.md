# Validación de persistencia funcional · 21 de octubre de 2026

- prueba_persistencia.py: asserts puros correctos; escritor independiente correcto; dos clientes, 10 mensajes, unión y error producen exactamente 10 líneas tras el cierre ordenado.
- python -m unittest discover -s pruebas -v: 10 pruebas correctas (18,32 segundos).
- python -m mypy --python-version 3.10 --strict mensajeria: sin errores en 14 archivos fuente.
- Prueba escalable: 100000 mensajes, 100000 autores distintos, 100002 palabras distintas; conteos correctos en 17,8 segundos. Pico Python medido: 294639 bytes con 1000 mensajes y 290122 con 100000. SQLite utiliza caché acotada y almacenamiento temporal en disco; tracemalloc no mide toda la memoria nativa.

Se mantuvieron las pruebas de concurrencia, aislamiento de canales y privados, UDP, entradas inválidas, persistencia tras reinicio y reversión ante fallo de fsync. Los registros anteriores siguen admitidos. La ruta predeterminada es ahora datos/mensajes.log.

El reporte funcional usa contadores en RAM según categorías distintas, sin acumular mensajes. Para memoria acotada aun con vocabulario creciente se conserva --escalable. La tabla de responsables del README debe completarla el equipo.

Entorno de ejecución Python 3.14; objetivo de tipos Python 3.10. No se probó en una LAN física.
