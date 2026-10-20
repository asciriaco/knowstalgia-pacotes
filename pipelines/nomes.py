"""Nomes portugueses para as espécies que a Wikidata deixou sem nome: os nomes vernáculos do GBIF
(Catalogue of Life, EUNIS, ITIS…), um pedido por espécie, das mais observadas para as menos.

Uso: python nomes.py <pasta_brutos> <ficheiro_cache>

O cache (chave GBIF → nome, ou null quando não há) fica no repositório: os nomes não mudam de mês para
mês, por isso cada actualização só pergunta pelas espécies novas. Grava de 100 em 100 e retoma onde parou.
"""
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

from gbif import Gbif

# A EUNIS é a base europeia: português de Portugal («toutinegra», não «felosa-de-cabeça-preta» do Brasil)
PESO_FONTE = {"EUNIS": 3}


def _norm(s):
    s = unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()
    return "-".join(s.replace("-", " ").split())


def escolher(vernaculos, cientifico):
    """O nome português mais apoiado pelas fontes; None se não houver nenhum que preste."""
    pontos, formas = defaultdict(float), defaultdict(list)
    genero = (cientifico or "").split(" ")[0].lower()
    for v in vernaculos:
        if v.get("language") != "por":
            continue
        nome = " ".join((v.get("vernacularName") or "").split())
        if len(nome) < 3 or (genero and genero in nome.lower()) or _norm(nome) == _norm(cientifico or ""):
            continue  # vazio, ou é o nome científico disfarçado
        n = _norm(nome)
        fonte = v.get("source") or ""
        pontos[n] += 1 + sum(p for f, p in PESO_FONTE.items() if f in fonte)
        formas[n].append(nome)
    if not pontos:
        return None
    melhor = max(pontos, key=lambda n: (pontos[n], -len(n)))
    # das formas escritas, a que tem hífenes (a grafia dos guias de campo), com minúscula inicial
    forma = max(formas[melhor], key=lambda f: (f.count("-"), f.islower()))
    return forma[0].lower() + forma[1:]


def main():
    brutos, cache_f = Path(sys.argv[1]), Path(sys.argv[2])
    especies = json.loads((brutos / "especies.json").read_text(encoding="utf-8"))
    cache = json.loads(cache_f.read_text(encoding="utf-8")) if cache_f.exists() else {}
    faltam = sorted((k for k, e in especies.items() if not e["nome"] and k not in cache),
                    key=lambda k: -especies[k]["observacoes"])
    print(f"{len(faltam)} espécies por perguntar ({len(cache)} já no cache)", flush=True)
    g = Gbif()
    for i, k in enumerate(faltam, 1):
        j = g.get(f"species/{k}/vernacularNames", limit=300)
        cache[k] = escolher(j.get("results", []), especies[k]["cientifico"])
        if i % 100 == 0 or i == len(faltam):
            cache_f.parent.mkdir(parents=True, exist_ok=True)
            cache_f.write_text(json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
            print(f"  {i}/{len(faltam)} · com nome: {sum(1 for v in cache.values() if v)}", flush=True)
    n = 0
    for k, e in especies.items():
        if not e["nome"] and cache.get(k):
            e["nome"], n = cache[k], n + 1
    (brutos / "especies.json").write_text(json.dumps(especies, ensure_ascii=False), encoding="utf-8")
    print(f"{n} nomes acrescentados · {sum(1 for e in especies.values() if e['nome'])} de {len(especies)} com nome",
          flush=True)


if __name__ == "__main__":
    main()
