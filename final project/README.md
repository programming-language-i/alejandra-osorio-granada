# Chat del centro de distribución: persistencia funcional

Actualización del 21 de octubre de 2026, adaptada a preguia_taller.md y guia_funcional.md. Se conservan el chat, canales, privados, actividad UDP y el reporte escalable; se separan los efectos de las transformaciones puras.

## Ejecutar el chat

En una terminal dentro de esta carpeta:

```powershell
python servidor_json.py
```

En otras dos terminales, una línea en cada una:

```powershell
python cliente_json.py Ana
python cliente_json.py Beto
```

El servidor escucha por defecto en localhost, TCP 8000 y UDP 8001. Python 3.10 o superior y solo biblioteca estándar para ejecutar. El programa se verificó con Python 3.14 y mypy con objetivo Python 3.10.

Comandos: texto normal para #general; /unir despacho; /canal despacho; /salir despacho; /privado Beto texto; /usuarios; /canales; /pausa; /activo; /ayuda; /fin. También existen recepcion y alistamiento. Todos permanecen en general. /canal selecciona dónde escribir; /unir establece la pertenencia. /pausa suspende avisos UDP y permite demostrar inactividad tras más de 15 segundos; /activo los reanuda en hasta cinco segundos.

## Qué cambió con el taller

- Mensaje es un NamedTuple inmutable; a_json y desde_json son puras.
- conexion.crear_mensaje asigna emisor y timestamp UTC una sola vez. El reloj queda fuera de la serialización.
- persistencia.se_guarda acepta exclusivamente mensaje y privado.
- persistencia.escribir recibe serializador y predicado como funciones; es el único borde que abre el log para escribir.
- Bitacora es una fachada compatible: serializa antes de encolar y espera la confirmación del escritor. Solo hay un hilo escritor no daemon, y una cola acotada.
- Al detener el servidor con Ctrl+C se cierran las conexiones y se espera a los productores; después se envía None y se hace join del escritor. Los mensajes confirmados ya pasaron flush y fsync. Ante un fallo de escritura se intenta revertir el registro parcial; si eso falla se bloquean las escrituras posteriores.
- analisis.lectura transforma líneas con map y filter. Solo leer_mensajes abre el archivo para lectura.
- analisis.metricas contiene consultas puras, sin abrir archivos ni imprimir.
- analisis.reporte llama a lectura y métricas, e imprime sus resultados. No calcula métricas.

Los efectos de red, pantalla y disponibilidad del chat siguen en sus respectivos bordes. La separación del taller corresponde al flujo de persistencia y análisis; no convierte toda la aplicación en funciones puras.

## Paso 0: tabla de efectos

Antes, Bitacora.guardar serializaba y escribía desde el hilo de cada cliente, protegido por un lock. Ahora la escritura queda en un único escritor y las transformaciones se prueban por separado.

| Módulo | Función | ¿Archivo, red, pantalla, reloj o estado? | ¿Pura? |
| --- | --- | --- | --- |
| mensajeria/mensaje.py | Mensaje.a_json, a_dict y desde_json | Ninguno | Sí |
| mensajeria/conexion.py | crear_mensaje | Reloj; asigna autor de sesión y hora | No: borde |
| mensajeria/persistencia.py | a_linea y se_guarda | Ninguno | Sí |
| mensajeria/persistencia.py | escribir | Cola, archivo, flush y fsync | No: borde de escritura |
| mensajeria/bitacora.py | guardar y cerrar | Cola, eventos, hilo y sincronización | No: coordinación |
| mensajeria/bitacora.py | serializar_solicitud y guardar_solicitud | Solo leen datos recibidos | Sí |
| mensajeria/bitacora.py | confirmar_solicitud | Actualiza el resultado y despierta al productor | No |
| mensajeria/analisis/lectura.py | desde_linea y registros | Ninguno; procesan las líneas recibidas | Sí |
| mensajeria/analisis/lectura.py | leer_mensajes | Archivo | No: borde de lectura |
| mensajeria/analisis/metricas.py | top_emisores, mensajes_por_hora, palabras_frecuentes, es_de, de_emisor | Ninguno | Sí |
| mensajeria/analisis/reporte.py | reporte y main | Orquestación, lectura y salida | No: borde de presentación |
| mensajeria/registro.py | actividad, listar | Reloj y estado de sesiones | No: disponibilidad |
| mensajeria/servidor_json.py | atender, responder, recibir_actividad | Red y estado | No: bordes de red |

## Relación con lo visto en clase

Su ejemplo obtiene pares mediante filter(es_par, numeros). En el proyecto:

```python
map(desde_linea, lineas)                 # transforma texto en Registro o None
filter(None, map(desde_linea, lineas))   # conserva únicamente registros válidos
```

Igual que map(lambda x: x * 2, numeros), una métrica transforma cada registro:

```python
map(lambda registro: registro.timestamp.hour, registros)
```

Counter cuenta esas horas. top_emisores usa map con attrgetter("emisor"). palabras_frecuentes aplana contenidos mediante una expresión generadora y cuenta palabras en minúsculas, sin puntuación. de_emisor combina filter y partial para fijar el emisor en un predicado.

Una lambda es una forma breve de escribir una función, no una garantía de pureza. Las funciones usadas aquí no leen el reloj, no imprimen y no modifican los argumentos.

map y filter son perezosos: un flujo se consume una sola vez. Para probar repetibilidad se utiliza una tupla pequeña y fija. Para leer el log completo no se usa list ni tuple.

## Formato y compatibilidad

Ruta predeterminada nueva: datos/mensajes.log. Es JSON Lines UTF-8, un objeto por línea. Conserva tipo, emisor, canal, destino, contenido y timestamp ISO. canal o destino vale null según corresponda. Los saltos de línea del contenido se escapan dentro del JSON y no crean registros adicionales. El timestamp se genera en UTC; desde_linea lo convierte en datetime sin consultar el reloj.

Solo se guardan mensaje y privado. unirse, dejar, unir, salir, respuestas de error y registro de conexión no producen líneas en el log. El servidor acepta unirse/dejar como equivalentes a unir/salir.

Los registros anteriores que omiten destino o canal se leen con campos opcionales; un mensaje antiguo sin campo canal se interpreta como general. Las líneas dañadas, los tipos no persistentes y las líneas con campos inválidos devuelven None y se descartan sin imprimir.

La ruta anterior datos/bitacora.jsonl no se borra ni se renombra automáticamente. Si tienes una bitácora previa, puedes seguir utilizándola con --bitacora datos/bitacora.jsonl en el servidor y pasándola como ruta al reporte. Se mantiene la opción --bitacora para rutas personalizadas. El administrador del disco puede leer los privados de la bitácora.

El saludo de red sigue siendo JSON: {"tipo":"registro","nombre":"Ana"}. El servidor genera un token de sesión que el cliente incluye en cada aviso UDP; también se comprueba la IP. La confirmación de un mensaje significa persistencia, no lectura por sus destinatarios. No hay reenvío histórico al reconectarse. Para usar la versión de texto del parcial se conservan servidor.py y cliente.py, que deben usarse juntos.

## Métricas y reporte

Reporte funcional del taller:

```powershell
python reporte.py
python reporte.py --salida datos/reporte.txt
python -m mensajeria.analisis.reporte
```

Este borde llama a las tres métricas puras. Reabre el log para cada métrica, sin materializar los mensajes; genera el reporte después de detener el servidor para analizar un archivo estable. Las horas son las de cada timestamp, UTC para los mensajes generados por este servidor. Los contadores ocupan memoria según autores y palabras distintos; no guardan cada mensaje.

Se conserva el modo de agregación exacta en disco para garantizar memoria acotada incluso con vocabulario y autores crecientes:

```powershell
python reporte.py --escalable --salida datos/reporte_completo.txt
python reporte.py --escalable datos/bitacora.jsonl
```

Este modo reutiliza leer_mensajes, acumula en SQLite temporal con caché de 2 MiB y mantiene las horas UTC-5 por defecto (opción --desfase para cambiarlo). No requiere instalar SQLite: viene en la biblioteca estándar. El componente SQLite es un borde con efectos, no una métrica pura. Ambos reportes cuentan privados y mensajes de canal, e incluyen artículos y preposiciones entre las palabras.

## Pruebas solicitadas por la guía

```powershell
python prueba_persistencia.py --puras
python prueba_persistencia.py
python -m unittest discover -s pruebas -v
python pruebas/probar_volumen.py
```

--puras verifica con asserts ida/vuelta, determinismo de las métricas sobre una tupla, ausencia de mutaciones, líneas dañadas, filtros y predicados; bloquea los intentos de abrir archivos o imprimir durante esas comprobaciones. No inicia servidor, archivos ni hilos en esa parte.

La prueba completa añade el escritor con archivo temporal, centinela y join, y un servidor con dos clientes que envían 10 mensajes, una unión y provocan un error: al cierre deben existir exactamente 10 líneas. Las pruebas usan rutas temporales y puertos libres, sin tocar el log de operación.

Comprobación de tipos en desarrollo:

```powershell
python -m pip install mypy
python -m mypy --python-version 3.10 --strict mensajeria
```

No se utilizan anotaciones Any ni exclusiones de tipos para silenciar errores. mypy no es una dependencia de ejecución.

## Responsables del equipo

Completar los nombres reales antes de entregar; no se asignaron personas sin conocer la distribución acordada por el equipo.

| Paso | Evidencia | Responsable |
| --- | --- | --- |
| 0 | Tabla de efectos de este README | Por asignar |
| 1 | Mensaje.a_json | Por asignar |
| 2 | Registro y desde_linea | Por asignar |
| 3 | TIPOS_GUARDADOS y se_guarda | Por asignar |
| 4 | escribir, cola y cierre | Por asignar |
| 5 | registros con map/filter | Por asignar |
| 6 | Tres métricas puras | Por asignar |
| 7 | Reporte funcional | Por asignar |
| 8 | prueba_persistencia.py y mypy | Por asignar |

## Red local

Para la LAN, python servidor_json.py --host 0.0.0.0; cada estación utiliza python cliente_json.py Ana --host IP_DEL_SERVIDOR. El firewall debe permitir TCP 8000 y UDP 8001. No depende de internet ni servicios de nube. El nombre identifica la sesión sin contraseña; no se implementó cifrado ni firma criptográfica del archivo. Ejecutar una sola instancia sobre cada log. La validación se realizó en localhost.
