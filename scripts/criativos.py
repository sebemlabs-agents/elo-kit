#!/usr/bin/env python3
"""Grava o pacote de conteudo de produto no formato do contrato.

A skill prometheus-criativos produz o conteudo; este script so valida e grava, para o
painel poder desenhar. Nao chama API nenhuma e nao precisa de conta conectada.

Uso:
    python3 criativos.py pacote.json
    python3 criativos.py pacote.json --faltando specs,garantia

O arquivo de entrada e uma LISTA de produtos. Cada produto aceita:
    produto     (obrigatorio) nome curto, como o usuario chama
    titulo      titulo pronto para o anuncio
    descricao   texto da descricao
    beneficios  lista de frases
    objecoes    lista de {"duvida": ..., "resposta": ...}
    specs       objeto de pares, ex.: {"capacidade": "70 kg"}

Campo que voce nao tem: deixe de fora e declare em --faltando. Nunca preencha
com suposicao — o painel sabe mostrar lacuna.

Compatibilidade: Python 3.8+.
"""
import json
import sys
from pathlib import Path

import contrato

BASE = Path(__file__).resolve().parent

EXPLICACAO = {
    "titulo": "o título não foi produzido para algum produto",
    "descricao": "a descrição não foi produzida para algum produto",
    "beneficios": "faltou informação do produto para escrever os benefícios",
    "objecoes": "não foram informadas as dúvidas que seguram a compra",
    "specs": "as especificações técnicas não foram informadas",
    "preco": "o preço não foi informado",
    "garantia": "a garantia não foi informada",
}


def preparar(produtos):
    """Normaliza a lista e devolve (itens, avisos). Nao inventa campo."""
    if not isinstance(produtos, list):
        raise ValueError("o arquivo precisa conter uma LISTA de produtos")
    if not produtos:
        raise ValueError("a lista de produtos esta vazia")

    itens, avisos = [], []
    for i, p in enumerate(produtos, 1):
        if not isinstance(p, dict):
            raise ValueError("produto %d nao e um objeto" % i)
        nome = (p.get("produto") or "").strip()
        if not nome:
            raise ValueError("produto %d esta sem o campo 'produto'" % i)

        item = {"produto": nome}
        for campo in ("titulo", "descricao"):
            item[campo] = p.get(campo) or None
        item["beneficios"] = p.get("beneficios") or []
        item["objecoes"] = p.get("objecoes") or []
        item["specs"] = p.get("specs") or {}

        if not item["titulo"]:
            avisos.append("%s: sem título" % nome)
        if not item["beneficios"]:
            avisos.append("%s: sem benefícios" % nome)
        itens.append(item)
    return itens, avisos


def _main():
    args = [a for a in sys.argv[1:]]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    entrada = Path(args[0])
    if not entrada.is_absolute():
        entrada = BASE / args[0]
    if not entrada.exists():
        print("Nao achei %s nesta pasta." % entrada.name)
        return 1

    faltando = []
    if "--faltando" in args:
        pos = args.index("--faltando")
        if pos + 1 < len(args):
            faltando = [f.strip() for f in args[pos + 1].split(",") if f.strip()]

    produtos = json.loads(entrada.read_text(encoding="utf-8"))
    itens, avisos = preparar(produtos)

    lacunas = {}
    for f in faltando:
        lacunas[f] = EXPLICACAO.get(
            f, "esta informação não foi fornecida — preencha e rode de novo"
        )

    dado = contrato.gravar(
        "prometheus-criativos",
        conta=None,
        periodo=None,
        resumo={
            "produtos": len(itens),
            "com_titulo": sum(1 for i in itens if i["titulo"]),
            "com_objecoes": sum(1 for i in itens if i["objecoes"]),
        },
        itens=itens,
        faltando=faltando,
        lacunas=lacunas,
        avisos=avisos,
        fonte="local",
        pasta=BASE,
    )
    print("Gravado: prometheus-criativos.json (%d produto(s))" % len(itens))
    if avisos:
        print("Avisos: %s" % "; ".join(avisos))
    print("Veja no painel:  python3 painel.py")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_main())
    except (ValueError, contrato.ContratoInvalido) as e:
        sys.exit("PARADO: %s" % e)
