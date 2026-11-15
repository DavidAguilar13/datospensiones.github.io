# datospensiones

Web estática con la pensión media contributiva por provincia en España, a partir de las
estadísticas mensuales del INSS. Se publica con GitHub Pages:
https://davidaguilar13.github.io/datospensiones.github.io/

## Estructura

| Ruta | Qué es |
|------|--------|
| `index.html` | La web (HTML + JS puro, Leaflet y Chart.js). Carga los datos con `fetch`. |
| `data/pensiones.json` | Datos del último mes: nacional y las 52 provincias, por código INE. |
| `data/provincias.geojson` | Contornos de las provincias (propiedad `cod_prov` = código INE). |
| `data/historico.json` | Serie mensual desde enero de 2010 (nacional y por provincia, por tipo) e IPC del INE. |
| `data/desigualdad.json` | Pensionistas por tramos de cuantía y sexo, Gini aproximado, brecha de género, mínimos. |
| `scripts/inss.py` | Código común: descarga, lectura de los Excel (todos los formatos desde 2010) y validación. |
| `scripts/update_data.py` | Actualización mensual (último mes, histórico, desigualdad). |
| `scripts/build_history.py` | Reconstruye el histórico completo desde 2010. |

## Formato de `data/pensiones.json`

```json
{
  "periodo": "2026-02",
  "fecha_datos": "2026-02-01",
  "fuente": { "nombre": "...", "url": "...", "fichero": "CA202602.xlsx", "hoja": "CA_Total sistema" },
  "nacional": { "total": { "num": 0, "media": 0.0 }, "jub": {}, "ip": {}, "viu": {}, "orf": {}, "fam": {} },
  "provincias": {
    "04": { "nombre": "Almería", "total": { "num": 0, "media": 0.0 }, "...": {} }
  }
}
```

Tipos: `total` (total sistema), `jub` (jubilación), `ip` (incapacidad permanente),
`viu` (viudedad), `orf` (orfandad) y `fam` (a favor de familiares).
`num` es el número de pensiones y `media` la pensión media en €/mes.

El mapa enlaza cada provincia por su código INE, no por el nombre, así que las variantes
de nombre (Alacant/Alicante, Araba/Álava…) no afectan.

## Actualizar los datos

`scripts/update_data.py` busca en la web del INSS el último `CAaaaamm.xlsx` (pensiones por
provincia) y el último `PTASaaaamm.xlsx` (pensionistas), y en el INE la serie del IPC. Si hay
datos nuevos, actualiza `pensiones.json`, añade el mes a `historico.json` y rehace
`desigualdad.json`.

```bash
pip install -r scripts/requirements.txt
python scripts/update_data.py            # descarga y actualiza si hay un mes nuevo
python scripts/update_data.py --dry-run  # solo comprueba, no escribe
python scripts/update_data.py --ca CA202610.xlsx --ptas PTAS202610.xlsx   # ficheros locales
python scripts/build_history.py          # reconstruye el histórico desde 2010 (~200 descargas)
```

`build_history.py` guarda los Excel descargados en `.cache/inss/` (no se sube al repositorio).
Los ficheros del INSS han cambiado de formato varias veces desde 2010 (nombre de la hoja,
columnas, columna extra con el código de provincia…); `inss.py` los reconoce todos y valida
cada mes por separado.

Antes de escribir nada comprueba que:
- existen la hoja «CA_Total sistema» y las columnas esperadas (número, importe y pensión media
  de cada tipo);
- están las 52 provincias y no aparece ningún nombre desconocido;
- las pensiones medias están en rangos razonables y cuadran con importe / número;
- la suma de las provincias da el total nacional, y la suma por tipos da el total;
- ninguna provincia cambia más de un 15 % respecto al mes anterior;
- en los tramos de pensionistas, la suma de tramos da el total y los rangos son razonables;
- el IPC no tiene saltos mensuales anómalos.

Si algo falla, no escribe ningún fichero y termina con código 1 (código 2 si no ha podido
descargar o leer algún fichero).

Notas de método:
- **Real**: pensión media × IPC del último mes / IPC del mes correspondiente (serie
  `IPC290751` del INE, índice general nacional).
- **Gini**: aproximado con el punto medio de cada tramo; el tramo abierto («Más de …») se
  ajusta para que el importe total cuadre con el importe medio publicado.
- **Percentiles** (P10…P90): interpolación lineal dentro del tramo, suponiendo reparto
  uniforme. **Cuotas** (50 % inferior, 10 % superior) y **S80/S20**: sobre la curva de Lorenz
  construida con los tramos. Todo se calcula por sexo.
- **Por debajo del SMI**: hoja «Tramos» del PTAS (pensionistas cuya suma de pensiones es
  inferior al salario mínimo vigente), por provincia.

## Actualización automática (GitHub Actions)

`.github/workflows/actualizar-y-publicar.yml`:

- **Cada día a las 7:17 UTC** (y a mano desde la pestaña *Actions → Run workflow*) ejecuta
  `scripts/update_data.py`.
  - Si hay datos nuevos y pasan la validación: commit en `main` («Datos actualizados …») y
    publica la web.
  - Si no hay novedades: no hace nada.
  - Si la validación falla o no se pueden descargar los datos: **no publica nada** y abre un
    issue con la etiqueta `aviso-datos` (o comenta en el que ya esté abierto) con el registro
    del error. La web sigue mostrando los últimos datos válidos.
- **Cada push a `main`** (por ejemplo, al fusionar un PR) publica la web.
- **Al lanzarlo a mano** también vuelve a publicar la web, aunque no haya datos nuevos.

La web se publica con GitHub Pages en modo *GitHub Actions* (Settings → Pages → Source).
Solo se publican `index.html`, `sobre.html`, `data/` y `assets/`.

## Analista semanal

Cada lunes se prepara un borrador de post para Substack y un hilo para X:

1. **Datos y gráficos (código, sin IA)**: `.github/workflows/analista-datos.yml` (lunes 5:00 UTC)
   ejecuta `scripts/analista/hallazgos.py`, que calcula las cifras a partir de `data/` y de la
   serie de salarios del INE (ETCL, coste salarial total por trabajador y mes) y genera los
   gráficos con el estilo de David (`scripts/analista/estilo.py`). Resultado en `analisis/`
   (no se publica en la web).
2. **Redacción (rutina de Claude)**: sigue `ANALISTA.md`. Solo puede usar las cifras de
   `analisis/hallazgos.json`, deja huecos para la opinión de David y entrega todo como pull
   request en `borradores/AAAA-MM-DD/` (post, hilo, gráficos y notas). Nunca publica.

## Radar de datos

Cada domingo, antes del analista, se mira qué han publicado las fuentes oficiales sobre
pensiones y Seguridad Social, Estado y deuda, demografía, y vivienda y desigualdad:

1. **Detección (código, sin IA)**: `.github/workflows/radar.yml` (domingo 6:00 UTC) ejecuta
   `scripts/radar/radar.py`, que compara con la semana anterior (`radar/estado.json`):
   operaciones del INE, series de Eurostat para España, déficit y deuda de las AAPP del
   Banco de España, disposiciones generales del BOE (filtradas por palabras clave) y
   publicaciones de la AIReF. Escribe `radar/novedades.json` y abre un issue con la etiqueta
   `radar`. Si una fuente falla, lo dice en el issue y sigue con las demás.
2. **Interpretación (rutina de Claude)**: sigue `RADAR.md`. Comenta el issue (qué importa,
   por qué e ideas de post, sin cifras propias) y, si un dato encaja, abre como mucho un PR
   que lo añade a `scripts/analista/hallazgos.py` con su validación. Nunca fusiona.

Los PR que tocan `scripts/` se comprueban con `.github/workflows/comprobar-pr.yml`.
La afiliación a la Seguridad Social aún no se vigila: su web no tiene enlaces estables.

## Seguridad y privacidad

- **Sin dependencias externas en la web**: fuentes (`assets/fonts/`, licencia SIL OFL), Leaflet
  1.9.4, Chart.js 4.4.0 y el script de GoatCounter están en `assets/`. Los ficheros de
  Leaflet y Chart.js coinciden byte a byte (SHA-256) con los publicados en npm.
- **Content-Security-Policy** en cada página: solo se ejecuta código de esta web y la única
  conexión externa permitida es el contador de visitas (`davidaguilar.goatcounter.com`).
- Los textos que vienen de los ficheros de datos se escapan antes de insertarlos en HTML.
- **Visitas**: GoatCounter, anónimo y sin cookies (no hace falta banner de consentimiento).
- **GitHub Actions**: permisos mínimos por job, acciones fijadas a un commit concreto y
  dependencias de Python con versión fija. `defusedxml` protege la lectura de los Excel.

## Probar en local

`fetch` no funciona abriendo el fichero con doble clic. Hay que servir la carpeta:

```bash
python -m http.server 8000
```

y abrir http://localhost:8000

## Fuentes

- Datos: [Instituto Nacional de la Seguridad Social (INSS)](https://www.seg-social.es),
  Estadísticas > Pensiones, ficheros `CAaaaamm.xlsx`.
- Contornos de provincias: [click_that_hood](https://github.com/codeforgermany/click_that_hood)
  (`spain-provinces.geojson`), simplificado a `cod_prov` y `name`.
