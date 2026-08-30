# Generador de transacciones

Todos los archivos necesarios para ejecutar el generador están bajo `scripts/ingestion/`, junto al flujo que alimentan.

Los parámetros editables están centralizados en [`generation_config.py`](generation_config.py): tasas y offsets de rechazo, distribución de códigos ISO-8583, comercios, países, proveedores, métodos, bancos, gasto, volumen horario, fechas, semilla y cantidad de filas. Las probabilidades usan decimales (`0.17` equivale a `17%`) y los valores `weight` son pesos relativos.

## Archivos del generador

- [`generation_config.py`](generation_config.py): contiene todos los parámetros editables del dataset. Aquí se configuran las fechas y cantidad de filas predeterminadas, monedas y tipos de cambio, distribución de gasto, comercios, países, proveedores, métodos, bancos, pesos de volumen por día y hora, probabilidades de rechazo, offsets y distribución de códigos ISO-8583.
- [`dataset_generator.py`](dataset_generator.py): es el motor de generación. Combina los parámetros, calcula la probabilidad natural de rechazo, aplica la regla de incidente ganadora, genera timestamps y valores monetarios, escribe el CSV y audita su esquema y consistencia.
- [`app.py`](app.py): inicia el servidor HTTP local. Entrega el HTML y los endpoints de configuración, generación y descarga; además valida filas, nombre del archivo, fechas, horas, tasas de proveedor y reglas antes de llamar al motor.
- [`index.html`](index.html): contiene la interfaz Control Tower, sus estilos y la lógica del navegador. Permite elegir cantidad de filas, archivo, fechas, horas, tasas base e incrementos específicos por código ISO-8583.
- [`generate_baseline.py`](generate_baseline.py): ejecuta una generación reproducible de un millón de transacciones con la semilla y el período configurados, y luego audita el resultado.
- [`generate_dataset.ipynb`](generate_dataset.ipynb): ofrece una alternativa interactiva en Jupyter para configurar reglas, generar el dataset y revisar una muestra de la auditoría.
- [`decisiones_dataset.md`](decisiones_dataset.md): documenta las decisiones de modelado, fuentes, supuestos, fórmulas de probabilidades, distribución de códigos y comportamiento de las reglas.
- [`README.md`](README.md): explica la estructura del generador y cómo ejecutar sus dos flujos principales.

Desde la raíz del proyecto, generar el baseline de 1.000.000 de filas:

```bash
python scripts/ingestion/generator/generate_baseline.py
```

Iniciar el front para controlar la ingestión en vivo:

```bash
make ingestion-generator
```

Abrir [http://127.0.0.1:8002](http://127.0.0.1:8002), iniciar o detener el stream y activar una de las dos simulaciones preseleccionadas: un spike global de fallos o uno específico para MercadoPago.

## Ingestión en vivo acelerada

Con PostgreSQL iniciado y configurado en `data/.env`, el mismo front controla la ingestión directamente en la base. Elegí el **promedio de transacciones por minuto**, el inicio simulado y presioná **Start live ingestion**. El generador mantiene su propio reloj: cada segundo real inserta un lote que representa un minuto simulado, y los `issued_timestamp` quedan dentro de ese minuto, no en la hora de pared. Cada hora simulada recibe un perfil normal propio con desvío estándar de 35%, y cada minuto varía 15% alrededor de ese perfil; así los totales horarios no quedan fijos cerca de 6.000. Las tasas y reglas visibles al iniciar se congelan para esa ejecución. **Stop** detiene el stream después del lote en curso.

El toggle **Global failure spike** establece una tasa base de rechazo de 85% para todos los proveedores. **Break MercadoPago** hace lo mismo sólo para MercadoPago. **Break BancoEstado in Chile** agrega reglas de rechazo de 80 puntos porcentuales a las transacciones de BancoEstado en Chile, con código ISO-8583 `51`. Los escenarios son mutuamente excluyentes y se aplican desde el siguiente minuto simulado; al apagar uno, el stream vuelve al perfil normal predeterminado.

El servidor del generador usa el puerto `8002` por defecto para no competir con el Dashboard API (`8000`). Se pueden instalar las dependencias requeridas con:

```bash
pip install -r scripts/ingestion/requirements.txt
```

Tanto `baseline.csv` como los CSV generados desde el front se guardan en `scripts/ingestion/generator/`, independientemente del directorio desde el que se ejecute el comando.
