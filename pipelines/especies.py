"""Catálogo das espécies que aparecem na fenologia: grupo, estatuto IUCN, nome português, nome
científico e fotografia — com poucos pedidos.

Uso: python especies.py <pasta_brutos> [--grupos]
  --grupos: só recalcula grupos e IUCN sobre o especies.json já gravado (sem Wikidata nem nomes)

- grupo (aves, plantas, cogumelos, borboletas…): uma faceta do GBIF por grupo (~16 pedidos);
- estatuto IUCN: uma faceta por categoria (CR, EN, VU, NT);
- nome português, nome científico, fotografia: Wikidata (CC0), em lotes de 300, pela ligação
  Wikidata → GBIF (propriedade P846); as fotografias são do Wikimedia Commons (licença de cada ficheiro);
- só as espécies sem nada na Wikidata pedem o nome científico ao GBIF, uma a uma.
"""
import json
import sys
import time
from pathlib import Path
from urllib.parse import unquote

import requests

from fenologia import FILTROS
from gbif import UA, Gbif

LIMIAR = 10  # observações em Portugal desde 2000: abaixo disto, a espécie não entra no catálogo

# (grupo, nome do táxon no GBIF, categoria) — do mais específico para o mais geral: a 1.ª que bate ganha
GRUPOS = [
    ("borboletas", "Lepidoptera", "ORDER"),
    ("libélulas", "Odonata", "ORDER"),
    ("abelhas e vespas", "Hymenoptera", "ORDER"),
    ("escaravelhos", "Coleoptera", "ORDER"),
    ("insectos", "Insecta", "CLASS"),
    ("aranhas", "Arachnida", "CLASS"),
    ("aves", "Aves", "CLASS"),
    ("mamíferos", "Mammalia", "CLASS"),
    ("anfíbios", "Amphibia", "CLASS"),
    ("répteis", "Squamata", "CLASS"),  # no GBIF actual são classes, não ordens
    ("répteis", "Testudines", "CLASS"),
    ("tubarões e raias", "Elasmobranchii", "CLASS"),
    ("crustáceos", "Malacostraca", "CLASS"),
    ("moluscos", "Mollusca", "PHYLUM"),
    ("estrelas e ouriços-do-mar", "Echinodermata", "PHYLUM"),
    ("anémonas e medusas", "Cnidaria", "PHYLUM"),
    ("ascídias", "Ascidiacea", "CLASS"),  # cordados, mas não peixes
    ("peixes", "Chordata", "PHYLUM"),  # o que sobra dos cordados (o GBIF actual não dá classe aos peixes ósseos)
    ("cogumelos e fungos", "Fungi", "KINGDOM"),
    ("plantas", "Plantae", "KINGDOM"),
    ("algas", "Chromista", "KINGDOM"),
]
IUCN = ["CR", "EN", "VU", "NT"]


def ler_fenologia(pasta):
    total = {}
    for f in sorted(pasta.glob("fenologia_*.json")):
        for m in json.loads(f.read_text(encoding="utf-8"))["meses"].values():
            for k, n in m["especies"].items():
                total[k] = total.get(k, 0) + n
    return total


def grupos(g, chaves):
    filtros = {k: v for k, v in FILTROS.items() if k != "year"}
    out = {}
    for grupo, nome, rank in GRUPOS:
        m = g.get("species/match", name=nome, rank=rank, strict="true")
        chave_taxon = m.get("usageKey")
        if not chave_taxon or m.get("rank") != rank:
            print(f"  ⚠ sem táxon para {nome} ({rank}) — grupo {grupo} fica de fora", flush=True)
            continue
        _, contagens = g.facetas("speciesKey", taxonKey=chave_taxon, **filtros)
        n = 0
        for k, _ in contagens:
            if k in chaves and k not in out:
                out[k] = grupo
                n += 1
        print(f"  {grupo:28} +{n}", flush=True)
    return out


def iucn(g, chaves):
    filtros = {k: v for k, v in FILTROS.items() if k != "year"}
    out = {}
    for cat in IUCN:
        _, contagens = g.facetas("speciesKey", iucnRedListCategory=cat, **filtros)
        for k, _ in contagens:
            if k in chaves:
                out[k] = cat
    return out


def wikidata(chaves):
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/sparql-results+json"})
    out = {}
    lista = sorted(chaves)
    for i in range(0, len(lista), 300):
        valores = " ".join(f'"{k}"' for k in lista[i:i + 300])
        q = f"""SELECT ?gbif ?cientifico ?pt ?ptbr ?imagem WHERE {{
  VALUES ?gbif {{ {valores} }}
  ?item wdt:P846 ?gbif .
  OPTIONAL {{ ?item wdt:P225 ?cientifico }}
  OPTIONAL {{ ?item rdfs:label ?pt FILTER(lang(?pt) = "pt") }}
  OPTIONAL {{ ?item rdfs:label ?ptbr FILTER(lang(?ptbr) = "pt-br") }}
  OPTIONAL {{ ?item wdt:P18 ?imagem }}
}}"""
        for tentativa in range(5):
            r = s.post("https://query.wikidata.org/sparql", data={"query": q}, timeout=120)
            if r.status_code == 200:
                break
            time.sleep(30 * (tentativa + 1))
        r.raise_for_status()
        for b in r.json()["results"]["bindings"]:
            k = b["gbif"]["value"]
            d = out.setdefault(k, {})
            if "cientifico" in b:
                d.setdefault("cientifico", b["cientifico"]["value"])
            nome = (b.get("pt") or b.get("ptbr") or {}).get("value")
            # a Wikidata usa o nome científico como rótulo quando não há nome comum — isso não é nome português
            if nome and nome != d.get("cientifico"):
                d.setdefault("nome", nome)
            if "imagem" in b:
                # a Wikidata dá o URL com o nome já codificado («Ficedula%20hypoleuca…»): guarda-se o nome
                # verdadeiro, e a app codifica-o uma vez só
                d.setdefault("imagem", unquote(b["imagem"]["value"].rsplit("/", 1)[-1]))
        print(f"  Wikidata {min(i + 300, len(lista))}/{len(lista)}", flush=True)
        time.sleep(1)
    return out


def so_grupos(pasta):
    f = pasta / "especies.json"
    especies = json.loads(f.read_text(encoding="utf-8"))
    g = Gbif()
    print("grupos:", flush=True)
    gr = grupos(g, set(especies))
    iu = iucn(g, set(especies))
    for k, e in especies.items():
        e["grupo"], e["iucn"] = gr.get(k, "outros"), iu.get(k)
    f.write_text(json.dumps(especies, ensure_ascii=False), encoding="utf-8")
    print(f"{len(especies)} espécies · {len(iu)} ameaçadas ou quase", flush=True)


def main():
    pasta = Path(sys.argv[1])
    if "--grupos" in sys.argv:
        return so_grupos(pasta)
    total = ler_fenologia(pasta)
    chaves = {k for k, n in total.items() if n >= LIMIAR}
    print(f"{len(total)} espécies na fenologia, {len(chaves)} com ≥ {LIMIAR} observações", flush=True)
    g = Gbif()
    print("grupos:", flush=True)
    gr = grupos(g, chaves)
    print("IUCN:", flush=True)
    iu = iucn(g, chaves)
    print("Wikidata:", flush=True)
    wd = wikidata(chaves)
    faltam = [k for k in chaves if "cientifico" not in wd.get(k, {})]
    print(f"nomes científicos ao GBIF: {len(faltam)}", flush=True)
    for k in faltam:
        j = g.get(f"species/{k}")
        wd.setdefault(k, {})["cientifico"] = j.get("canonicalName") or j.get("scientificName")
    especies = {
        k: {"cientifico": wd.get(k, {}).get("cientifico"), "nome": wd.get(k, {}).get("nome"),
            "grupo": gr.get(k, "outros"), "iucn": iu.get(k), "imagem": wd.get(k, {}).get("imagem"),
            "observacoes": total[k]}
        for k in chaves
    }
    (pasta / "especies.json").write_text(json.dumps(especies, ensure_ascii=False), encoding="utf-8")
    com_nome = sum(1 for e in especies.values() if e["nome"])
    print(f"{len(especies)} espécies · {com_nome} com nome português · "
          f"{sum(1 for e in especies.values() if e['imagem'])} com fotografia · "
          f"{len(iu)} ameaçadas ou quase", flush=True)


if __name__ == "__main__":
    main()

