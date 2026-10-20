# Proyecto final: mensajería del centro de distribución

Implementación sobre el parcial anterior. Python 3.10 o superior; aplicación y pruebas usan solo biblioteca estándar. mypy es una herramienta opcional de desarrollo que el enunciado exige para revisar los tipos.

## 1. Ejecutar

Abre PowerShell dentro de esta carpeta (en el Explorador puedes escribir powershell en la barra de dirección).

Primera terminal:

```powershell
python servidor_json.py
```

Abre otras tres terminales en la misma carpeta. Ejecuta una línea en cada terminal:

```powershell
python cliente_json.py Ana
python cliente_json.py Beto
python cliente_json.py Carla
```

El servidor usa TCP 8000 y UDP 8001 en 127.0.0.1. Deja abierta su terminal mientras usas los clientes. Termina cada cliente con /fin y el servidor con Ctrl+C.

## 2. Comandos

| Entrada | Resultado |
| --- | --- |
| Un texto normal | Lo envía al canal seleccionado, inicialmente #general |
| /unir despacho | Se une a #despacho |
| /canal despacho | Selecciona #despacho para escribir; debe haberse unido antes |
| /salir despacho | Abandona #despacho |
| /canal general | Vuelve a escribir en #general |
| /privado Beto texto | Solo Beto recibe ese mensaje |
| /usuarios | Muestra conectados, estado, última actividad UTC y canales |
| /canales | Lista los cuatro canales disponibles |
| /pausa | Suspende los avisos de actividad para demostrar el estado inactivo |
| /activo | Reanuda los avisos de actividad |
| /ayuda | Muestra los comandos |
| /fin o 0 | Cierra el cliente |

Los canales fijos son general, recepcion, alistamiento y despacho. Todos permanecen en general. Seleccionar un canal no equivale a unirse: son acciones separadas. Los nombres de usuario no admiten espacios, tienen hasta 40 caracteres y distinguen mayúsculas.

## 3. Bitácora y reporte

El servidor crea automáticamente datos/bitacora.jsonl. Cada mensaje aceptado, incluyendo los privados, se guarda como un objeto JSON en una línea. El servidor asigna emisor y timestamp UTC. Ejecuta flush y fsync antes de entregar o confirmar el mensaje. Si falla el guardado, lo rechaza.

La confirmación significa que el mensaje quedó guardado. Los destinatarios se atienden mediante colas independientes; no se confirma que hayan leído el mensaje ni se recuperan entregas históricas al reconectarse. La administración del servidor tiene acceso a la bitácora, incluidos los privados.

Para ver el reporte:

```powershell
python reporte.py
```

Para guardarlo:

```powershell
python reporte.py --salida datos/reporte.txt
```

Para analizar otra bitácora:

```powershell
python reporte.py ruta/al/archivo.jsonl --salida datos/reporte.txt
```

Cuenta mensajes por persona, por cada una de las 24 horas y las 20 palabras más frecuentes. Cuenta palabras completas sin distinguir mayúsculas; incluye artículos y preposiciones. Por defecto agrupa las horas en UTC-5 (Colombia); --desfase permite cambiarlo. Incluye mensajes generales, por área y privados, y omite líneas dañadas o sin los campos válidos. Un generador lee una entrada a la vez; map y funciones puras transforman los registros. Los conteos exactos se acumulan en una base SQLite temporal en disco y su caché está limitada a 2 MiB. La base temporal se elimina al finalizar normalmente. Requiere permiso de escritura en la carpeta de la bitácora.

## 4. Demostración sugerida

1. Conecta Ana, Beto y Carla. Intenta conectar otra Ana: debe rechazar el nombre repetido.
2. Desde Ana envía un mensaje general: Beto y Carla lo reciben; Ana ve la confirmación.
3. Ana y Beto ejecutan /unir despacho y /canal despacho. Un mensaje de Ana solo llega a Beto. Carla sigue en general.
4. Desde Ana usa /privado Carla revisar pedido. Solo Carla recibe el contenido.
5. En Beto ejecuta /pausa. Espera más de 15 segundos y consulta /usuarios desde Ana: Beto aparece inactivo. Beto ejecuta /activo; dentro de cinco segundos vuelve a aparecer activo.
6. Cierra Carla. El resto puede seguir enviando mensajes. Consulta /usuarios para ver que Carla ya no está conectada.
7. Detén y reinicia el servidor. La bitácora conserva lo guardado. Los clientes deben reconectarse: las sesiones y pertenencias a canales se mantienen solo en memoria.
8. Ejecuta python reporte.py para ver los datos de la operación.

## 5. Estructura y relación con el parcial

| Archivo | Responsabilidad |
| --- | --- |
| servidor_json.py | Punto de entrada que conserva el nombre acordado |
| cliente_json.py | Punto de entrada del cliente final |
| reporte.py | Punto de entrada del reporte |
| mensajeria/protocolo.py | Prefijo de longitud de 4 bytes, UTF-8, lectura completa y límite de 65536 bytes por trama |
| mensajeria/registro.py | Registro sincronizado, canales, sesiones, colas de salida y actividad |
| mensajeria/bitacora.py | Escritura persistente y sincronizada de JSONL |
| mensajeria/servidor_json.py | Validación, distribución, recepción UDP y atención por hilos |
| mensajeria/cliente_json.py | Comandos, recepción y avisos UDP cada cinco segundos |
| mensajeria/reporte.py | Generadores, transformaciones puras y agregación exacta en disco |
| pruebas/test_proyecto.py | Pruebas automáticas de requisitos |
| pruebas/probar_volumen.py | Prueba reproducible con 100000 mensajes |
| servidor.py y cliente.py | Versión de texto del parcial, conservada como referencia |
| protocolo.py y registro.py | Reexportan la implementación del paquete para conservar importaciones anteriores |
| respaldo/ | Copias previas a los cambios |

La implementación final usa JSON también para el saludo inicial. Debes emparejar cliente_json.py con servidor_json.py. El cliente de texto del parcial se empareja con servidor.py y no ofrece las funciones del proyecto final.

También puedes usar python -m mensajeria.servidor_json, python -m mensajeria.cliente_json Ana y python -m mensajeria.reporte desde esta carpeta.

## 6. Protocolo

TCP: cuatro bytes de longitud unsigned big-endian seguidos del cuerpo UTF-8. Cada cuerpo del proyecto final es un objeto JSON. Registro: {"tipo":"registro","nombre":"Ana"}. La respuesta incluye nombre, canales y un token aleatorio de sesión. Un mensaje: {"tipo":"mensaje","canal":"general","contenido":"pedido listo"}. Un privado: {"tipo":"privado","destino":"Beto","contenido":"revisar pedido"}. El servidor ignora cualquier emisor o timestamp enviado por el cliente y genera los suyos.

UDP 8001: un objeto JSON por datagrama: {"tipo":"actividad","nombre":"Ana","token":"token recibido al registrarse"}. Se valida el token y la IP de la sesión TCP. No se utiliza prefijo TCP en un datagrama UDP, porque el datagrama ya conserva su longitud. Las entradas inválidas se descartan. La actividad se mide con reloj monotónico; la fecha visible se guarda en UTC.

## 7. Pruebas y revisión de tipos

```powershell
python -m unittest discover -s pruebas -v
python pruebas/probar_volumen.py
```

Las pruebas usan puertos libres y bitácoras temporales; no modifican la bitácora de operación. La suite espera algo más de 15 segundos para probar la inactividad real. La prueba de volumen tarda más y crea temporalmente 100000 registros con autores y vocabulario distintos.

En el equipo de desarrollo:

```powershell
python -m pip install mypy
python -m mypy --python-version 3.10 mensajeria
```

No hay que instalar mypy ni ningún paquete adicional en las estaciones para ejecutar el sistema. La implementación fue ejecutada con Python 3.14 y comprobada por mypy con objetivo Python 3.10; no se ejecutó un intérprete 3.10 durante esta revisión.

## 8. Uso en la red local

Para desarrollo usa los valores predeterminados. En una LAN, el servidor puede escuchar con python servidor_json.py --host 0.0.0.0. Los clientes deben indicar la IP privada real del servidor: python cliente_json.py Ana --host IP_DEL_SERVIDOR. El firewall debe permitir TCP 8000 y UDP 8001. No hay servicios de nube ni dependencia de internet en ejecución. Si cambias puertos, indica el mismo puerto TCP posicional y --udp en servidor y clientes.

## 9. Alcance

El nombre identifica la sesión, sin contraseña. El token de actividad vincula los avisos UDP a esa sesión; no reemplaza un sistema de autenticación. El programa está pensado para la red interna indicada en el enunciado. La bitácora es persistente y legible; no implementa firmas criptográficas ni protección contra modificaciones por parte de quien administra el disco. Ejecuta una sola instancia del servidor sobre cada archivo de bitácora.
