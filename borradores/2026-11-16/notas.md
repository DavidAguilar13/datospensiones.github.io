# Notas de revisión — 2026-11-16

Tema principal: `novedades_mes` (dato de 2026-10, pensión media real en negativo). Sin tema secundario.

## Cifras usadas
| id en hallazgos.json | valor | fuente |
|---|---|---|
| var_interanual_media_real | -0,2 % | INSS; INE IPC |
| var_interanual_media_nominal | 4,6 % | INSS |
| media_ultimo_mes | 1.376,14 €/mes | INSS |
| num_pensiones | 10.565.782 | INSS |
| var_mensual_num | 18.365 | INSS |
| var_interanual_num | 1,6 % | INSS |
| var_interanual_real_jub / viu / ip | -0,4 % / -0,6 % / -1,1 % | INSS; INE IPC |
| real_desde_2010_nacional | 22,7 % | INSS; INE IPC |
| real_desde_2010_max / min | Soria 30,6 % / Huelva 17,1 % | INSS; INE IPC |
| prov_mas_sube / prov_menos_sube | Cuenca 5,9 % / Asturias 3,8 % | INSS |

## Advertencias incluidas
- Efecto sustitución: la pensión media no es la revalorización.
- Pensiones ≠ pensionistas.

## A revisar
- `prov_mas_sube` / `prov_menos_sube`: el JSON no dice si es variación nominal o real; en el post no lo especifico.
- Tiene huecos `[OPINIÓN DE DAVID]` (4) por rellenar.
- Frase de cierre sobre posible cambio de tendencia: está formulada con cautela; ajústala a tu criterio.

## Datos que faltan / ideas para próximos posts
- Dato que falta: IPC interanual de octubre de 2026 para explicar el -0,2 % (no está en hallazgos.json).
- Próximos: pensiones vs. salarios (ya hay datos: pensión real +24,6 % vs. salario real -6,1 % 2010–2025); desigualdad entre pensionistas.
- Sin cifras todavía: cotizaciones frente a gasto, deuda de la Seguridad Social, afiliación.
