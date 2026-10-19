#!/usr/bin/env python3
"""Transforma o painel local num plano para subir para Supabase e Vercel.

Le os arquivos que as skills gravaram nesta pasta e escreve spec-nuvem.md:
o esquema de tabelas tirado dos SEUS dados reais, a fronteira do que sobe e do
que fica, e os passos na ordem.

Nao sobe nada. Nao cria conta. Nao toca em credencial. So escreve um documento
para voce (ou o Claude, com voce junto) executar depois.

Uso:
    python3 spec.py
    python3 spec.py --projeto painel-da-minha-loja

Compatibilidade: Python 3.8+.
"""
import datetime as dt
import re
import sys
from pathlib import Path

import contrato

BASE = Path(__file__).resolve().parent
SAIDA = "spec-nuvem.md"

# Nunca sobem. Nem numa tabela, nem numa variavel de ambiente do painel.
NUNCA_SOBEM = ("credenciais.txt", "tokens.json", ".env", "RETORNO.txt",
               ".oauth_state", "ABRIR_NO_NAVEGADOR.txt")


def nome_de_tabela(skill):
    limpo = re.sub(r"[^a-z0-9]+", "_", str(skill).lower()).strip("_")
    return limpo or "dados"


def tipo_sql(valores):
    """Infere o tipo pelo dado real, nao por suposicao."""
    reais = [v for v in valores if v is not None]
    if not reais:
        return "text", True
    if all(isinstance(v, bool) for v in reais):
        return "boolean", False
    if all(isinstance(v, int) and not isinstance(v, bool) for v in reais):
        return "integer", False
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in reais):
        return "numeric(14,2)", False
    if all(isinstance(v, (list, dict)) for v in reais):
        return "jsonb", False
    if all(isinstance(v, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", v) for v in reais):
        return "date", False
    return "text", False


def colunas_de(itens):
    """Uniao das chaves, na ordem em que aparecem, com o tipo de cada uma."""
    ordem = []
    valores = {}
    for item in itens:
        if not isinstance(item, dict):
            continue
        for k, v in item.items():
            if k not in valores:
                ordem.append(k)
                valores[k] = []
            valores[k].append(v)
    saida = []
    for k in ordem:
        tipo, so_nulo = tipo_sql(valores[k])
        saida.append({"nome": nome_de_tabela(k), "origem": k, "tipo": tipo,
                      "sempre_vazia": so_nulo})
    return saida


def tabela_sql(tabela, colunas):
    linhas = ["  id bigserial primary key",
              "  conta_id bigint not null",
              "  gerado_em timestamptz not null"]
    for c in colunas:
        linhas.append("  %s %s" % (c["nome"], c["tipo"]))
    corpo = ",\n".join(linhas)
    return (
        "create table if not exists %s (\n%s\n);\n\n"
        "alter table %s enable row level security;" % (tabela, corpo, tabela))


def montar(pasta=None, projeto=None):
    pasta = Path(pasta or BASE)
    dados = contrato.carregar_todos(pasta)
    if not dados:
        raise FileNotFoundError(
            "Nenhum arquivo de skill nesta pasta. Rode uma skill do pacote antes: "
            "sem dado real não dá para montar o esquema — e esquema chutado é "
            "o que faz a migração falhar depois.")

    projeto = projeto or "painel-da-minha-loja"
    agora = dt.datetime.now().astimezone()
    blocos = []
    for d in sorted(dados, key=lambda x: x.get("skill", "")):
        skill = d.get("skill", "?")
        itens = d.get("itens") or []
        blocos.append({
            "skill": skill,
            "tabela": nome_de_tabela(skill),
            "linhas": len(itens),
            "colunas": colunas_de(itens),
            "fonte": d.get("fonte"),
            "resumo": list((d.get("resumo") or {}).keys()),
        })

    return {"projeto": projeto, "gerado_em": agora.isoformat(timespec="seconds"),
            "blocos": blocos}


def escrever(plano, pasta=None):
    pasta = Path(pasta or BASE)
    p = []
    a = p.append

    a("# Levar o painel para a nuvem — %s\n" % plano["projeto"])
    a("> Gerado em %s a partir dos dados que **já existem** nesta pasta.\n"
      "> O esquema abaixo não é modelo de exemplo: saiu dos seus próprios arquivos.\n"
      % plano["gerado_em"])

    a("\n## A fronteira, antes de qualquer passo\n")
    a("**Os dados sobem. A credencial não.**\n")
    a("O acesso ao Mercado Livre continua só nesta máquina. O que vai para a nuvem é o\n"
      "resultado já calculado — promoções, valores, datas. Quem subir `tokens.json` ou\n"
      "`credenciais.txt` entrega a própria conta de venda a qualquer pessoa que leia o banco.\n")
    a("\nEstes arquivos **nunca** entram em repositório, variável de ambiente ou tabela:\n")
    for f in NUNCA_SOBEM:
        a("- `%s`" % f)
    a("\nQuem continua chamando a API é a sua máquina. A nuvem só guarda e mostra.\n")

    a("\n## O que existe hoje\n")
    a("| Skill | Tabela | Linhas | Colunas |")
    a("|---|---|---|---|")
    for b in plano["blocos"]:
        marca = " ⚠️ demonstração" if b["fonte"] == "demo" else ""
        a("| `%s`%s | `%s` | %d | %d |"
          % (b["skill"], marca, b["tabela"], b["linhas"], len(b["colunas"])))

    demo = [b for b in plano["blocos"] if b["fonte"] == "demo"]
    if demo:
        a("\n**Atenção:** %s está com dados de demonstração. Suba só depois de rodar com a\n"
          "conta real, senão o painel na nuvem nasce mentindo.\n"
          % ", ".join("`%s`" % b["skill"] for b in demo))

    a("\n## Passo 1 — as tabelas\n")
    a("Uma tabela por skill. `conta_id` e `gerado_em` entram em todas: é o que permite ter\n"
      "mais de uma loja e saber de quando é cada número.\n")
    for b in plano["blocos"]:
        a("\n### `%s`\n" % b["tabela"])
        a("```sql")
        a(tabela_sql(b["tabela"], b["colunas"]))
        a("```")
        vazias = [c["origem"] for c in b["colunas"] if c["sempre_vazia"]]
        if vazias:
            a("\n> Vieram sempre vazias nesta leitura: %s. Ficaram como `text` por falta de\n"
              "> exemplo — confira o tipo quando tiver dado real."
              % ", ".join("`%s`" % v for v in vazias))

    a("\n## Passo 2 — a segurança, antes de existir dado\n")
    a("Todas as tabelas nascem com **row level security ligada e nenhuma política**. Isso\n"
      "significa que, por padrão, **ninguém lê nada** — nem você.\n")
    a("\nIsso é de propósito. O erro mais comum em painel feito com IA é subir a tabela\n"
      "aberta e descobrir depois: enquanto não existe política, não existe vazamento.\n")
    a("\nEscrever a política é uma decisão, não um detalhe: **quem pode ler quais linhas?**\n"
      "Na maioria dos casos é \"cada pessoa lê as linhas da conta dela\", e a política\n"
      "compara o usuário autenticado com `conta_id`. Escreva essa regra com alguém que\n"
      "entenda o seu caso — é exatamente o assunto do bloco de segurança.\n")

    a("\n## Passo 3 — mandar os dados para cima\n")
    a("O que sobe é o conteúdo dos arquivos `elo-*.json` desta pasta: para cada skill, as\n"
      "linhas de `itens`, carimbadas com `conta_id` e `gerado_em`.\n")
    a("\nA rotina que já roda na sua máquina passa a fazer duas coisas em vez de uma: grava o\n"
      "arquivo local **e** envia para a tabela. O painel local continua funcionando; a nuvem\n"
      "vira a cópia que a equipe abre.\n")

    a("\n## Passo 4 — a tela\n")
    a("O `painel.html` desta pasta já é a tela. Na nuvem ele deixa de ler arquivo e passa a\n"
      "ler as tabelas — mesmos blocos, mesma leitura.\n")
    a("\nDuas regras que não mudam ao sair daqui: **dado ausente continua dizendo que não\n"
      "veio** em vez de virar zero, e **dado de demonstração continua marcado**. Se o painel\n"
      "na nuvem perder isso, ele ficou mais bonito e menos confiável.\n")

    a("\n## O que este documento não decide por você\n")
    a("- **Quem pode ver.** A política de leitura depende de como as pessoas entram.\n")
    a("- **Quanto tempo guardar.** Histórico cresce; decida a janela antes de encher.\n")
    a("- **Quem paga.** Conta de nuvem tem dono e tem custo quando o uso cresce.\n")

    a("\n---\n")
    a("Para ir além disto — testes, revisão automática, planos por etapa — existe o pacote\n"
      "`superpowers`, que é feito para quem escreve software. Não é necessário para subir\n"
      "este painel: é o próximo degrau, para quem quiser.\n")

    alvo = pasta / SAIDA
    alvo.write_text("\n".join(p) + "\n", encoding="utf-8")
    return alvo


def _main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    projeto = None
    if "--projeto" in args:
        pos = args.index("--projeto")
        if pos + 1 < len(args):
            projeto = args[pos + 1]

    plano = montar(projeto=projeto)
    alvo = escrever(plano)
    print("Plano escrito: %s" % alvo.name)
    print("Abrir: %s" % alvo.resolve().as_uri())
    for b in plano["blocos"]:
        print("  %-18s -> tabela %-18s %d linha(s), %d coluna(s)"
              % (b["skill"], b["tabela"], b["linhas"], len(b["colunas"])))
    print("\nNada foi enviado. O documento e um plano para voce executar com alguem junto.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_main())
    except FileNotFoundError as e:
        sys.exit("PARADO: %s" % e)
