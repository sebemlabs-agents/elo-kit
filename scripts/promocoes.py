#!/usr/bin/env python3
"""Fila diaria de decisao sobre promocoes do Mercado Livre. SOMENTE LEITURA.

Le as campanhas da conta, separa as que terminam dentro da janela e diz, para
cada uma: quantos dias faltam, quantos anuncios estao dentro, o desconto minimo
exigido e se voce ja aderiu.

Nao adere a promocao, nao muda preco, nao altera anuncio. Toda chamada passa
pelo meli.request, que recusa qualquer metodo que nao seja GET antes de a
requisicao sair do computador.

Uso:
    python3 promocoes.py                 janela de 7 dias
    python3 promocoes.py --janela 14
    python3 promocoes.py --rapido        nao varre a lista de anuncios

O que ele NAO sabe, e diz na cara: se a promocao vai ser renovada, qual a sua
margem depois do desconto, e o desconto exigido anuncio a anuncio.

Compatibilidade: Python 3.8+.
"""
import datetime as dt
import sys

import contrato
import meli

JANELA_PADRAO = 7
MAX_PAGINAS = 20
POR_PAGINA = 100
FUSO = dt.timezone(dt.timedelta(hours=-3))

# Escopo amplo: valem para o catalogo elegivel, entao a lista muda sozinha.
AMPLO = ("DEAL", "MARKETPLACE_CAMPAIGN", "PRICE_MATCHING", "PRICE_MATCHING_MELI_ALL",
         "SMART", "PRE_NEGOTIATED")

ADERIDO = ("started", "active")


def quando(iso):
    """ISO do Mercado Livre -> datetime no fuso de Sao Paulo, ou None."""
    if not iso:
        return None
    texto = str(iso).strip().replace("Z", "+00:00")
    try:
        d = dt.datetime.fromisoformat(texto)
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(FUSO)


def _num(v):
    """Percentual pode vir como texto, None, ou numero. Nunca invente zero."""
    if v is None or v == "":
        return None
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def itens_da_promocao(pid, tipo, buscar=True):
    """Devolve (quantidade, aderidos, truncado). Sem varredura: (None, None, False)."""
    if not buscar:
        return None, None, False
    base = "/seller-promotions/promotions/%s/items" % pid
    params = {"app_version": "v2", "promotion_type": tipo, "limit": POR_PAGINA}
    total = 0
    aderidos = 0
    visto = None
    for _ in range(MAX_PAGINAS):
        p = dict(params)
        if visto:
            p["search_after"] = visto
        corpo = meli.request("GET", base, p)
        achados = corpo.get("results") or []
        if not achados:
            break
        for item in achados:
            total += 1
            if (item.get("status") or "").lower() in ADERIDO:
                aderidos += 1
        visto = (corpo.get("paging") or {}).get("searchAfter")
        if not visto or len(achados) < POR_PAGINA:
            return total, aderidos, False
    return total, aderidos, True


def coletar(janela=JANELA_PADRAO, rapido=False, hoje=None):
    """Monta o dado no formato do contrato. Nao grava — quem grava e o main."""
    conta = meli.conta_conectada()
    hoje = hoje or dt.datetime.now(FUSO).date()

    corpo = meli.request("GET", "/seller-promotions/users/%s" % conta["id"],
                         {"app_version": "v2"})
    todas = corpo.get("results") or []

    itens = []
    sem_data = 0
    truncou = False
    for p in todas:
        if (p.get("status") or "").lower() not in ("started", "pending"):
            continue
        fim = quando(p.get("finish_date"))
        if not fim:
            sem_data += 1
            continue
        dias = (fim.date() - hoje).days
        if dias < 0 or dias > janela:
            continue

        quantos, aderidos, cortou = itens_da_promocao(
            p.get("id"), p.get("type"), buscar=not rapido)
        truncou = truncou or cortou

        itens.append({
            "promocao": p.get("name") or p.get("type") or "sem nome",
            "tipo": p.get("type"),
            "termina": fim.date().isoformat(),
            "dias_restantes": dias,
            "anuncios_dentro": quantos,
            "anuncios_aderidos": aderidos,
            "desconto_minimo": _num(p.get("fixed_percentage")),
            "escopo_amplo": (p.get("type") or "") in AMPLO,
        })

    itens.sort(key=lambda i: (i["dias_restantes"], i["promocao"]))

    faltando, lacunas, avisos = [], {}, []

    if rapido or any(i["anuncios_dentro"] is None for i in itens):
        faltando.append("anuncios_dentro")
        lacunas["anuncios_dentro"] = (
            "não varremos a lista de anúncios nesta execução — rode sem --rapido "
            "para saber quantos estão dentro de cada promoção")
    if truncou:
        avisos.append(
            "alguma promoção passou do teto de %d páginas; a contagem de anúncios "
            "cobre só parte dela" % MAX_PAGINAS)
    if sem_data:
        avisos.append("%d promoção(ões) sem data de término foram ignoradas" % sem_data)
    if any(i["desconto_minimo"] is None for i in itens):
        faltando.append("desconto_minimo")
        lacunas["desconto_minimo"] = (
            "esta campanha não publica um percentual fixo; o desconto exigido "
            "aparece anúncio a anúncio, no painel do Mercado Livre")

    faltando.append("margem_apos_desconto")
    lacunas["margem_apos_desconto"] = (
        "a API do Mercado Livre não tem o seu custo por SKU, então ninguém aqui "
        "sabe se o desconto cabe na sua margem — essa conta é sua")
    faltando.append("vai_ser_renovada")
    lacunas["vai_ser_renovada"] = (
        "a API não diz se a campanha será renovada, estendida ou reaberta; "
        "só o seu gerente de conta confirma")

    if any(i["escopo_amplo"] for i in itens):
        avisos.append(
            "há campanha de escopo amplo: a lista de anúncios dentro muda sozinha "
            "conforme o Mercado Livre reavalia a elegibilidade")

    dentro = [i["anuncios_dentro"] for i in itens if i["anuncios_dentro"] is not None]
    ader = [i["anuncios_aderidos"] for i in itens if i["anuncios_aderidos"] is not None]
    resumo = {
        "promocoes_na_janela": len(itens),
        "termina_em_3_dias": sum(1 for i in itens if i["dias_restantes"] <= 3),
        "anuncios_afetados": sum(dentro) if dentro else None,
        "anuncios_ja_aderidos": sum(ader) if ader else None,
    }

    return {
        "conta": conta,
        "periodo": {"de": hoje.isoformat(),
                    "ate": (hoje + dt.timedelta(days=janela)).isoformat()},
        "resumo": resumo,
        "itens": itens,
        "faltando": faltando,
        "lacunas": lacunas,
        "avisos": avisos,
    }


def _main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    janela = JANELA_PADRAO
    if "--janela" in args:
        pos = args.index("--janela")
        if pos + 1 < len(args):
            try:
                janela = max(1, min(60, int(args[pos + 1])))
            except ValueError:
                print("--janela precisa de um numero de dias. Usando %d." % JANELA_PADRAO)

    d = coletar(janela=janela, rapido="--rapido" in args)
    contrato.gravar("elo-promocoes", conta=d["conta"], periodo=d["periodo"],
                    resumo=d["resumo"], itens=d["itens"], faltando=d["faltando"],
                    lacunas=d["lacunas"], avisos=d["avisos"])

    n = d["resumo"]["promocoes_na_janela"]
    if not n:
        print("Nenhuma promocao terminando nos proximos %d dias." % janela)
        print("Gravado assim mesmo: o painel mostra a janela vazia, que tambem e informacao.")
    else:
        print("%d promocao(oes) terminando em ate %d dias." % (n, janela))
        for i in d["itens"][:5]:
            dentro = i["anuncios_dentro"]
            print("  %-34s termina em %d dia(s)%s" % (
                i["promocao"][:34], i["dias_restantes"],
                "" if dentro is None else " · %d anuncio(s)" % dentro))
    print("\nVeja no painel:  python3 painel.py")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_main())
    except (meli.SemAutorizacao, meli.CredenciaisIncompletas) as e:
        sys.exit("PARADO: %s" % e)
    except meli.ErroDaAPI as e:
        sys.exit("PARADO: %s" % e)
