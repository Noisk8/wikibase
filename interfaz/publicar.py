#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import re
import subprocess
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener


FAILED_SUMMARY = "Personalizar la portada de Wikibase WMCO"
PREVIEW_TITLE = "Proyecto:Vista previa de la portada WMCO"
PREVIEW_SUMMARY = "Preparar vista previa de la portada WMCO"
LEARNING_LINKS = (("Tutoriales", "Tutoriales"), ("Crear", "Crear propiedades y elementos"))


def read_api(opener, base_url, **params):
    url = base_url + "/w/api.php?" + urlencode({"format": "json", "formatversion": 2, **params})
    with opener.open(url, timeout=15) as response:
        payload = json.load(response)
    if "error" in payload:
        raise SystemExit(payload["error"]["info"])
    return payload["query"]


def revisions(opener, base_url, **params):
    page = read_api(
        opener, base_url, action="query", prop="revisions",
        rvprop="ids|comment|content", rvslots="main", **params,
    )["pages"][0]
    return page.get("revisions", [])


def revision_text(revision):
    return revision["slots"]["main"]["content"]


def remove_section(text, start, end):
    if start not in text and end not in text:
        return text
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) >= text.index(end):
        raise SystemExit(f"Marcadores inesperados. Revisa {start}")
    before, section = text.split(start, 1)
    _, after = section.split(end, 1)
    if not after.strip():
        return before.rstrip()
    return before + after.lstrip("\n")


def edit(root, title, content, summary):
    print(f"Guardando {title}", flush=True)
    subprocess.run(
        ["docker", "compose", "exec", "-T", "wikibase", "php",
         "/var/www/html/maintenance/run.php", "edit", "-s", summary, title],
        cwd=root, input=content, text=True, check=True,
    )


def add_learning_links(content):
    match = re.search(r'<div\b[^>]*class="[^"]*\bwmco-learn\b[^"]*"[^>]*>.*?<ul>(.*?)</ul>', content, re.S)
    if not match:
        raise SystemExit("No encontré la lista de la tarjeta Aprender en la portada actual.")
    entries = "".join(
        f"\n<li>[[{title}|{label}]]</li>"
        for title, label in LEARNING_LINKS
        if not re.search(r"\[\[" + re.escape(title) + r"(?:\||\]\])", match[1])
    )
    return content[:match.start(1)] + entries + content[match.start(1):]


def main(learning_links=False):
    assets = Path(__file__).resolve().parent
    root = assets.parent
    settings = json.loads(subprocess.check_output(
        ["docker", "compose", "config", "--format", "json"], cwd=root, text=True,
    ))["services"]["wikibase"]["environment"]
    base_url = settings["MW_WG_SERVER"]
    opener = build_opener(ProxyHandler({}))
    mainpage = read_api(opener, base_url, action="query", meta="siteinfo")["general"]["mainpage"]

    if learning_links:
        pages = read_api(
            opener, base_url, action="query", titles="|".join(title for title, _ in LEARNING_LINKS),
        )["pages"]
        missing = [page["title"] for page in pages if "missing" in page]
        if missing:
            raise SystemExit("No se añadieron enlaces. Faltan las páginas: " + ", ".join(missing))
        current = revisions(opener, base_url, titles=mainpage, rvlimit=1)
        content = revision_text(current[0])
        updated = add_learning_links(content)
        if updated != content:
            edit(root, mainpage, updated, "Añadir Tutoriales y Crear a la tarjeta Aprender")
            saved = revisions(opener, base_url, titles=mainpage, rvlimit=1)
            if revision_text(saved[0]).rstrip() != updated.rstrip():
                raise SystemExit("No se pudo verificar la edición de la portada.")
        print("La tarjeta Aprender incluye Tutoriales y Crear.")
        return

    history = revisions(opener, base_url, titles=mainpage, rvlimit=10)
    failed = next((rev for rev in history if rev.get("comment") == FAILED_SUMMARY), None)
    if failed and failed["revid"] == history[0]["revid"]:
        original = revisions(opener, base_url, revids=failed["parentid"])
        if len(original) != 1:
            raise SystemExit("No se pudo recuperar la revisión anterior de la portada.")
        edit(root, mainpage, revision_text(original[0]), "Restaurar la portada y sus enlaces anteriores")
        restored = revisions(opener, base_url, titles=mainpage, rvlimit=1)
        if not restored or revision_text(restored[0]) != revision_text(original[0]):
            raise SystemExit("No se pudo verificar la restauración de la portada.")
    elif history and 'class="wmco-portal"' in revision_text(history[0]):
        raise SystemExit(f"La portada tiene revisiones posteriores. Revisa su historial antes de restaurar: {base_url}/w/index.php?" + urlencode({"title": mainpage, "action": "history"}))

    for title, start, end in (
        ("MediaWiki:Common.css", "/* Inicio de la portada WMCO */", "/* Fin de la portada WMCO */"),
        ("MediaWiki:Sidebar", "<!-- Inicio de los enlaces WMCO -->", "<!-- Fin de los enlaces WMCO -->"),
    ):
        current = revisions(opener, base_url, titles=title, rvlimit=1)
        if current:
            text = revision_text(current[0])
            clean = remove_section(text, start, end)
            if clean != text:
                edit(root, title, clean, "Retirar el bloque añadido por la portada de prueba")

    preview = revisions(opener, base_url, titles=PREVIEW_TITLE, rvlimit=1)
    if preview and preview[0].get("comment") != PREVIEW_SUMMARY:
        raise SystemExit(f"La página {PREVIEW_TITLE} ya tiene contenido editado. Revisa esa página antes de publicar.")

    query_url = settings["WDQS_PUBLIC_FRONTEND_URL"].rstrip("/") + "/"
    qs_url = settings["QUICKSTATEMENTS_PUBLIC_URL"].rstrip("/") + "/"
    portal = (assets / "portada.wiki").read_text(encoding="utf-8")
    portal = portal.replace("__WMCO_QUERY_URL__", query_url).replace("__WMCO_QS_URL__", qs_url)
    edit(root, PREVIEW_TITLE, portal, PREVIEW_SUMMARY)
    print("Vista previa: " + base_url + "/w/index.php?" + urlencode({"title": PREVIEW_TITLE}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--enlaces-aprender", action="store_true")
    try:
        main(learning_links=parser.parse_args().enlaces_aprender)
    except URLError as error:
        raise SystemExit(f"No se pudo acceder a la wiki local: {error.reason}") from None
