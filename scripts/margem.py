#!/usr/bin/env python3
"""Margem de contribuicao por anuncio. Calcula so o que da para calcular.

Entra uma lista de anuncios com preco, taxa, frete, custo e imposto; sai quanto
sobra em cada um, em reais e em percentual.

A regra que manda neste arquivo: **componente que nao veio nao vira zero.**
Zero de custo transforma prejuizo em lucro na tela, e e o tipo de erro que a
pessoa so descobre no fim do mes. Falta um componente, a linha fica sem margem
e o arquivo diz qual faltou.

Zero DECLARADO e diferente de ausente. Quem escreve "frete: 0" esta dizendo que
nao paga frete naquele anuncio, e a conta roda.

Uso:
    python3 margem.py linhas.json
    python3 margem.py linhas.json --capturado-em 2026-10-12T09:00:00-03:00

Cada linha aceita:
    mlb / sku / produto     identificacao (pelo menos um)
    preco                   preco de venda           (obrigatorio)
    custo                   custo do produto         (obrigatorio)
    taxa      ou taxa_pct   comissao do marketplace
    frete                   frete pago pelo vendedor
    imposto   ou imposto_pct

Compatibilidade: Python 3.8+.
"""
import json
import sys
from pathlib import Path

import contrato

BASE = Path(__file__).resolve().parent

COMPONENTES = ("preco", "custo", "taxa", "frete", "imposto")

EXPLICACAO = {
    "preco": "o preço de venda não veio — sem ele não há margem para calcular",
    "custo": "o custo deste produto não está na sua planilha",
    "taxa": "a comissão do marketplace não foi informada nem como valor nem como percentual",
    "frete": "o frete pago por você não foi informado; se você não paga frete neste "
             "anúncio, escreva 0 em vez de deixar vazio",
    "imposto": "o imposto não foi informado nem como valor nem como percentual",
}


def _num(v):
    """Numero ou None. String vazia e texto NAO viram zero."""
    if v is None or v is True or v is False:
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    return None


def _componente(linha, nome, preco):
    """Devolve (valor, origem). origem: 'valor', 'percentual' ou None."""
    direto = _num(linha.get(nome))
    if direto is not None:
        return direto, "valor"
    pct = _num(linha.get(nome + "_pct"))
    if pct is not None and preco is not None:
        return round(preco * pct / 100.0, 2), "percentual"
    return None, None


def identificar(linha):
    for campo in ("mlb", "sku", "produto"):
        v = linha.get(campo)
        if v not in (None, ""):
            return str(v)
    return None


def calcular(linhas):
    """Devolve (itens, faltando, lacunas, avisos, resumo)."""
    if not isinstance(linhas, list):
        raise ValueError("o arquivo precisa conter uma LISTA de anúncios")
    if not linhas:
        raise ValueError("a lista está vazia")

    itens = []
    faltou = {}
    sem_identificacao = 0

    for i, linha in enumerate(linhas, 1):
        if not isinstance(linha, dict):
            raise ValueError("a linha %d não é um objeto" % i)
        nome = identificar(linha)
        if nome is None:
            sem_identificacao += 1
            nome = "linha %d" % i

        preco = _num(linha.get("preco"))
        partes = {"preco": preco}
        origens = {}
        for c in ("custo", "taxa", "frete", "imposto"):
            valor, origem = _componente(linha, c, preco)
            partes[c] = valor
            if origem:
                origens[c] = origem

        ausentes = [c for c in COMPONENTES if partes[c] is None]
        for c in ausentes:
            faltou.setdefault(c, 0)
            faltou[c] += 1

        item = {
            "anuncio": nome,
            "preco": preco,
            "custo": partes["custo"],
            "taxa": partes["taxa"],
            "frete": partes["frete"],
            "imposto": partes["imposto"],
        }

        if ausentes:
            item["margem"] = None
            item["margem_pct"] = None
            item["sem_margem_porque"] = ausentes
        else:
            margem = round(preco - partes["taxa"] - partes["frete"]
                           - partes["custo"] - partes["imposto"], 2)
            item["margem"] = margem
            item["margem_pct"] = round(margem / preco * 100.0, 2) if preco else None
            item["sem_margem_porque"] = []
        if origens:
            item["calculado_por_percentual"] = sorted(
                c for c, o in origens.items() if o == "percentual")
        itens.append(item)

    com_margem = [i for i in itens if i["margem"] is not None]
    negativos = [i for i in com_margem if i["margem"] < 0]

    faltando, lacunas, avisos = [], {}, []
    for c, quantos in sorted(faltou.items()):
        faltando.append(c)
        lacunas[c] = "%s (faltou em %d de %d anúncio(s))" % (
            EXPLICACAO[c], quantos, len(itens))

    if sem_identificacao:
        avisos.append("%d anúncio(s) vieram sem mlb, sku nem nome — aparecem pela "
                      "posição na lista" % sem_identificacao)
    if negativos:
        avisos.append("%d anúncio(s) com margem NEGATIVA: você paga para vender"
                      % len(negativos))
    if len(com_margem) < len(itens):
        avisos.append("%d de %d anúncio(s) ficaram sem margem por falta de componente"
                      % (len(itens) - len(com_margem), len(itens)))

    soma = round(sum(i["margem"] for i in com_margem), 2) if com_margem else None
    medio = None
    if com_margem:
        precos = sum(i["preco"] for i in com_margem)
        medio = round(soma / precos * 100.0, 2) if precos else None

    resumo = {
        "anuncios": len(itens),
        "com_margem_calculada": len(com_margem),
        "margem_total": soma,
        "margem_media_pct": medio,
        "anuncios_no_prejuizo": len(negativos),
    }
    return itens, faltando, lacunas, avisos, resumo


def _main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    entrada = Path(args[0])
    if not entrada.is_absolute():
        entrada = BASE / args[0]
    if not entrada.exists():
        print("Nao achei %s nesta pasta." % entrada.name)
        return 1

    capturado = None
    if "--capturado-em" in args:
        pos = args.index("--capturado-em")
        if pos + 1 < len(args):
            capturado = args[pos + 1]

    linhas = json.loads(entrada.read_text(encoding="utf-8"))
    itens, faltando, lacunas, avisos, resumo = calcular(linhas)

    contrato.gravar("prometheus-margem", conta=None, periodo=None, resumo=resumo,
                    itens=itens, faltando=faltando, lacunas=lacunas, avisos=avisos,
                    fonte="export", capturado_em=capturado, pasta=BASE)

    print("%d anuncio(s) · %d com margem calculada"
          % (resumo["anuncios"], resumo["com_margem_calculada"]))
    if resumo["margem_media_pct"] is not None:
        print("Margem media: %.2f%%" % resumo["margem_media_pct"])
    for i in itens[:5]:
        if i["margem"] is None:
            print("  %-28s sem margem: falta %s"
                  % (str(i["anuncio"])[:28], ", ".join(i["sem_margem_porque"])))
        else:
            print("  %-28s R$ %9.2f  (%.1f%%)"
                  % (str(i["anuncio"])[:28], i["margem"], i["margem_pct"] or 0))
    for a in avisos:
        print("  aviso: %s" % a)
    print("\nVeja no painel:  python3 painel.py")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_main())
    except (ValueError, contrato.ContratoInvalido) as e:
        sys.exit("PARADO: %s" % e)
