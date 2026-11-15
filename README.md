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
