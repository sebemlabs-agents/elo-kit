#!/usr/bin/env python3
"""Contrato de dados do pacote Elo — versao 1.

Toda skill grava pelo mesmo envelope e o painel le so dali. A especificacao
completa esta em CONTRATO.md, na raiz do repositorio.

    from contrato import gravar, carregar
    gravar("elo-promocoes", conta, periodo, resumo, itens, faltando=[...], lacunas={...})

gravar() valida ANTES de escrever. Falhar na escrita e melhor que gravar um
arquivo que o painel desenharia errado.

Compatibilidade: Python 3.8+.
"""
import json
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONTRATO = "1"
# api  = leitura da conta real
# demo = dados de demonstracao preparados
# local = produzido aqui, sem ler conta nenhuma (ex.: conteudo de produto)
FONTES = ("api", "demo", "local", "export")

# Chaves cujo valor e dinheiro. Usadas para recusar valor monetario como texto
# (o classico "1.234,56" que quebra qualquer soma depois).
MARCAS_DE_DINHEIRO = (
    "valor", "preco", "custo", "imposto", "margem", "receita", "total",
    "taxa", "liquido", "bruto", "frete", "repasse", "desconto", "ticket",
)


class ContratoInvalido(ValueError):
    """O que a skill quis gravar nao respeita o contrato."""


def _parece_dinheiro(chave):
    k = str(chave).lower()
    return any(marca in k for marca in MARCAS_DE_DINHEIRO)


def _conferir_dinheiro(onde, obj):
    """Procura valor monetario gravado como texto, em qualquer profundidade."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if _parece_dinheiro(k) and isinstance(v, str):
                raise ContratoInvalido(
                    "%s: o campo '%s' e dinheiro e chegou como texto (%r). "
                    "Grave numero decimal com ponto, ex.: 149.90." % (onde, k, v)
                )
            _conferir_dinheiro(onde, v)
    elif isinstance(obj, list):
        for item in obj:
            _conferir_dinheiro(onde, item)


def validar(dado):
    """Levanta ContratoInvalido quando o envelope nao serve. Devolve o dado."""
    if dado.get("contrato") != CONTRATO:
        raise ContratoInvalido(
            "versao de contrato %r; este pacote grava e le a versao %r"
            % (dado.get("contrato"), CONTRATO)
        )

    if dado.get("fonte") not in FONTES:
        raise ContratoInvalido(
            "fonte %r invalida; use 'api' (conta real) ou 'demo' (dados de demonstracao)"
            % dado.get("fonte")
        )

    conta = dado.get("conta") or {}
    if dado["fonte"] == "api" and not conta.get("id"):
        # So exigimos a conta quando o dado veio dela. Skill que produz conteudo
        # local nao tem conta para nomear, e inventar uma seria mentira no painel.
        raise ContratoInvalido(
            "falta conta['id']. Pegue com meli.conta_conectada() para a pessoa poder "
            "confirmar que e a loja certa."
        )

    resumo = dado.get("resumo")
    if not isinstance(resumo, dict):
        raise ContratoInvalido("resumo precisa ser um objeto, mesmo vazio")
    for k, v in resumo.items():
        if isinstance(v, (dict, list)):
            raise ContratoInvalido(
                "resumo['%s'] e aninhado. O resumo tem de ser raso: o painel e o "
                "Claude leem dali em vez de somar linha por linha." % k
            )

    if not isinstance(dado.get("itens"), list):
        raise ContratoInvalido("itens precisa ser uma lista, mesmo vazia")

    faltando = dado.get("faltando")
    lacunas = dado.get("lacunas") or {}
    if not isinstance(faltando, list):
        raise ContratoInvalido("faltando precisa ser uma lista de strings, mesmo vazia")
    sem_explicacao = [f for f in faltando if not str(lacunas.get(f, "")).strip()]
    if sem_explicacao:
        raise ContratoInvalido(
            "estes campos estao em 'faltando' sem explicacao em 'lacunas': %s. "
            "Toda lacuna tem de ser dizivel ao vendedor, em portugues."
            % ", ".join(sem_explicacao)
        )

    if not isinstance(dado.get("avisos"), list):
        raise ContratoInvalido("avisos precisa ser uma lista, mesmo vazia")

    _conferir_dinheiro("resumo", resumo)
    _conferir_dinheiro("itens", dado["itens"])
    return dado


def montar(skill, conta, periodo, resumo, itens, faltando=None, lacunas=None,
           avisos=None, fonte="api", paginacao=None, moeda="BRL",
           capturado_em=None):
    """Monta o envelope e valida, sem tocar em disco.

    conta pode vir None quando fonte='local' — ver CONTRATO.md secao 2."""
    dado = {
        "contrato": CONTRATO,
        "skill": skill,
        "gerado_em": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "fonte": fonte,
        # Quando o dado veio de arquivo, ele tem DUAS idades: quando foi
        # processado (gerado_em) e quando foi capturado da origem. Confundir
        # as duas e mostrar dado de semana passada como se fosse de agora.
        "capturado_em": capturado_em,
        "conta": conta or {"id": None, "apelido": None, "site": None},
        "periodo": periodo if periodo else {"de": None, "ate": None},
        "moeda": moeda,
        "resumo": resumo or {},
        "itens": itens if itens is not None else [],
        "faltando": list(faltando or []),
        "lacunas": dict(lacunas or {}),
        "avisos": list(avisos or []),
    }
    if paginacao:
        dado["paginacao"] = paginacao
    return validar(dado)


def caminho(skill, pasta=None):
    return Path(pasta or BASE) / ("%s.json" % skill)


def gravar(skill, conta, periodo, resumo, itens, faltando=None, lacunas=None,
           avisos=None, fonte="api", paginacao=None, moeda="BRL", pasta=None,
           capturado_em=None):
    """Valida e grava <skill>.json na pasta. Devolve o que foi gravado."""
    dado = montar(skill, conta, periodo, resumo, itens, faltando=faltando,
                  lacunas=lacunas, avisos=avisos, fonte=fonte,
                  paginacao=paginacao, moeda=moeda, capturado_em=capturado_em)
    alvo = caminho(skill, pasta)
    alvo.write_text(
        json.dumps(dado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return dado


def carregar(skill, pasta=None):
    """Devolve o que a skill gravou, ou None quando ela ainda nao rodou."""
    alvo = caminho(skill, pasta)
    if not alvo.exists():
        return None
    return json.loads(alvo.read_text(encoding="utf-8"))


def carregar_todos(pasta=None):
    """Todos os arquivos de contrato presentes na pasta, em ordem de nome.

    Arquivo de versao desconhecida e ignorado com aviso em vez de derrubar o
    painel: quem instalou skill nova num pacote antigo nao fica sem painel."""
    pasta = Path(pasta or BASE)
    achados = []
    for arq in sorted(pasta.glob("elo-*.json")):
        try:
            dado = json.loads(arq.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if dado.get("contrato") != CONTRATO:
            continue
        achados.append(dado)
    return achados
