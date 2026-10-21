# knowstalgia-pacotes

Os pacotes de dados abertos que a app **Knowstalgia** descarrega: o que anda por aí, mês a mês, em
cada uma das 20 regiões de Portugal (18 distritos, Açores e Madeira) — aves, plantas, cogumelos,
borboletas, peixes e o resto.

Servidos pelo GitHub Pages: `https://asciriaco.github.io/knowstalgia-pacotes/regioes/<regiao>.json`
(lista em [`docs/indice.json`](docs/indice.json)). Refeitos no dia 3 de cada mês
([`mensal.yml`](.github/workflows/mensal.yml)).

**Este repositório só tem dados abertos.** Nada dos almanaques (Borda d'Água, Seringador) vem para
aqui — isso vive num repositório privado.

## Formato (versão 1)

```json
{"versao": 1, "regiao": "lisboa", "nome": "Lisboa", "gerado": "2026-10-20", "fontes": "…",
 "totais": [12 inteiros],
 "especies": [[gbif, nome_pt, cientifico, grupo, iucn, imagem, [12 contagens]], …]}
```

- `totais[m]` — observações **de todas as espécies** na região no mês `m` (Janeiro = 0): o esforço
  de observação. Há muito mais gente a observar em Abril do que em Janeiro, por isso a app compara
  **frequências** (`contagem ÷ total`), nunca contagens.
- `gbif` — chave da espécie no GBIF (`https://www.gbif.org/species/<gbif>`).
- `nome_pt` — nome português da Wikidata ou, sem ele, o nome vernáculo do GBIF mais apoiado pelas fontes (a EUNIS, europeia, pesa mais); `null` quando não há (nunca o nome científico repetido). Os do GBIF ficam em `nomes/` para não se repetirem os pedidos. Cobertura em 2026-10-20: 3 196 de 8 254 espécies (39%) — 1 035 da Wikidata, 2 161 do GBIF; o resto são sobretudo insectos, líquenes e plantas pequenas sem nome comum em fonte aberta.
- `grupo` — aves, plantas, cogumelos e fungos, borboletas, libélulas, abelhas e vespas,
  escaravelhos, insectos, aranhas, mamíferos, anfíbios, répteis, tubarões e raias, crustáceos,
  moluscos, estrelas e ouriços-do-mar, anémonas e medusas, ascídias, peixes, algas, outros.
- `iucn` — `CR`, `EN`, `VU`, `NT` ou `null` (Lista Vermelha da IUCN, pelo GBIF).
- `imagem` — nome de um ficheiro do Wikimedia Commons, ou `null`.

Uma espécie entra no pacote de uma região com **5 ou mais observações** lá, e no catálogo com
**10 ou mais** em Portugal.

## Como se faz

```bash
cd pipelines
python fenologia.py ../brutos        # 260 pedidos ao GBIF: região × mês (retoma onde parou)
python especies.py ../brutos         # grupos, IUCN, nomes e fotografias (Wikidata)
python especies.py ../brutos --grupos  # só refaz grupos e IUCN, sem repetir a Wikidata
python nomes.py ../brutos ../nomes/vernaculos_gbif.json  # nomes PT do GBIF para as que a Wikidata não tem
python montar.py ../brutos ../docs ../nomes/vernaculos_gbif.json   # os pacotes
python -m pytest -q
```

O GBIF corta quem pede depressa (`Too many API requests`): o cliente (`gbif.py`) espera 1,2 s entre
pedidos e recua de 30 s a 15 min quando é travado.

**Filtros** das observações: Portugal, desde 2000, `HUMAN_OBSERVATION` e `MACHINE_OBSERVATION`
(seres vivos vistos, não colecções de museu nem fósseis), presentes, sem problemas de coordenadas.
As regiões são o nível 1 do GADM (`PRT.1_1` Aveiro … `PRT.20_1` Viseu); `regioes.py` confirma os
nomes no arranque e pára se o GADM mudar a numeração.

## Fontes e licenças

| | Licença |
|---|---|
| Observações — [GBIF.org](https://www.gbif.org), API de ocorrências (consulta por facetas) | CC0, CC BY 4.0 e **CC BY-NC 4.0**, registo a registo |
| Nomes portugueses e científicos — [Wikidata](https://www.wikidata.org) | CC0 |
| Nomes vernáculos — GBIF (Catalogue of Life, EUNIS, ITIS…) | CC BY 4.0 / CC0, por lista |
| Fotografias — [Wikimedia Commons](https://commons.wikimedia.org) | a de cada ficheiro (a página do ficheiro diz qual) |
| Estatuto de ameaça — Lista Vermelha da IUCN, tal como o GBIF a publica | uso não-comercial |
| Regiões — [GADM](https://gadm.org) nível 1, tal como o GBIF o aplica | uso não-comercial |

⚠ **Os pacotes misturam registos CC BY-NC e o estatuto da IUCN, que são não-comerciais.** A app é,
por agora, não-comercial. Se deixar de o ser: pedir as facetas com
`license=CC0_1_0&license=CC_BY_4_0` e tirar o campo `iucn`.

Citação: *GBIF.org (2026), consulta da API de ocorrências por facetas, filtros acima,
https://www.gbif.org*. As consultas por facetas não geram DOI; se for preciso um DOI citável,
faz-se um descarregamento pelo portal com os mesmos filtros.
