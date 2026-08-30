# Decisiones del dataset

- Baseline: 1.000.000 de filas en `baseline.csv`.
- Incidentes desde el front: 10.000 filas por defecto en `transactions.csv`.
- Período: 2026-08-22 00:00:00 a 2026-08-29 23:59:59.
- Semilla: 42.
- `value`: monto equivalente en USD.
- `value_transaction_currency`: monto en moneda local.

## Comercios

| merchant_id | Comercio | Volumen | Multiplicador de gasto |
|---:|---|---:|---:|
| 1 | Walmart | 60% | 0.90 |
| 2 | Cencosud | 40% | 1.15 |

Distribución de país condicionada por comercio:

| Comercio | Mexico | Chile | Argentina | Brasil |
|---|---:|---:|---:|---:|
| Walmart | 70% | 30% | 0% | 0% |
| Cencosud | 0% | 40% | 35% | 25% |

## Países y conversión fija

| País | Moneda | Moneda local por USD |
|---|---|---:|
| Chile | CLP | 950 |
| Argentina | ARS | 1300 |
| Mexico | MXN | 19 |
| Brasil | BRL | 5.5 |

## Gasto por país

`value` usa una distribución normal truncada en los límites indicados. La media y el desvío del país se multiplican por el multiplicador del comercio.

| País | Media USD | Desvío USD | Mínimo | Máximo |
|---|---:|---:|---:|---:|
| Argentina | 25 | 12 | 2 | 100 |
| Brasil | 45 | 22 | 3 | 180 |
| Chile | 60 | 30 | 4 | 250 |
| Mexico | 70 | 35 | 5 | 300 |

## Volumen por día y hora

Pesos por día: lunes=0.85, martes=0.90, miércoles=0.95, jueves=1.00, viernes=1.20, sábado=1.35 y domingo=1.10.

Pesos horarios de 00 a 23:

`[0.25, 0.15, 0.10, 0.08, 0.07, 0.08, 0.15, 0.30, 0.55, 0.80, 1.00, 1.15, 1.25, 1.20, 1.05, 1.00, 1.10, 1.25, 1.45, 1.60, 1.70, 1.45, 0.90, 0.50]`

El mínimo es a las 04:00 y el pico a las 20:00. Los minutos y segundos son uniformes.

## Proveedores y métodos

IDs de proveedor: MercadoPago=1, dLocal=2, PayU=3, Stripe=4, Adyen=5.

IDs de método: credit_card=1, debit_card=2, wallet=3, bank_transfer=4, cash_in_store=5, pix=6, boleto=7.

- Chile: MercadoPago, dLocal, PayU. Tarjetas y wallet.
- Argentina: MercadoPago, dLocal, PayU. Tarjetas, wallet y efectivo.
- Mexico: MercadoPago, dLocal, PayU, Stripe. Tarjetas, wallet, SPEI y efectivo.
- Brasil: MercadoPago, dLocal, PayU, Adyen, Stripe. Tarjetas, wallet, PIX y boleto.
- Los proveedores y sus métodos tienen distribución uniforme.
- `issuing_bank` es `N/A` para wallet, efectivo y boleto.

## Bancos

- Chile: Banco de Chile, Santander Chile, BancoEstado, BCI, Scotiabank Chile.
- Argentina: Banco Nación, Banco Galicia, Santander Argentina, BBVA Argentina, Banco Macro.
- Mexico: BBVA México, Banorte, Santander México, Citibanamex, HSBC México.
- Brasil: Itaú Unibanco, Bradesco, Banco do Brasil, Caixa Econômica Federal, Nubank.

## Rechazos

### Qué mide la columna

El dataset modela **tasa de aprobación de intentos de pago**, no conversión completa del checkout. Adyen distingue explícitamente autorización (respuesta del adquirente/emisor) de conversión de oferta (incluye que el comprador complete el flujo). Aquí `approval_rate = 1 - decline_rate`; por ejemplo, 17% de rechazo implica 83% de aprobación. [Definición de Adyen](https://help.adyen.com/en_US/knowledge/payment-methods/manage-payment-methods/what-is-the-difference-between-authorization-and-conversion-rates).

### Evidencia y criterio de calibración

- Mercado Pago considera saludable para e-commerce una aprobación de 85% a 95%, pero aclara que depende del segmento, ticket y método. Eso es un rango general, no una tasa pública propia. [Mercado Pago](https://www.mercadopago.com.br/blog/metricas-pagamento-melhorar-atendimento).
- Visa encontró aproximadamente 20% de rechazos en pagos *card-not-present* en varios mercados latinoamericanos, frente a 3% con tarjeta presente. [Visa LAC](https://caribbean.visa.com/partner-with-us/visa-performance-solutions/improving-the-credit-authorization-customer-experience.html).
- Una recopilación regional de 2022 basada en Visa y CONDUSEF situó la aprobación CNP en Chile=85%, Argentina=78%, Brasil=77% y México=65%. [Kushki, Tendencias de pagos 2024](https://downloads.ctfassets.net/md4qn0za9whk/1ot6jtAmW4g0dp5l4UiBS5/4fcd3c9649152bee08b9123f48b1bde6/Ebook_-_Payment_Trends_in_2024__1_.pdf).
- Para México existe evidencia oficial más reciente: Banco de México reportó 70,44% de aceptación e-commerce en 4T-2025 y 69,75% en 1T-2026. [SIE de Banco de México, cuadro CF621](https://www.banxico.org.mx/SieInternet/consultarDirectorioInternetAction.do?accion=consultarCuadro&idCuadro=CF621&locale=es&sector=21).
- No hay una publicación pública comparable que permita afirmar una tasa absoluta homogénea para MercadoPago, dLocal, PayU, Stripe y Adyen. Sus publicaciones muestran resultados no comparables: dLocal anuncia casos de hasta 98,4% en tarjetas y 97% en Pix; PayU indica que multi-adquirencia puede sumar hasta 5 puntos; Stripe publica un caso mexicano con 10% de mejora; Adyen publica mejoras de 2 puntos para Globo. Son *casos/uplifts*, no benchmarks generales. [dLocal](https://www.dlocal.com/our-solution/payins/), [PayU](https://developers.payulatam.com/latam/en/), [Stripe](https://stripe.com/en-mx/customers/ben-and-frank), [Adyen](https://www.adyen.com/pt_BR/centro-de-conhecimento/por-que-as-principais-marcas-escolhem-adyen).

Por eso las tasas por proveedor son una **calibración sintética**, centrada en los benchmarks regionales y con una ventaja pequeña para proveedores/local acquiring; no se presentan como KPIs reales de esas empresas.

La probabilidad normal es: tasa base del proveedor + ajustes de comercio, país, método y banco emisor.

| Proveedor | Rechazo base | Aprobación base implícita |
|---|---:|---:|
| MercadoPago | 17% | 83% |
| dLocal | 15% | 85% |
| PayU | 18% | 82% |
| Stripe | 18% | 82% |
| Adyen | 16% | 84% |

La tasa base es el punto de partida neutral, no el resultado agregado del proveedor. La cobertura de países y métodos cambia el valor observado. En el `baseline.csv` regenerado con 1.000.000 de filas y semilla 42 se obtuvo:

| Proveedor | Filas | Rechazo observado | Aprobación observada |
|---|---:|---:|---:|
| MercadoPago | 284.835 | 18,39% | 81,61% |
| dLocal | 285.890 | 18,15% | 81,85% |
| PayU | 284.139 | 21,43% | 78,57% |
| Stripe | 125.311 | 26,37% | 73,63% |
| Adyen | 19.825 | 18,91% | 81,09% |

- Comercio: Walmart=-0,2 puntos; Cencosud=+0,2 puntos.
- País: Chile=-2; Argentina=+4; Mexico=+12; Brasil=+5 puntos. La diferencia grande de México es intencional y se apoya en el dato oficial de aceptación e-commerce cercano a 70%.
- Método: credit_card=-3; debit_card=+1; wallet=-8; bank_transfer=-7; cash_in_store=+3; pix=-13; boleto=+5 puntos. Pix y wallet quedan por encima de tarjetas; dLocal publica hasta 97% de conversión para Pix y Mercado Pago indica que los pagos con saldo tienen aprobación significativamente superior.

Resultado observado por país en el mismo baseline: Chile=87,13%, Argentina=79,40%, Brasil=79,96% y México=73,99% de aprobación. México queda algo por encima del agregado oficial de tarjetas porque el dataset también incluye wallet, transferencia y efectivo, y sólo contiene cinco emisores seleccionados.

### Bancos emisores

México es el único país del dataset para el que se encontró una publicación oficial, reciente y comparable por emisor y por tipo de tarjeta. Se usan los porcentajes reportados por CONDUSEF/Banco de México para 4T-2025:

| Banco de México | Aprobación crédito publicada | Ajuste de rechazo crédito | Aprobación débito publicada | Ajuste de rechazo débito |
|---|---:|---:|---:|---:|
| BBVA México | 80,82% | -7,22 pp | 72,92% | -3,69 pp |
| Citibanamex | 79,60% | -6,00 pp | 77,97% | -8,74 pp |
| Banorte | 45,52% | +28,08 pp | 62,75% | +6,48 pp |
| Santander México | 63,45% | +10,15 pp | 65,85% | +3,38 pp |
| HSBC México | 56,97% | +16,63 pp | 59,39% | +9,84 pp |

Fuentes: [CONDUSEF crédito 4T-2025](https://www.condusef.gob.mx/documentos/comercio/TC-4to-Trim-2025.pdf) y [CONDUSEF débito 4T-2025](https://www.condusef.gob.mx/documentos/comercio/TD-4to-Trim-2025.pdf). Los ajustes son la diferencia respecto del promedio mexicano publicado para cada método. Además, la selección del emisor mexicano deja de ser uniforme y usa la cantidad de solicitudes de esos informes: crédito BBVA=61,63%, Citibanamex=19,80%, Banorte=8,51%, Santander=6,39%, HSBC=3,67%; débito BBVA=65,39%, Citibanamex=13,48%, Santander=9,34%, Banorte=8,04%, HSBC=3,75%.

La auditoría del baseline reprodujo el perfil de esos emisores: crédito BBVA=81,55%, Citibanamex=79,69%, Banorte=46,53%, Santander=63,97%, HSBC=55,52%; débito BBVA=74,07%, Citibanamex=78,29%, Banorte=63,81%, Santander=67,04%, HSBC=59,30%. Las pequeñas diferencias frente a la fuente se deben a los ajustes adicionales de proveedor/comercio y al muestreo.

Para Chile, Argentina y Brasil no se encontró una serie pública equivalente por banco emisor. Para mantener la dimensión diagnóstica sin inventar una supuesta medición, se usan offsets sintéticos pequeños, balanceados alrededor de cero:

| País | Ajustes sintéticos de rechazo por banco |
|---|---|
| Chile | Banco de Chile=-1 pp; Santander=-0,5; BCI=0; Scotiabank=+0,5; BancoEstado=+1 |
| Argentina | BBVA=-1 pp; Galicia=-0,5; Santander=0; Macro=+0,5; Nación=+1 |
| Brasil | Itaú=-1 pp; Nubank=-0,5; Bradesco=0; Banco do Brasil=+0,5; Caixa=+1 |

En métodos mexicanos no cubiertos por los informes de tarjetas se usan offsets sintéticos: BBVA=-1 pp, Citibanamex=-0,5, HSBC=0, Santander=+0,5 y Banorte=+1. `N/A` usa 0. Estas diferencias son parámetros de simulación y **no un ranking real de bancos**.

`decline_code = 0` significa aprobación. Códigos de rechazo ISO-8583 usados:

| Código | Significado | Peso entre rechazos |
|---:|---|---:|
| 5 | Do not honor | 15% |
| 14 | Invalid card/account number | 3% |
| 51 | Insufficient funds | 40% |
| 54 | Expired card | 5% |
| 57 | Transaction not permitted | 7% |
| 59 | Suspected fraud | 15% |
| 61 | Exceeds approval amount limit | 10% |
| 91 | Issuer or switch unavailable | 3% |
| 96 | System malfunction | 2% |

La distribución es sintética y está informada por referencias de ISO-8583 y redes de tarjetas; no representa un benchmark universal. En el front se muestra `05`, pero se almacena `5` porque `decline_code` es numérico.

## Front de probabilidades

- Los parámetros del generador están centralizados en `generation_config.py`.
- La vista principal está agrupada por proveedor y permite editar su tasa base.
- Las reglas pueden filtrar opcionalmente comercio, país, método y banco emisor.
- Cada regla requiere un código de rechazo ISO-8583 y un incremento positivo en puntos porcentuales, que puede ser tan bajo como `0,01%` desde el front.
- `Any` funciona como comodín. La regla más específica gana; ante empate gana la más nueva.
- Una regla suma su incremento al baseline natural sólo para las transacciones que coinciden. Los rechazos normales conservan su probabilidad y distribución; el incremento usa exclusivamente el código seleccionado. Por eso la participación relativa de todos los demás códigos baja proporcionalmente.
- El front permite elegir entre 1 y 1.000.000 de filas y el nombre del CSV.
- El front permite elegir las fechas y horas inicial y final con precisión de segundos.
- El nombre predeterminado es `transactions.csv`; `baseline.csv` está reservado para evitar sobrescribirlo.
- `python scripts/ingestion/generator/generate_baseline.py`, ejecutado desde la raíz del proyecto, regenera `scripts/ingestion/generator/baseline.csv` con 1.000.000 de filas y tasas base.
