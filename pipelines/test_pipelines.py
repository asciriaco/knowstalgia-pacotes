"""Testes dos pipelines (sem rede). Correr: python -m pytest -q (na pasta pipelines)."""
import pytest

import gbif
from montar import pacote_regiao
from regioes import REGIOES


def feno_sintetico():
    meses = {str(m): {"total": 1000 * m, "especies": {}} for m in range(1, 13)}
    for m in (4, 5, 6):
        meses[str(m)]["especies"]["111"] = 50  # «andorinha»: só na Primavera
    meses["1"]["especies"]["222"] = 2  # rara: abaixo do limiar
    return {"regiao": "teste", "nome": "Teste", "meses": meses}


def test_pacote_regiao_filtra_e_ordena():
    esp = {"111": {"nome": "Andorinha","cientifico": "Hirundo rustica", "grupo": "aves"},
           "222": {"nome": None, "cientifico": "Rara rara", "grupo": "plantas"}}
    p = pacote_regiao(feno_sintetico(), esp)
    assert p["totais"] == [1000 * m for m in range(1, 13)]
    assert [l[0] for l in p["especies"]] == [111]  # a rara (2 observações) fica de fora
    assert p["especies"][0][1] == "andorinha"  # minúscula inicial, como nos guias de campo
    assert p["especies"][0][6] ==[0, 0, 0, 50, 50, 50, 0, 0, 0, 0, 0, 0]


def test_20_regioes_com_slugs_unicos():
    assert len(REGIOES) == 20
    assert len({s for s, _ in REGIOES.values()}) == 20


def test_cliente_recua_quando_o_gbif_pede(monkeypatch):
    respostas = iter([429, 429, 200])

    class R:
        def __init__(self, c):
            self.status_code = c

        def json(self):
            return {"ok": True}

        def raise_for_status(self):
            raise AssertionError

    esperas = []
    monkeypatch.setattr(gbif.time, "sleep", lambda s: esperas.append(s))
    g = gbif.Gbif(intervalo=0)
    monkeypatch.setattr(g.s, "get", lambda *a, **k: R(next(respostas)))
    assert g.get("x") == {"ok": True}
    assert esperas[:2] == [30.0, 60.0]  # recuo exponencial


def test_cliente_desiste_com_erro_claro(monkeypatch):
    monkeypatch.setattr(gbif.time, "sleep", lambda s: None)
    g = gbif.Gbif(intervalo=0, tentativas=2)

    class R:
        status_code = 503

    monkeypatch.setattr(g.s, "get", lambda *a, **k: R())
    with pytest.raises(RuntimeError):
        g.get("x")


def test_escolher_nome_portugues():
    from nomes import escolher
    v = [{"vernacularName": "Toutinegra-de-barrete-preto", "language": "por", "source": "EUNIS Biodiversity Database"},
         {"vernacularName": "toutinegra-de-barrete", "language": "por", "source": "Catalogue of Life"},
         {"vernacularName": "Blackcap", "language": "eng", "source": "x"},
         {"vernacularName": "Sylvia atricapilla", "language": "por", "source": "x"}]
    assert escolher(v, "Sylvia atricapilla") == "toutinegra-de-barrete-preto"  # a EUNIS pesa mais
    assert escolher(v[2:], "Sylvia atricapilla") is None  # inglês e o científico disfarçado não servem
    v2 = [{"vernacularName": "Cartaxo comum", "language": "por", "source": "a"},
          {"vernacularName": "cartaxo-comum", "language": "por", "source": "b"},
          {"vernacularName": "cartaxo", "language": "por", "source": "c"}]
    assert escolher(v2, "Saxicola rubicola") == "cartaxo-comum"  # 2 fontes, grafia com hífen
