# Vivir en Paz TV — vivirenpaz.tv

Sitio del canal de televisión por internet **Vivir en Paz** y su sección de noticias.

## Estructura

| Carpeta / archivo | Qué contiene |
|---|---|
| `sitio/` | Portada del canal (`index.html`) y recursos (`assets/`: videos, imágenes, íconos). |
| `contenido/noticias/` | Una nota por archivo Markdown (`AAAA-MM-DD-slug.md`). |
| `scripts/construir.py` | Genera el sitio final en `public/`: páginas de cada nota, portada de noticias, temas, RSS y sitemap. |
| `EDITORIAL.md` | Reglas editoriales y formato de las notas. |
| `netlify.toml` | Configuración de publicación en Netlify. |

## Publicación

Netlify está conectado a este repositorio: cada commit en `main` ejecuta `python3 scripts/construir.py` y publica la carpeta `public/`.

## Probar en local

```bash
python3 scripts/construir.py --validar   # revisa el formato de las notas
python3 scripts/construir.py             # construye public/
python3 -m http.server -d public 8000    # abre http://localhost:8000
```

## Agregar, corregir o retirar una nota

Consulte `EDITORIAL.md`.
