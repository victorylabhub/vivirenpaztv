#!/usr/bin/env python3
"""
Busca fotografías con licencia libre en Wikimedia Commons para ilustrar una nota.

Uso:
    python3 scripts/buscar_foto.py "Palacio Nacional Ciudad de México"
    python3 scripts/buscar_foto.py "Banco de México edificio" --max 8

Imprime candidatas con licencia libre (CC0, dominio público, CC BY, CC BY-SA) y los
campos listos para pegar en el encabezado de la nota. Excluye licencias no libres,
imágenes pequeñas y archivos que no son fotos (SVG, PDF, mapas, logotipos).
"""
import argparse, html, json, re, sys, time, urllib.error, urllib.parse, urllib.request

API = "https://commons.wikimedia.org/w/api.php"
AGENTE = "VivirEnPazTV-Redaccion/1.0 (https://vivirenpaz.tv; y@vivirenpaz.org)"
LIBRES = re.compile(r"^(cc0|public domain|pd|cc by(-sa)? [0-9.]+|cc by(-sa)?)", re.I)
EXCLUIR = re.compile(r"\.(svg|pdf|tif|tiff|gif|webm|ogv)$|logo|escudo|coat of arms|map|mapa|flag of|bandera de", re.I)

def limpiar(t):
    t = re.sub(r"<[^>]+>", "", t or "")
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

def buscar(consulta, maximo):
    params = {
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": "6",
        "gsrsearch": f"{consulta} filetype:bitmap", "gsrlimit": str(maximo * 3),
        "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": "1280",
    }
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": AGENTE})
    for intento in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                datos = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code != 429 or intento == 4: raise
            espera = int(e.headers.get("Retry-After") or 0) or 5 * (intento + 1)
            print(f"(Wikimedia pide esperar {espera} s…)", file=sys.stderr); time.sleep(min(espera, 60))
    paginas = sorted((datos.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    salida = []
    for p in paginas:
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        licencia = limpiar(meta.get("LicenseShortName", {}).get("value"))
        titulo = p.get("title", "")
        if not LIBRES.match(licencia) or EXCLUIR.search(titulo):
            continue
        if info.get("width", 0) < 1000:
            continue
        autor = limpiar(meta.get("Artist", {}).get("value")) or "Autor desconocido"
        if len(autor) > 80: autor = autor[:77] + "…"
        salida.append({
            "titulo": titulo,
            "descripcion": limpiar(meta.get("ImageDescription", {}).get("value"))[:200],
            "imagen": (info.get("thumburl") or info.get("url") or "").split("?")[0],
            "imagen_credito": f"{autor} ({licencia})",
            "imagen_fuente": info.get("descriptionurl"),
        })
        if len(salida) >= maximo:
            break
    return salida

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("consulta")
    ap.add_argument("--max", type=int, default=5)
    a = ap.parse_args()
    try:
        res = buscar(a.consulta, a.max)
    except Exception as e:
        print(f"ERROR al consultar Wikimedia Commons: {e}", file=sys.stderr)
        sys.exit(2)
    if not res:
        print("Sin resultados con licencia libre. Pruebe otra consulta (más general o en inglés).")
        return
    for i, c in enumerate(res, 1):
        print(f"\n[{i}] {c['titulo']}\n    {c['descripcion']}")
        print(f'imagen: "{c["imagen"]}"')
        print(f'imagen_credito: "{c["imagen_credito"]}"')
        print(f'imagen_fuente: "{c["imagen_fuente"]}"')
        print('imagen_alt: "Describa en una frase lo que se ve en la foto"')

if __name__ == "__main__":
    main()
