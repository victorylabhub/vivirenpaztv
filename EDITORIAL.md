# Manual editorial y formato de notas — Vivir en Paz TV

Este documento rige la redacción automática de noticias. La tarea programada lo lee antes de cada lote. Cualquier cambio de criterio editorial se hace aquí.

## Identidad

- **Medio:** Vivir en Paz TV. Lema: «Información para entender».
- **Audiencia:** público general en México, con énfasis en jóvenes.
- **Tono:** informativo, claro, sereno y respetuoso. Explica el contexto («qué pasó, por qué importa, qué sigue»). Sin sensacionalismo.

## Reglas obligatorias

1. **Solo hechos verificables.** Cada nota se basa en al menos una fuente periodística o institucional identificable y consultada ese mismo día. Si un dato no está en una fuente, no se escribe.
2. **Fuentes citadas y enlazadas.** Cada fuente va en el campo `fuentes` con el nombre del medio y la URL exacta del artículo consultado. Se prefieren dos fuentes independientes en los temas sensibles.
3. **Redacción propia.** No se copian ni se parafrasean de cerca párrafos de otros medios. Las citas textuales van entre comillas, son breves y se atribuyen a quien las dijo.
4. **Sin declaraciones inventadas.** Solo se citan palabras que aparecen textualmente en la fuente.
5. **Sin propaganda electoral.** No se llama a votar por nadie ni en contra de nadie, no se promocionan candidaturas y no se descalifican personas. Las posiciones políticas se presentan atribuidas a quien las sostiene, con su contraparte cuando exista. En periodos de veda electoral no se publican notas sobre candidaturas ni sobre las campañas.
6. **Personas privadas.** No se publican nombres, domicilios ni imágenes de víctimas, de menores de edad ni de personas privadas. Las personas detenidas se presentan como «presuntas» responsables, sin apellidos completos, conforme a la presunción de inocencia.
7. **Violencia.** Se informa sin detalles morbosos ni descripciones gráficas. Cuando aplique, se incluyen datos de ayuda (por ejemplo, la Línea de la Vida: 800 911 2000).
8. **Fechas y cifras exactas.** Las fechas se escriben completas («21 de octubre») y no con «ayer» u «hoy». Las cifras se citan tal como aparecen en la fuente, con su unidad.
9. **Sin rumores ni contenido de redes no verificado.** Una publicación en redes sociales solo se usa cuando su autoría está confirmada (cuenta oficial verificada) y se dice que es una publicación en redes.
10. **No duplicar.** Antes de escribir, se revisan las notas de los últimos 3 días en `contenido/noticias/` para no repetir hechos ya publicados, salvo que haya información nueva relevante.

## Mezcla diaria (20 notas)

| Tema (`tema`)    | Notas |
|------------------|-------|
| `nacional`       | 4 |
| `seguridad`      | 3 |
| `politica`       | 2 |
| `justicia`       | 2 |
| `economia`       | 2 |
| `sociedad`       | 2 |
| `juventudes`     | 2 |
| `internacional`  | 1 |
| `cultura` o `medio-ambiente` | 2 |

Si un tema no tiene noticias suficientes y verificables, se compensa con otro tema. Nunca se rellena con notas sin sustento.

## Extensión

- **Título:** de 60 a 100 caracteres, informativo, sin signos de admiración ni clickbait.
- **Resumen:** una oración de 140 a 220 caracteres que diga lo esencial.
- **Cuerpo:** de 250 a 450 palabras, con 1 o 2 subtítulos `##`, por ejemplo «Contexto» o «Qué sigue».

## Formato del archivo

Ubicación: `contenido/noticias/AAAA-MM-DD-slug-corto.md`

```markdown
---
titulo: "Título informativo de la nota"
fecha: 2026-10-22T06:00:00-06:00
tema: seguridad
resumen: "Una oración con lo esencial del hecho, quién, qué, dónde y cuándo."
fuentes:
  - "Nombre del medio | https://url-exacta-del-articulo"
  - "Segundo medio | https://url-exacta"
autor: "Redacción Vivir en Paz"
ia: si
---

Primer párrafo con el hecho principal.

Segundo párrafo con detalles y datos atribuidos.

## Contexto

Antecedentes que ayudan a entender.

## Qué sigue

Próximos pasos conocidos.
```

- `tema` debe ser uno de: `nacional`, `seguridad`, `justicia`, `politica`, `economia`, `juventudes`, `sociedad`, `internacional`, `cultura`, `medio-ambiente`.
- `fecha`: hora de publicación en la hora del centro de México (UTC-06:00). Escalonar las notas del lote por minutos (06:00, 06:03, 06:06…) para que se ordenen.
- Campos de foto (opcionales, ver «Fotografía»): `imagen`, `imagen_credito`, `imagen_fuente`, `imagen_alt`.
- Campos opcionales: `slug` (URL personalizada), `borrador: si` (no se publica), `correccion: "Texto de la corrección"` (se muestra al pie de la nota).
- El cuerpo admite: párrafos, `##` y `###`, listas con `-`, citas con `>`, **negritas**, *cursivas* y [enlaces](https://…).

## Fotografía

Cada nota lleva, cuando sea posible, una **foto con licencia libre de Wikimedia Commons**. Está prohibido usar fotos de otros medios, agencias, redes sociales o bancos comerciales.

1. Buscar candidatas con el script, usando términos concretos del lugar, institución o tema (pruebe en español y en inglés):

   ```bash
   python3 scripts/buscar_foto.py "Palacio Nacional Ciudad de México"
   ```

2. Elegir una foto que **ilustre** la nota sin inducir a error. Debe ser el lugar, el edificio, la institución o un tema genérico relacionado, por ejemplo la fachada del Banco de México para una nota de tipo de cambio.
   - No usar fotos de personas privadas ni de menores.
   - No usar fotos de víctimas, de violencia explícita ni de hechos distintos presentados como si fueran el de la nota.
   - Las fotos de funcionarios o figuras públicas solo se usan si la nota trata sobre ellas.
3. Copiar al encabezado los cuatro campos (la URL de `imagen` puede ser de upload.wikimedia.org o thumb.wikimedia.org, sin parámetros después de `?`) que imprime el script y escribir `imagen_alt` describiendo lo que se ve:

   ```markdown
   imagen: "https://upload.wikimedia.org/wikipedia/commons/thumb/…/1280px-….jpg"
   imagen_credito: "Nombre del autor (CC BY-SA 4.0)"
   imagen_fuente: "https://commons.wikimedia.org/wiki/File:….jpg"
   imagen_alt: "Fachada del edificio del Banco de México en el Centro Histórico"
   ```

4. Si no hay una foto adecuada, se omiten los cuatro campos y la nota se muestra con la ilustración del tema. Es preferible no poner foto a poner una que no corresponda.

El sitio muestra al pie de la foto el aviso «Imagen ilustrativa» con el crédito y el enlace a la licencia, como exigen las licencias Creative Commons.

## Correcciones y retiros

- **Corregir:** editar el archivo y añadir `correccion: "Se corrigió la cifra de …"`. No se borra el error sin dejar constancia.
- **Retirar:** añadir `borrador: si` o eliminar el archivo.

## Verificación técnica

Antes de subir un lote:

```bash
python3 scripts/construir.py --validar
```

Si reporta errores, se corrigen antes de hacer commit.
