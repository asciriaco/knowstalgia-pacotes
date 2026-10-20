"""Monta os pacotes de região que a app descarrega: um JSON por região, servido pelo GitHub Pages.

Uso: python montar.py <pasta_brutos> <pasta_docs> [cache_dos_nomes]

Formato (versão 1) de docs/regioes/<regiao>.json:
  {"versao": 1, "regiao": "lisboa", "nome": "Lisboa", "gerado": "AAAA-MM-DD",
   "totais": [12 inteiros: observações de todas as espécies em cada mês — o esforço de observação],
   "especies": [[gbif, nome_pt, cientifico, grupo, iucn, imagem, [12 contagens]], ...]}   (por ordem de observações)

JSON e não SQLite (como previa a arquitectura) porque o sqflite não funciona na versão web da app.
"""
import datetime
import json
import sys
from pathlib import Path

LIMIAR_REGIAO = 5  # observações da espécie na região (todos os meses) para entrar no pacote
MINIMO_ESPECIES = 500  # abaixo disto numa região, os dados vieram estragados
FONTES = ("Observações: GBIF.org (CC BY 4.0 / CC0 / CC BY-NC, por registo; uso não-comercial). "
          "Nomes e fotografias: Wikidata (CC0) e Wikimedia Commons (licença de cada ficheiro).")


def minuscula(nome):
    """A Wikidata escreve «Felosa-comum», o GBIF «estorninho-comum»: na app vão todos como nos guias de campo."""
    return nome[0].lower() + nome[1:] if nome else nome


def pacote_regiao(feno, especies, limiar=LIMIAR_REGIAO):
    meses = feno["meses"]
    totais = [meses[str(m)]["total"] for m in range(1, 13)]
    linhas = []
    for k, e in especies.items():
        contagens = [meses[str(m)]["especies"].get(k, 0) for m in range(1, 13)]
        if sum(contagens) >= limiar:
            linhas.append([int(k), minuscula(e.get("nome")),e.get("cientifico"), e.get("grupo"), e.get("iucn"),
                           e.get("imagem"), contagens])
    linhas.sort(key=lambda l: -sum(l[6]))
    return {"versao": 1, "regiao": feno["regiao"], "nome": feno["nome"],
            "gerado": datetime.date.today().isoformat(), "fontes": FONTES, "totais": totais, "especies": linhas}


def main():
    brutos, docs = Path(sys.argv[1]), Path(sys.argv[2])
    especies = json.loads((brutos / "especies.json").read_text(encoding="utf-8"))
    if len(sys.argv) > 3 and Path(sys.argv[3]).exists():  # os nomes do GBIF (nomes.py), mesmo a meio
        vern = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        for k, e in especies.items():
            if not e.get("nome") and vern.get(k):
                e["nome"] = vern[k]
    print(f"{sum(1 for e in especies.values() if e.get('nome'))} de {len(especies)} espécies com nome português",
          flush=True)
    (docs / "regioes").mkdir(parents=True, exist_ok=True)
    indice = []
    for f in sorted(brutos.glob("fenologia_*.json")):
        feno = json.loads(f.read_text(encoding="utf-8"))
        p = pacote_regiao(feno, especies)
        # a região mais pobre (Viseu) tem milhares de espécies: muito menos é o GBIF a falhar, não a natureza.
        # Falha alto em vez de publicar um pacote vazio por cima do bom.
        if len(p["especies"]) < MINIMO_ESPECIES:
            raise SystemExit(f"{p['nome']}: só {len(p['especies'])} espécies — abaixo de {MINIMO_ESPECIES}, nada publicado")
        destino = docs / "regioes" / f"{p['regiao']}.json"
        destino.write_text(json.dumps(p, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        tam = destino.stat().st_size
        indice.append({"regiao": p["regiao"], "nome": p["nome"], "especies": len(p["especies"]), "bytes": tam})
        print(f"{p['nome']:18} {len(p['especies']):5} espécies · {tam / 1024:6.0f} KB", flush=True)
    (docs / "indice.json").write_text(json.dumps(
        {"versao": 1, "gerado": datetime.date.today().isoformat(), "fontes": FONTES, "regioes": indice},
        ensure_ascii=False, indent=1), encoding="utf-8")
    (docs / ".nojekyll").write_text("", encoding="utf-8")


if __name__ == "__main__":
    main()
