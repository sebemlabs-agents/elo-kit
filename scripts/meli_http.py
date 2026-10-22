#!/usr/bin/env python3
"""Cliente tolerante: devolve (status, corpo) em vez de abortar, com nova
tentativa em 429 e 5xx. Para coletas longas, onde uma falha pontual nao deve
derrubar o trabalho todo.

Somente leitura, como o meli.py: so faz GET.

Compatibilidade: Python 3.8+.
"""
import json
import time
import urllib.error
import urllib.request

import meli
import seguro

API = "https://api.mercadolibre.com"
_tok = {"v": None, "t": 0}


def token():
    if not _tok["v"] or time.time() - _tok["t"] > 1800:
        _tok["v"] = meli.get_access_token()
        _tok["t"] = time.time()
    return _tok["v"]


def pedir(path, headers=None, tentativas=4):
    """GET tolerante. Devolve (status, corpo). status -1 = falha de rede."""
    url = API + path
    for i in range(tentativas):
        h = {"Authorization": "Bearer " + token(), "Accept": "application/json"}
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, method="GET", headers=h)
        try:
            with seguro.abrir(req, timeout=60) as r:
                bruto = r.read().decode("utf-8", "replace")
                return r.status, (json.loads(bruto) if bruto.strip() else {})
        except urllib.error.HTTPError as e:
            try:
                corpo = json.loads(e.read().decode("utf-8", "replace"))
            except Exception:
                corpo = {}
            if e.code in (429, 500, 502, 503, 504) and i < tentativas - 1:
                time.sleep(1.5 * (i + 1))
                continue
            if e.code == 401 and i < tentativas - 1:
                _tok["v"] = None
                time.sleep(0.5)
                continue
            return e.code, corpo
        except Exception as e:
            if i < tentativas - 1:
                time.sleep(1.0 * (i + 1))
                continue
            return -1, {"erro": str(e)}
    return -1, {}
