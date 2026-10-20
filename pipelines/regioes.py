"""As 20 regiões dos pacotes: os 18 distritos do continente, os Açores e a Madeira, com o código GADM
nível 1 que o GBIF usa (ordem alfabética do GADM — confirmada contra o GBIF por `confirmar()`)."""

REGIOES = {
    "PRT.1_1": ("aveiro", "Aveiro"),
    "PRT.2_1": ("acores", "Açores"),
    "PRT.3_1": ("beja", "Beja"),
    "PRT.4_1": ("braga", "Braga"),
    "PRT.5_1": ("braganca", "Bragança"),
    "PRT.6_1": ("castelo-branco", "Castelo Branco"),
    "PRT.7_1": ("coimbra", "Coimbra"),
    "PRT.8_1": ("evora", "Évora"),
    "PRT.9_1": ("faro", "Faro"),
    "PRT.10_1": ("guarda", "Guarda"),
    "PRT.11_1": ("leiria", "Leiria"),
    "PRT.12_1": ("lisboa", "Lisboa"),
    "PRT.13_1": ("madeira", "Madeira"),
    "PRT.14_1": ("portalegre", "Portalegre"),
    "PRT.15_1": ("porto", "Porto"),
    "PRT.16_1": ("santarem", "Santarém"),
    "PRT.17_1": ("setubal", "Setúbal"),
    "PRT.18_1": ("viana-do-castelo", "Viana do Castelo"),
    "PRT.19_1": ("vila-real", "Vila Real"),
    "PRT.20_1": ("viseu", "Viseu"),
}

# nomes do GADM tal como o GBIF os devolve (sem acentos nalguns casos), para a confirmação
_GADM = {"Azores": "Açores", "Braganca": "Bragança", "Evora": "Évora", "Santarem": "Santarém",
         "Setubal": "Setúbal", "Madeira": "Madeira"}


def confirmar(gbif):
    """Confirma, com um registo de cada região, que o código GADM corresponde ao distrito esperado."""
    erros = []
    for gid, (_, nome) in REGIOES.items():
        j = gbif.get("occurrence/search", gadmLevel1Gid=gid, limit=1)
        lido = j["results"][0]["gadm"]["level1"]["name"]
        if _GADM.get(lido, lido) != nome:
            erros.append(f"{gid}: GBIF diz {lido!r}, esperava {nome!r}")
    if erros:
        raise AssertionError("mapa de regiões errado:\n" + "\n".join(erros))
