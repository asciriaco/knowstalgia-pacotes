"""Cliente educado da API do GBIF: um pedido de cada vez, com intervalo, e espera crescente quando
o GBIF pede para abrandar.

⚠ O GBIF bloqueia («Too many API requests») quem dispara pedidos seguidos — aconteceu a 2026-10-13
com 20 pedidos sem pausa. Por isso: intervalo mínimo entre pedidos, User-Agent identificado, e
recuo exponencial nos 429/503.
"""
import time

import requests

API = "https://api.gbif.org/v1"
UA = "Almanact/0.1 (almanaque natural, nao-comercial; github.com/asciriaco)"


class Gbif:
    def __init__(self, intervalo=1.2, tentativas=8):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = UA
        self.intervalo = intervalo
        self.tentativas = tentativas
        self._ultimo = 0.0
        self.pedidos = 0

    def get(self, caminho, **params):
        espera = 30.0
        for n in range(self.tentativas):
            pausa = self.intervalo - (time.monotonic() - self._ultimo)
            if pausa > 0:
                time.sleep(pausa)
            self._ultimo = time.monotonic()
            try:
                r = self.s.get(f"{API}/{caminho}", params=params, timeout=300)
            except requests.RequestException:
                r = None
            self.pedidos += 1
            if r is not None and r.status_code == 200:
                return r.json()
            if r is not None and r.status_code not in (429, 500, 502, 503, 504):
                r.raise_for_status()
            estado = "sem resposta" if r is None else r.status_code
            print(f"  … GBIF {estado} em {caminho}: espero {espera:.0f} s", flush=True)
            time.sleep(espera)
            espera = min(espera * 2, 900)
        raise RuntimeError(f"GBIF não respondeu: {caminho} {params}")

    def facetas(self, campo, limite=100000, **filtros):
        """→ (total de ocorrências que cumprem os filtros, [(valor, contagem)])"""
        j = self.get("occurrence/search", limit=0, facet=campo, **{f"{campo}.facetLimit": limite}, **filtros)
        contagens = [(c["name"], c["count"]) for c in (j.get("facets") or [{}])[0].get("counts", [])]
        return j["count"], contagens
