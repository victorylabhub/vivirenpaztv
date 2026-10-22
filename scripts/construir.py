#!/usr/bin/env python3
"""
Construye el sitio de Vivir en Paz TV.

- Copia el sitio estático de /sitio a /public.
- Convierte cada nota de /contenido/noticias/*.md en una página HTML.
- Genera la portada de noticias (con paginación), páginas por tema,
  noticias/ultimas.json (para la portada del canal), sitemap.xml, feed RSS y robots.txt.

Solo usa la biblioteca estándar de Python (Netlify lo ejecuta en cada publicación).
Formato de cada nota: ver EDITORIAL.md.
"""
import html, json, math, re, shutil, sys, unicodedata
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITIO, CONTENIDO, SALIDA = RAIZ / "sitio", RAIZ / "contenido" / "noticias", RAIZ / "public"
DOMINIO = "https://vivirenpaz.tv"
POR_PAGINA = 24
MX = timezone(timedelta(hours=-6))

TEMAS = {
    "nacional":      ("Nacional", "mexico"),
    "seguridad":     ("Seguridad y paz", "seguridad"),
    "justicia":      ("Justicia", "justicia"),
    "politica":      ("Política", "dialogo"),
    "economia":      ("Economía", "crecimiento"),
    "juventudes":    ("Juventudes", "comunidad"),
    "sociedad":      ("Sociedad", "familia"),
    "internacional": ("Internacional", "paloma"),
    "cultura":       ("Cultura", "corazon"),
    "medio-ambiente":("Medio ambiente", "olivo"),
}
MESES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]

class ErrorNota(Exception): pass

# ---------------------------------------------------------------- utilidades
def esc(t): return html.escape(str(t), quote=True)

def slugify(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:80]

def fecha_larga(d):
    return f"{d.day} de {MESES[d.month-1]} de {d.year}"

def leer_frontmatter(texto, origen):
    if not texto.startswith("---"):
        raise ErrorNota(f"{origen}: falta el encabezado --- al inicio")
    try:
        _, cab, cuerpo = texto.split("---", 2)
    except ValueError:
        raise ErrorNota(f"{origen}: encabezado sin cerrar")
    datos, clave_lista = {}, None
    for linea in cab.strip().splitlines():
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        m_item = re.match(r"^\s*-\s+(.*)$", linea)
        if m_item and clave_lista:
            datos[clave_lista].append(m_item.group(1).strip().strip('"'))
            continue
        m = re.match(r"^([a-z_]+):\s*(.*)$", linea)
        if not m:
            raise ErrorNota(f"{origen}: línea no válida en el encabezado: {linea!r}")
        k, v = m.group(1), m.group(2).strip()
        if v == "":
            datos[k], clave_lista = [], k
        else:
            datos[k], clave_lista = v.strip('"'), None
    return datos, cuerpo.strip()

def inline(t):
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    return t

def markdown(md):
    """Subconjunto: párrafos, ## y ### subtítulos, listas -, citas >, **negritas**, *cursivas*, [enlaces](url)."""
    salida, bloque, tipo = [], [], None
    def cerrar():
        nonlocal bloque, tipo
        if not bloque: return
        if tipo == "p":  salida.append("<p>" + inline(" ".join(bloque)) + "</p>")
        if tipo == "ul": salida.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in bloque) + "</ul>")
        if tipo == "q":  salida.append("<blockquote><p>" + inline(" ".join(bloque)) + "</p></blockquote>")
        bloque, tipo = [], None
    for linea in md.splitlines():
        s = linea.strip()
        if not s: cerrar(); continue
        if s.startswith("### "): cerrar(); salida.append(f"<h3>{inline(s[4:])}</h3>"); continue
        if s.startswith("## "):  cerrar(); salida.append(f"<h2>{inline(s[3:])}</h2>"); continue
        nuevo = "ul" if s.startswith("- ") else "q" if s.startswith("> ") else "p"
        if nuevo != tipo: cerrar(); tipo = nuevo
        bloque.append(s[2:] if nuevo in ("ul", "q") else s)
    cerrar()
    return "\n".join(salida)

def palabras(t): return len(re.findall(r"\w+", t))

# ---------------------------------------------------------------- notas
def cargar_notas():
    notas, errores, vistos = [], [], set()
    for f in sorted(CONTENIDO.glob("*.md")):
        try:
            d, cuerpo = leer_frontmatter(f.read_text(encoding="utf-8"), f.name)
            for k in ("titulo", "fecha", "tema", "resumen", "fuentes"):
                if not d.get(k): raise ErrorNota(f"{f.name}: falta el campo '{k}'")
            if d["tema"] not in TEMAS:
                raise ErrorNota(f"{f.name}: tema '{d['tema']}' no válido (use: {', '.join(TEMAS)})")
            try:
                fecha = datetime.fromisoformat(d["fecha"])
            except ValueError:
                raise ErrorNota(f"{f.name}: fecha no válida, use 2026-10-22T06:00:00-06:00")
            if fecha.tzinfo is None: fecha = fecha.replace(tzinfo=MX)
            fuentes = []
            for linea in d["fuentes"] if isinstance(d["fuentes"], list) else [d["fuentes"]]:
                nombre, _, url = linea.partition("|")
                url = url.strip()
                if not url.startswith(("http://", "https://")):
                    raise ErrorNota(f"{f.name}: cada fuente debe ser 'Medio | https://url'")
                fuentes.append((nombre.strip(), url))
            imagen = None
            if d.get("imagen"):
                if not re.match(r"^https://(upload|thumb)\.wikimedia\.org/[^\s?]+$", d["imagen"]):
                    raise ErrorNota(f"{f.name}: 'imagen' debe ser una URL de upload.wikimedia.org o thumb.wikimedia.org, sin parámetros")
                for k in ("imagen_credito", "imagen_fuente", "imagen_alt"):
                    if not d.get(k): raise ErrorNota(f"{f.name}: con 'imagen' es obligatorio '{k}'")
                if not d["imagen_fuente"].startswith("https://commons.wikimedia.org/"):
                    raise ErrorNota(f"{f.name}: 'imagen_fuente' debe ser la página del archivo en commons.wikimedia.org")
                imagen = dict(url=d["imagen"], credito=d["imagen_credito"], fuente=d["imagen_fuente"], alt=d["imagen_alt"])
            if d.get("borrador", "").lower() in ("si", "sí", "true"):
                continue
            slug = d.get("slug") or slugify(d["titulo"])
            base = slug; n = 2
            while slug in vistos: slug = f"{base}-{n}"; n += 1
            vistos.add(slug)
            notas.append(dict(
                titulo=d["titulo"], fecha=fecha, tema=d["tema"], resumen=d["resumen"],
                fuentes=fuentes, autor=d.get("autor", "Redacción Vivir en Paz"),
                ia=d.get("ia", "si").lower() in ("si", "sí", "true"),
                corregida=d.get("correccion", ""), slug=slug,
                url=f"/noticias/{fecha:%Y/%m}/{slug}/", cuerpo=markdown(cuerpo),
                lectura=max(1, round(palabras(cuerpo) / 220)), archivo=f.name, imagen=imagen))
        except ErrorNota as e:
            errores.append(str(e))
    notas.sort(key=lambda n: n["fecha"], reverse=True)
    return notas, errores

# ---------------------------------------------------------------- plantillas
CSS = """
:root{--morado:#2A0F57;--morado-2:#4B1D8F;--lila:#C7B2FF;--vivo:#6D2FD1;--ambar:#F2B65A;
 --tinta:#141A2E;--texto:#2A3148;--suave:#5B6480;--fondo:#F6F3FB;--papel:#fff;--linea:#E2DAF0;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--tinta:#EEF1F8;--texto:#D3D8E6;--suave:#9AA3BC;--fondo:#120822;--papel:#1C1033;--linea:#33224F;--vivo:#B79CFF;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--fondo);color:var(--texto);font:17px/1.65 "Atkinson Hyperlegible",system-ui,sans-serif}
a{color:inherit}:focus-visible{outline:3px solid var(--lila);outline-offset:3px;border-radius:4px}
h1,h2,h3{font-family:"Bricolage Grotesque",system-ui,sans-serif;color:var(--tinta);line-height:1.12;letter-spacing:-.015em;margin:0}
.env{max-width:1200px;margin:0 auto;padding:0 16px}@media(min-width:760px){.env{padding:0 32px}}
.cab{background:rgba(42,15,87,.95);backdrop-filter:blur(12px);color:#fff;position:sticky;top:0;z-index:10}
.cab .env{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:66px}
.marca{display:flex;align-items:center;gap:10px;text-decoration:none;color:#fff}
.marca img{width:44px;height:40px;object-fit:contain}
.marca b{font-family:Montserrat,system-ui,sans-serif;font-weight:900;text-transform:uppercase;font-size:1.2rem;line-height:1}
.marca small{display:block;font-size:.72rem;opacity:.8}
.cab nav{display:flex;gap:4px;flex-wrap:wrap}.cab nav a{text-decoration:none;color:#EEE8FB;padding:8px 12px;border-radius:999px;font-size:.95rem}
.cab nav a:hover,.cab nav a[aria-current]{background:rgba(255,255,255,.12);color:#fff}
@media(max-width:700px){.cab nav a.opc{display:none}}
.portada{background:radial-gradient(90% 120% at 85% 0%,#4B1D8F 0%,#2A0F57 60%);color:#fff;padding:48px 0 40px}
.portada h1{color:#fff;font-family:Montserrat,system-ui,sans-serif;font-weight:900;text-transform:uppercase;font-size:clamp(2.2rem,6vw,4rem);letter-spacing:-.02em}
.portada p{color:#E2D8F7;max-width:60ch;margin:10px 0 0}
.temas{display:flex;gap:6px;overflow-x:auto;padding:22px 0 4px}
.temas a{white-space:nowrap;text-decoration:none;border:1px solid rgba(255,255,255,.3);color:#fff;border-radius:999px;padding:6px 14px;font-size:.9rem}
.temas a[aria-current]{background:#fff;color:var(--morado);border-color:#fff;font-weight:700}
.rejilla{display:grid;gap:20px;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));padding:36px 0 56px}
.nota{background:var(--papel);border:1px solid var(--linea);border-radius:18px;overflow:hidden;display:flex;flex-direction:column;text-decoration:none;transition:transform .35s cubic-bezier(.16,.84,.24,1),box-shadow .35s}
.nota:hover{transform:translateY(-4px);box-shadow:0 24px 40px -26px rgba(42,15,87,.55)}
.nota.destacada{grid-column:1/-1}@media(min-width:900px){.nota.destacada{flex-direction:row}.nota.destacada .banda{flex:0 0 46%;aspect-ratio:auto;min-height:280px}.nota.destacada h2{font-size:2rem}}
.banda{aspect-ratio:16/7;display:grid;place-items:center;position:relative;overflow:hidden;color:rgba(255,255,255,.9);background:linear-gradient(140deg,var(--c1),var(--c2))}
.banda .ic{width:34%;height:60%;max-width:120px}
.banda.con-foto img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transition:transform .8s cubic-bezier(.16,.84,.24,1)}
.banda.con-foto .tema{z-index:1}
.nota:hover .banda.con-foto img{transform:scale(1.05)}
.foto{margin:0 0 20px}.foto img{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:16px;display:block;background:var(--linea)}
.foto figcaption{font-size:.82rem;color:var(--suave);margin-top:8px}.foto figcaption a{color:inherit}
.banda .tema{position:absolute;left:14px;top:12px;background:rgba(0,0,0,.25);color:#fff;font-size:.78rem;font-weight:700;padding:3px 10px;border-radius:999px}
.nota .cuerpo{padding:18px 20px 22px;display:flex;flex-direction:column;gap:8px}
.nota h2{font-size:1.2rem}.nota p{margin:0;color:var(--suave)}
.meta{font-size:.85rem;color:var(--suave)}
.ic{display:inline-block;background:currentColor;-webkit-mask:var(--i) center/contain no-repeat;mask:var(--i) center/contain no-repeat}
.paginas{display:flex;gap:8px;justify-content:center;padding-bottom:64px;flex-wrap:wrap}
.paginas a,.paginas span{min-width:42px;text-align:center;padding:8px 12px;border-radius:999px;border:1px solid var(--linea);text-decoration:none;background:var(--papel)}
.paginas span{background:var(--morado);color:#fff;border-color:var(--morado)}
.vacio{padding:72px 0;text-align:center;color:var(--suave)}
article.completa{max-width:760px;margin:0 auto;padding:40px 0 24px}
.completa .volver{font-size:.9rem;color:var(--suave);text-decoration:none}
.completa h1{font-size:clamp(1.9rem,4.4vw,2.9rem);margin:14px 0 14px}
.completa .entrada{font-size:1.2rem;color:var(--tinta);margin:0 0 18px}
.completa .meta{display:flex;flex-wrap:wrap;gap:6px 16px;padding:12px 0;border-top:1px solid var(--linea);border-bottom:1px solid var(--linea)}
.completa .texto{margin-top:24px}.completa .texto p{margin:0 0 1.1em}
.completa .texto h2{font-size:1.45rem;margin:1.4em 0 .5em}.completa .texto h3{font-size:1.15rem;margin:1.2em 0 .4em}
.completa .texto a{color:var(--vivo)}
.completa blockquote{margin:1.2em 0;padding:4px 0 4px 18px;border-left:4px solid var(--ambar);color:var(--tinta)}
.fuentes,.aviso{background:var(--papel);border:1px solid var(--linea);border-radius:14px;padding:18px 20px;margin-top:22px}
.fuentes h2{font-size:1rem;margin-bottom:6px}.fuentes ul{margin:0;padding-left:20px}.fuentes a{color:var(--vivo)}
.aviso{font-size:.9rem;color:var(--suave)}
.compartir{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.compartir a,.compartir button{font:inherit;font-size:.9rem;font-weight:700;text-decoration:none;border:1px solid var(--linea);background:var(--papel);color:var(--tinta);border-radius:999px;padding:8px 16px;cursor:pointer}
.relacionadas{border-top:1px solid var(--linea);margin-top:40px}
.relacionadas>h2{padding-top:32px;font-size:1.5rem}
.relacionadas .rejilla{padding-top:20px}
.pie{background:var(--morado);color:#D9CCF5;padding:32px 0;font-size:.9rem}
.pie .env{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px}.pie a{color:#fff}
"""

COLORES = {"nacional":("#2A0F57","#6D2FD1"),"seguridad":("#2E1B5E","#4B1D8F"),"justicia":("#3A1578","#7A3FB0"),
           "politica":("#22114A","#5A2A8C"),"economia":("#3D2A63","#6D2FD1"),"juventudes":("#5B1F7A","#B0479A"),
           "sociedad":("#4B1D8F","#8C5BE0"),"internacional":("#1F1550","#3E6E9E"),"cultura":("#5B1F7A","#C26A3A"),
           "medio-ambiente":("#1F3D35","#4B7F5E")}

def iconos_css(raiz_rel):
    return "".join(f".i-{n}{{--i:url({raiz_rel}assets/iconos/{n}.png)}}" for n in {v[1] for v in TEMAS.values()})

ACTUAL = ' aria-current="page"'

def pagina(titulo, descripcion, url, cuerpo, actual="noticias", extra_head="", tipo="website", imagen="/assets/img/presentacion.jpg"):
    return f"""<!doctype html>
<html lang="es-MX">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo)}</title>
<meta name="description" content="{esc(descripcion)}">
<link rel="canonical" href="{DOMINIO}{url}">
<meta name="theme-color" content="#2A0F57">
<link rel="icon" type="image/png" href="/assets/favicon.png">
<link rel="alternate" type="application/rss+xml" title="Noticias de Vivir en Paz TV" href="/noticias/feed.xml">
<meta property="og:type" content="{tipo}">
<meta property="og:site_name" content="Vivir en Paz TV">
<meta property="og:title" content="{esc(titulo)}">
<meta property="og:description" content="{esc(descripcion)}">
<meta property="og:url" content="{DOMINIO}{url}">
<meta property="og:image" content="{imagen if imagen.startswith("http") else DOMINIO + imagen}">
<meta property="og:locale" content="es_MX">
<meta name="twitter:card" content="summary_large_image">
{extra_head}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700;900&family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=Atkinson+Hyperlegible:wght@400;700&display=swap" rel="stylesheet">
<style>{CSS}{iconos_css("/")}</style>
</head>
<body>
<header class="cab"><div class="env">
  <a class="marca" href="/"><img src="/assets/img/logo-paloma.png" alt="" width="44" height="40"><span><b>Vivir en Paz</b><small>Información para entender</small></span></a>
  <nav aria-label="Principal">
    <a href="/#envivo">En vivo</a>
    <a class="opc" href="/#programacion">Programación</a>
    <a href="/noticias/"{ACTUAL if actual == "noticias" else ""}>Noticias</a>
    <a class="opc" href="/#contacto">Contacto</a>
  </nav>
</div></header>
<main id="contenido">
{cuerpo}
</main>
<footer class="pie"><div class="env">
  <span>© {datetime.now(MX).year} Vivir en Paz TV. Un proyecto de comunicación hecho por jóvenes.</span>
  <span><a href="/noticias/feed.xml">RSS</a> · <a href="https://www.youtube.com/@VivirenPAZTV" target="_blank" rel="noopener">YouTube</a></span>
</div></footer>
</body>
</html>"""

def tarjeta(n, destacada=False):
    nombre, icono = TEMAS[n["tema"]]; c1, c2 = COLORES[n["tema"]]
    return f"""<a class="nota{' destacada' if destacada else ''}" href="{n['url']}">
  <div class="banda{' con-foto' if n['imagen'] else ''}" style="--c1:{c1};--c2:{c2}"><span class="tema">{esc(nombre)}</span>{f'<img src="{esc(n["imagen"]["url"])}" alt="{esc(n["imagen"]["alt"])}" loading="lazy" decoding="async">' if n['imagen'] else f'<span class="ic i-{icono}" aria-hidden="true"></span>'}</div>
  <div class="cuerpo"><p class="meta"><time datetime="{n['fecha'].isoformat()}">{fecha_larga(n['fecha'])}</time> · {n['lectura']} min</p>
  <h2>{esc(n['titulo'])}</h2><p>{esc(n['resumen'])}</p></div>
</a>"""

def portada_listado(titulo, subtitulo, tema_actual):
    ac = ' aria-current="page"'
    chips = [f'<a href="/noticias/"{ac if tema_actual is None else ""}>Todas</a>']
    for k, (nombre, _) in TEMAS.items():
        chips.append(f'<a href="/noticias/tema/{k}/"{ac if tema_actual == k else ""}>{esc(nombre)}</a>')
    return f"""<section class="portada"><div class="env">
  <h1>{esc(titulo)}</h1><p>{esc(subtitulo)}</p>
  <nav class="temas" aria-label="Temas">{''.join(chips)}</nav>
</div></section>"""

def paginacion(base, actual, total):
    if total <= 1: return ""
    partes = []
    for i in range(1, total + 1):
        href = base if i == 1 else f"{base}pagina/{i}/"
        partes.append(f'<span aria-current="page">{i}</span>' if i == actual else f'<a href="{href}">{i}</a>')
    return f'<nav class="paginas" aria-label="Páginas">{"".join(partes)}</nav>'

def escribir(ruta_url, contenido):
    destino = SALIDA / ruta_url.strip("/") / "index.html" if not ruta_url.endswith(".xml") else SALIDA / ruta_url.strip("/")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(contenido, encoding="utf-8")

def construir_listados(notas, base, titulo, subtitulo, tema):
    paginas = max(1, math.ceil(len(notas) / POR_PAGINA))
    for p in range(1, paginas + 1):
        lote = notas[(p-1)*POR_PAGINA : p*POR_PAGINA]
        if lote:
            tarjetas = "".join(tarjeta(n, destacada=(p == 1 and i == 0)) for i, n in enumerate(lote))
            cuerpo = f'<div class="env"><div class="rejilla">{tarjetas}</div>{paginacion(base, p, paginas)}</div>'
        else:
            cuerpo = '<div class="env vacio"><p>Todavía no hay notas publicadas en esta sección.</p></div>'
        url = base if p == 1 else f"{base}pagina/{p}/"
        t = titulo if p == 1 else f"{titulo} — página {p}"
        escribir(url, pagina(f"{t} | Vivir en Paz TV", subtitulo, url, portada_listado(titulo, subtitulo, tema) + cuerpo))

def construir_nota(n, relacionadas):
    nombre, icono = TEMAS[n["tema"]]
    fuentes = "".join(f'<li><a href="{esc(u)}" target="_blank" rel="noopener">{esc(m or u)}</a></li>' for m, u in n["fuentes"])
    aviso = ("Nota elaborada con apoyo de inteligencia artificial a partir de las fuentes públicas citadas. "
             "Si detecta un error, escríbanos a <a href=\"mailto:y@vivirenpaz.org?subject=Correcci%C3%B3n%20de%20nota\">y@vivirenpaz.org</a>.") if n["ia"] else \
            "Si detecta un error, escríbanos a <a href=\"mailto:y@vivirenpaz.org\">y@vivirenpaz.org</a>."
    correccion = f'<p class="aviso"><strong>Corrección:</strong> {esc(n["corregida"])}</p>' if n["corregida"] else ""
    url_abs = DOMINIO + n["url"]
    ld = json.dumps({"@context":"https://schema.org","@type":"NewsArticle","headline":n["titulo"],"description":n["resumen"],
        "datePublished":n["fecha"].isoformat(),"dateModified":n["fecha"].isoformat(),"author":{"@type":"Organization","name":n["autor"]},
        "publisher":{"@type":"Organization","name":"Vivir en Paz TV","logo":{"@type":"ImageObject","url":DOMINIO+"/assets/favicon.png"}},
        "mainEntityOfPage":url_abs,"image":[n["imagen"]["url"] if n["imagen"] else DOMINIO+"/assets/img/presentacion.jpg"],"articleSection":nombre}, ensure_ascii=False)
    rel = "".join(tarjeta(r) for r in relacionadas)
    im = n["imagen"]
    foto = (f'<figure class="foto"><img src="{esc(im["url"])}" alt="{esc(im["alt"])}">'
            f'<figcaption>Imagen ilustrativa. Foto: <a href="{esc(im["fuente"])}" target="_blank" rel="noopener">{esc(im["credito"])}</a>, vía Wikimedia Commons.</figcaption></figure>') if im else ""
    cuerpo = f"""<div class="env">
<article class="completa">
  <a class="volver" href="/noticias/tema/{n['tema']}/">← {esc(nombre)}</a>
  <h1>{esc(n['titulo'])}</h1>
  <p class="entrada">{esc(n['resumen'])}</p>
  {foto}
  <p class="meta"><span>{esc(n['autor'])}</span><time datetime="{n['fecha'].isoformat()}">{fecha_larga(n['fecha'])}, {n['fecha']:%H:%M} h</time><span>{n['lectura']} min de lectura</span></p>
  <div class="texto">{n['cuerpo']}</div>
  {correccion}
  <section class="fuentes" aria-labelledby="h-fuentes"><h2 id="h-fuentes">Fuentes</h2><ul>{fuentes}</ul></section>
  <p class="aviso">{aviso}</p>
  <div class="compartir">
    <a href="https://wa.me/?text={esc(n['titulo'])}%20{esc(url_abs)}" target="_blank" rel="noopener">WhatsApp</a>
    <a href="https://www.facebook.com/sharer/sharer.php?u={esc(url_abs)}" target="_blank" rel="noopener">Facebook</a>
    <a href="https://x.com/intent/post?url={esc(url_abs)}&amp;text={esc(n['titulo'])}" target="_blank" rel="noopener">X</a>
    <button type="button" onclick="navigator.clipboard.writeText('{esc(url_abs)}').then(()=>this.textContent='Enlace copiado')">Copiar enlace</button>
  </div>
</article>
{f'<section class="relacionadas"><h2>Más de {esc(nombre)}</h2><div class="rejilla">{rel}</div></section>' if rel else ''}
</div>"""
    escribir(n["url"], pagina(f"{n['titulo']} | Vivir en Paz TV", n["resumen"], n["url"], cuerpo,
                              extra_head=f'<script type="application/ld+json">{ld}</script>', tipo="article",
                              imagen=(n["imagen"]["url"] if n["imagen"] else "/assets/img/presentacion.jpg")))

def construir_feeds(notas):
    ahora = datetime.now(MX)
    items = "".join(f"""<item><title>{esc(n['titulo'])}</title><link>{DOMINIO}{n['url']}</link><guid>{DOMINIO}{n['url']}</guid>
<pubDate>{format_datetime(n['fecha'])}</pubDate><category>{esc(TEMAS[n['tema']][0])}</category><description>{esc(n['resumen'])}</description></item>""" for n in notas[:50])
    escribir("/noticias/feed.xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Noticias de Vivir en Paz TV</title><link>{DOMINIO}/noticias/</link>
<description>Información para entender.</description><language>es-MX</language><lastBuildDate>{format_datetime(ahora)}</lastBuildDate>{items}</channel></rss>""")
    urls = [f"<url><loc>{DOMINIO}/</loc></url>", f"<url><loc>{DOMINIO}/noticias/</loc></url>"]
    urls += [f"<url><loc>{DOMINIO}/noticias/tema/{k}/</loc></url>" for k in TEMAS]
    urls += [f"<url><loc>{DOMINIO}{n['url']}</loc><lastmod>{n['fecha'].date().isoformat()}</lastmod></url>" for n in notas]
    escribir("/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(urls) + "</urlset>")
    (SALIDA / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {DOMINIO}/sitemap.xml\n", encoding="utf-8")
    (SALIDA / "noticias").mkdir(parents=True, exist_ok=True)
    (SALIDA / "noticias" / "ultimas.json").write_text(json.dumps([{
        "titulo": n["titulo"], "resumen": n["resumen"], "url": n["url"], "tema": TEMAS[n["tema"]][0],
        "icono": TEMAS[n["tema"]][1], "colores": COLORES[n["tema"]], "fecha": n["fecha"].isoformat(),
        "fecha_texto": fecha_larga(n["fecha"]), "imagen": (n["imagen"] or {}).get("url"),
        "imagen_alt": (n["imagen"] or {}).get("alt")} for n in notas[:7]], ensure_ascii=False), encoding="utf-8")

def main():
    solo_validar = "--validar" in sys.argv
    notas, errores = cargar_notas()
    for e in errores: print("ERROR:", e, file=sys.stderr)
    if solo_validar:
        print(f"{len(notas)} notas válidas, {len(errores)} con errores")
        sys.exit(1 if errores else 0)
    if SALIDA.exists(): shutil.rmtree(SALIDA)
    shutil.copytree(SITIO, SALIDA)
    construir_listados(notas, "/noticias/", "Noticias", "Información para entender: lo más relevante del día, con fuentes.", None)
    for k, (nombre, _) in TEMAS.items():
        construir_listados([n for n in notas if n["tema"] == k], f"/noticias/tema/{k}/", nombre, f"Notas de {nombre.lower()} con fuentes verificables.", k)
    for n in notas:
        rel = [r for r in notas if r["tema"] == n["tema"] and r is not n][:3]
        construir_nota(n, rel)
    construir_feeds(notas)
    print(f"Sitio construido: {len(notas)} notas publicadas, {len(errores)} omitidas por errores.")

if __name__ == "__main__":
    main()
