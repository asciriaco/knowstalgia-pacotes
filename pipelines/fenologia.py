"""Fenologia: quantas observações de cada espécie há em cada região e mês (GBIF, desde 2000).

Uso: python fenologia.py <pasta_brutos>
Faz 20 regiões × 12 meses = 240 pedidos de facetas (mais 20 para confirmar o mapa de regiões),
devagar (ver gbif.py). Retoma onde parou: as regiões já descarregadas não se repetem.

Cada resposta traz também o TOTAL de observações da região nesse mês — o esforço de observação —,
que serve para corrigir o facto de haver mais gente a observar na Primavera do que no Inverno.
"""
import datetime
import json
import sys
from pathlib import Path

from gbif import Gbif
from regioes import REGIOES, confirmar

FILTROS = {
    "country": "PT",
    "year": f"2000,{datetime.date.today().year}",
    "basisOfRecord": ["HUMAN_OBSERVATION", "MACHINE_OBSERVATION"],  # seres vivos observados, não museus/fósseis
    "occurrenceStatus": "PRESENT",
    "hasGeospatialIssue": "false",
}


def main():
    pasta = Path(sys.argv[1])
    pasta.mkdir(parents=True, exist_ok=True)
    g = Gbif()
    confirmar(g)
    print("mapa de regiões confirmado", flush=True)
    for gid, (slug, nome) in REGIOES.items():
        destino = pasta / f"fenologia_{slug}.json"
        if destino.exists():
            continue
        meses = {}
        for m in range(1, 13):
            total, contagens = g.facetas("speciesKey", gadmLevel1Gid=gid, month=m, **FILTROS)
            meses[m] = {"total": total, "especies": {k: n for k, n in contagens}}
        destino.write_text(json.dumps({"regiao": slug, "nome": nome, "gadm": gid, "filtros": FILTROS,
                                       "obtido": datetime.date.today().isoformat(), "meses": meses}),
                           encoding="utf-8")
        especies = len({k for v in meses.values() for k in v["especies"]})
        print(f"{nome}: {especies} espécies, {sum(v['total'] for v in meses.values()):,} observações · "
              f"{g.pedidos} pedidos", flush=True)


if __name__ == "__main__":
    main()
