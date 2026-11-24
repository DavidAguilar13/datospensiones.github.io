# Notas de revisión

Tema: `pensiones_vs_salarios` (el tema `novedades_mes` ya se trató en la rama `borrador/2026-11-16`, sin PR abierto ni fusionada).

## Cifras usadas
| Cifra | id en hallazgos.json | Valor | Fuente |
|---|---|---|---|
| Pensión media real 2010–2025 | pension_real_acum | 24,6 % | INSS; INE IPC |
| Salario medio real 2010–2025 | salario_real_acum | -6,1 % | INE ETCL; INE IPC |
| Años en que la pensión gana al salario | anyos_pension_gana | 14 de 15 (excepción: 2021) | Cálculo propio |
| Ratio pensión/salario 2010 | ratio_inicio | 41,6 % | INSS; INE ETCL |
| Ratio pensión/salario 2025 | ratio_fin | 55,2 % | INSS; INE ETCL |
| Pensión media 2025 | pension_media_nominal_fin | 1.311,69 € | INSS |
| Coste salarial medio 2025 | salario_medio_nominal_fin | 2.376,55 € | INE ETCL |
| Índices 2025 (124,6 / 93,9) y 2022 (113,1 / 91,3) | serie_anual | — | INSS; INE |

## Advertencias incluidas
Efecto sustitución; salario = coste salarial total (ETCL, sin autónomos); pensión por pensión y 14 pagas vs. salario 12 meses; medias anuales 2010–2025.

## Datos que faltan / ideas
- Cotizaciones frente a gasto, deuda de la Seguridad Social y afiliación: sin datos aún (no se citan cifras).
- Comparar con productividad: dato que falta.
- Próximo tema sugerido: desigualdad entre pensionistas (brecha de género, SMI) o novedades del mes.
- Nota: el borrador del 16-11 (novedades_mes) no tiene PR; revisa si se publicó.
