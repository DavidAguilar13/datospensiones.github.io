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

`scripts/update_data.py` busca el último `CAaaaamm.xlsx` en la página de estadísticas de
pensiones del INSS, lo descarga, lo convierte y escribe `data/pensiones.json`.

```bash
pip install -r scripts/requirements.txt
python scripts/update_data.py            # descarga y actualiza si hay un mes nuevo
python scripts/update_data.py --dry-run  # solo comprueba, no escribe
python scripts/update_data.py --file CA202610.xlsx   # usa un Excel ya descargado
```

Antes de escribir nada comprueba que:
- existen la hoja «CA_Total sistema» y las columnas esperadas (número, importe y pensión media
  de cada tipo);
- están las 52 provincias y no aparece ningún nombre desconocido;
- las pensiones medias están en rangos razonables y cuadran con importe / número;
- la suma de las provincias da el total nacional, y la suma por tipos da el total;
- ninguna provincia cambia más de un 15 % respecto a los datos anteriores.

Si algo falla, no toca `data/pensiones.json` y termina con código 1 (código 2 si no ha podido
descargar o leer el Excel).

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
