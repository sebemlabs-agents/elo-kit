#!/usr/bin/env python3
"""Monta painel.html a partir dos arquivos de contrato presentes na pasta.

A skill coleta e grava; o painel le e formata. Este arquivo nunca chama a API.

Regras que o painel precisa cumprir (ver CONTRATO.md):
  - skill ausente nao e erro: o bloco simplesmente nao aparece;
  - fonte 'demo' aparece de forma visivel e permanente, nao em rodape;
  - toda lacuna e impressa com a explicacao em portugues;
  - a idade do dado aparece, porque dado de ontem lido como de hoje e decisao errada.

CLI:
    python3 painel.py            # le elo-*.json da pasta e grava painel.html

Compatibilidade: Python 3.8+.
"""
import html
import sys
import time
from pathlib import Path

import contrato

BASE = Path(__file__).resolve().parent

TITULOS = {
    "elo-promocoes": "Promoções terminando",
    "elo-caixa": "Dinheiro a receber",
    "elo-criativos": "Conteúdo de produto",
    "elo-devolucoes": "Devoluções",
    "elo-margem": "Margem por anúncio",
    "elo-concorrencia": "Concorrência",
    "elo-estoque": "Estoque e compras",
}


def _e(txt):
    return html.escape(str(txt), quote=True)


def idade(gerado_em):
    """Texto curto com a idade do dado. Nunca esconde dado velho."""
    try:
        marca = time.strptime(gerado_em[:19], "%Y-%m-%dT%H:%M:%S")
    except (ValueError, TypeError):
        return "data de geração desconhecida"
    segundos = time.time() - time.mktime(marca)
    if segundos < 0:
        return "agora"
    minutos = int(segundos // 60)
    if minutos < 2:
        return "agora"
    if minutos < 60:
        return "há %d min" % minutos
    horas = int(minutos // 60)
    if horas < 24:
        return "há %d h" % horas
    return "há %d dia(s)" % int(horas // 24)


def _valor(v):
    if v is None:
        return '<span class="vazio">não veio</span>'
    if isinstance(v, bool):
        return "sim" if v else "não"
    if isinstance(v, float):
        return _e(("%.2f" % v).replace(".", ","))
    if isinstance(v, (list, tuple)):
        return _e(", ".join(str(x) for x in v))
    if isinstance(v, dict):
        return _e("; ".join("%s: %s" % (k, x) for k, x in v.items()))
    return _e(v)


def bloco_resumo(resumo):
    if not resumo:
        return ""
    celulas = "".join(
        '<div class="kpi"><span class="rotulo">%s</span><strong>%s</strong></div>'
        % (_e(str(k).replace("_", " ")), _valor(v))
        for k, v in resumo.items()
    )
    return '<div class="kpis">%s</div>' % celulas


def bloco_itens(itens):
    if not itens:
        return '<p class="nada">Nada nesta janela.</p>'
    colunas = []
    for item in itens:
        if isinstance(item, dict):
            for k in item:
                if k not in colunas:
                    colunas.append(k)
    if not colunas:
        return "<ul>%s</ul>" % "".join("<li>%s</li>" % _valor(i) for i in itens)
    cabecalho = "".join("<th>%s</th>" % _e(c.replace("_", " ")) for c in colunas)
    linhas = []
    for item in itens:
        celulas = "".join("<td>%s</td>" % _valor(item.get(c)) for c in colunas)
        linhas.append("<tr>%s</tr>" % celulas)
    return ('<div class="tabela"><table><thead><tr>%s</tr></thead><tbody>%s</tbody>'
            "</table></div>" % (cabecalho, "".join(linhas)))


def bloco_lacunas(dado):
    faltando = dado.get("faltando") or []
    if not faltando:
        return ""
    lacunas = dado.get("lacunas") or {}
    linhas = "".join(
        "<li><b>%s</b> não veio da API: %s</li>"
        % (_e(str(f).replace("_", " ")), _e(lacunas.get(f, "")))
        for f in faltando
    )
    return '<div class="lacunas"><p>O que falta neste bloco</p><ul>%s</ul></div>' % linhas


def bloco_avisos(dado):
    avisos = dado.get("avisos") or []
    if not avisos:
        return ""
    return '<div class="avisos">%s</div>' % "".join(
        "<span>%s</span>" % _e(a) for a in avisos
    )


def bloco_skill(dado):
    skill = dado.get("skill", "?")
    titulo = TITULOS.get(skill, skill)
    demo = dado.get("fonte") == "demo"
    periodo = dado.get("periodo") or {}
    recorte = ""
    if periodo.get("de") and periodo.get("ate"):
        recorte = " · %s a %s" % (_e(periodo["de"]), _e(periodo["ate"]))
    selo = '<span class="demo">dados de demonstração</span>' if demo else ""
    return """
<section class="bloco%s">
  <header>
    <h2>%s %s</h2>
    <p class="meta">%s%s · atualizado %s</p>
  </header>
  %s
  %s
  %s
  %s
</section>""" % (
        " em-demo" if demo else "",
        _e(titulo),
        selo,
        _e(skill),
        recorte,
        _e(idade(dado.get("gerado_em"))),
        bloco_resumo(dado.get("resumo")),
        bloco_lacunas(dado),
        bloco_itens(dado.get("itens")),
        bloco_avisos(dado),
    )


ESTILO = """
:root{--papel:#f4f6f5;--carta:#fff;--tinta:#131a18;--tinta2:#4b5853;--linha:#d6dcd8;
--aco:#1f5f73;--ambar:#a8640c;--ambar-fundo:#f9ecd6;--vazio:#8d9793}
*{box-sizing:border-box}
body{margin:0;background:var(--papel);color:var(--tinta);
font:16px/1.5 -apple-system,"Segoe UI",system-ui,sans-serif}
.pagina{max-width:1000px;margin:0 auto;padding:28px 18px 64px}
h1{font-size:1.6rem;margin:0}
.cabeca{border-bottom:1px solid var(--linha);padding-bottom:16px;margin-bottom:8px}
.cabeca p{margin:6px 0 0;color:var(--tinta2);font-size:.92rem}
.so-leitura{display:inline-block;margin-top:10px;padding:4px 9px;border-radius:4px;
background:#dceaef;color:#15485a;font-size:.78rem}
.bloco{background:var(--carta);border:1px solid var(--linha);border-radius:8px;
padding:18px 20px;margin-top:18px}
.bloco.em-demo{border-color:var(--ambar);background:var(--ambar-fundo)}
.bloco h2{font-size:1.12rem;margin:0}
.demo{font-size:.72rem;background:var(--ambar);color:#fff;padding:2px 8px;
border-radius:999px;vertical-align:middle;margin-left:6px}
.meta{margin:3px 0 0;color:var(--tinta2);font-size:.82rem}
.kpis{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}
.kpi{background:var(--papel);border:1px solid var(--linha);border-radius:6px;
padding:9px 13px;min-width:120px}
.bloco.em-demo .kpi{background:#fff}
.kpi .rotulo{display:block;font-size:.74rem;color:var(--tinta2)}
.kpi strong{font-size:1.2rem;font-variant-numeric:tabular-nums}
.lacunas{border-left:3px solid var(--ambar);background:var(--papel);
padding:10px 14px;margin:12px 0;border-radius:0 5px 5px 0}
.bloco.em-demo .lacunas{background:#fff}
.lacunas p{margin:0 0 4px;font-size:.8rem;text-transform:uppercase;
letter-spacing:.05em;color:var(--ambar)}
.lacunas ul{margin:0;padding-left:1.1em;font-size:.9rem;color:var(--tinta2)}
.tabela{overflow-x:auto;border:1px solid var(--linha);border-radius:6px;margin-top:12px}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th,td{text-align:left;padding:9px 12px;border-top:1px solid var(--linha);
vertical-align:top}
thead th{border-top:0;background:var(--papel);font-size:.74rem;text-transform:uppercase;
letter-spacing:.05em;color:var(--tinta2)}
.vazio{color:var(--vazio);font-style:italic}
.nada{color:var(--tinta2);font-size:.9rem;margin:12px 0 0}
.avisos{margin-top:12px;display:flex;flex-wrap:wrap;gap:6px}
.avisos span{font-size:.78rem;background:var(--papel);border:1px solid var(--linha);
border-radius:999px;padding:3px 9px;color:var(--tinta2)}
.bloco.em-demo .avisos span{background:#fff}
.vazio-geral{background:var(--carta);border:1px dashed var(--linha);border-radius:8px;
padding:28px 22px;margin-top:18px;color:var(--tinta2)}
footer{margin-top:28px;padding-top:14px;border-top:1px solid var(--linha);
color:var(--vazio);font-size:.8rem}
@media print{body{background:#fff}.bloco{break-inside:avoid}}
"""


def render(dados):
    """HTML do painel a partir de uma lista de arquivos de contrato."""
    conta = {}
    for d in dados:
        if d.get("conta", {}).get("id"):
            conta = d["conta"]
            break

    if dados:
        corpo = "".join(bloco_skill(d) for d in dados)
    else:
        corpo = (
            '<div class="vazio-geral"><b>Nenhuma skill rodou ainda.</b>'
            "<p>Depois de conectar a conta, rode uma das skills do pacote. "
            "Cada uma grava um arquivo nesta pasta e aparece aqui como um bloco.</p></div>"
        )

    titulo = "Painel Elo"
    quem = ""
    if conta:
        quem = "%s · conta %s" % (
            _e(conta.get("apelido") or "sem apelido"),
            _e(conta.get("id")),
        )

    return """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title><style>%s</style></head>
<body><div class="pagina">
<div class="cabeca">
  <h1>%s</h1>
  <p>%s</p>
  <span class="so-leitura">somente leitura · nada é alterado na sua conta</span>
</div>
%s
<footer>Gerado por painel.py a partir dos arquivos desta pasta. Para atualizar,
rode a skill de novo e depois <code>python3 painel.py</code>.</footer>
</div></body></html>
""" % (_e(titulo), ESTILO, _e(titulo), quem, corpo)


def _main():
    pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE
    dados = contrato.carregar_todos(pasta)
    alvo = pasta / "painel.html"
    alvo.write_text(render(dados), encoding="utf-8")
    if not dados:
        print("Nenhum arquivo de skill encontrado em %s." % pasta)
        print("Painel criado vazio em %s — rode uma skill e gere de novo." % alvo.name)
        print("Abrir: %s" % alvo.resolve().as_uri())
        return 0
    nomes = ", ".join(d.get("skill", "?") for d in dados)
    print("Painel gerado: %s" % alvo)
    print("Abrir: %s" % alvo.resolve().as_uri())
    print("Blocos: %s" % nomes)
    demo = [d.get("skill") for d in dados if d.get("fonte") == "demo"]
    if demo:
        print("Atencao: em dados de demonstracao: %s" % ", ".join(demo))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
