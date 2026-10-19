#!/usr/bin/env python3
"""Quanto as suas vendas vao liberar, e quando. SOMENTE LEITURA.

Le os pedidos pagos da conta e monta o calendario de liberacao: o que ja
liberou, o que cai nos proximos dias, e o que ainda nao tem data.

NAO e o saldo da sua carteira. O saldo e o saque vivem noutra linha do tempo e
noutro endpoint, que a conta de vendedor nao alcanca. Esta skill responde uma
pergunta mais util no dia a dia: do que eu ja vendi, quanto ainda vai cair.

Uso:
    python3 caixa.py                 ultimos 60 dias de pedidos
    python3 caixa.py --dias 90
    python3 caixa.py --paginas 10    teto de paginas (cada uma = 50 pedidos)

Armadilhas que este script ja evita, todas medidas em operacao real:
  - id de pagamento alfanumerico NAO e venda (e fatura do Meli). Fica de fora.
  - saque nao tem data de liberacao e nao entra no calendario.
  - linha negativa nao vira perda somada: o que vale e o liquido do pagamento.
  - tipo que ele nao sabe classificar e CONTADO e RELATADO, nunca somem calado.

Compatibilidade: Python 3.8+.
"""
import datetime as dt
import sys

import contrato
import meli

DIAS_PADRAO = 60
POR_PAGINA = 50
MAX_PAGINAS = 20
FUSO = dt.timezone(dt.timedelta(hours=-3))

# A data de liberacao ja apareceu com mais de um nome. Procuramos nesta ordem
# e, se nenhum vier, declaramos a lacuna — nunca chutamos a data.
CAMPOS_LIBERACAO = ("money_release_date", "date_released", "release_date",
                    "money_release_status_date")
CAMPOS_VALOR = ("transaction_amount", "total_paid_amount", "amount")

PAGO = ("approved", "accredited", "paid")
FORA_DO_CALENDARIO = ("payout", "withdrawal", "transfer")


def quando(iso):
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


def _primeiro(dic, campos):
    for c in campos:
        v = dic.get(c)
        if v not in (None, ""):
            return v
    return None


def e_venda(pagamento):
    """Id alfanumerico nao e venda — e fatura do Meli, e nao entra no caixa."""
    pid = pagamento.get("id")
    if pid is None:
        return False
    texto = str(pid)
    return texto.isdigit() and len(texto) >= 6


def _valor(pagamento):
    v = _primeiro(pagamento, CAMPOS_VALOR)
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def coletar(dias=DIAS_PADRAO, paginas=MAX_PAGINAS, hoje=None):
    """Monta o dado no formato do contrato. Nao grava."""
    conta = meli.conta_conectada()
    hoje = hoje or dt.datetime.now(FUSO).date()
    desde = hoje - dt.timedelta(days=dias)

    pedidos = []
    truncou = False
    for pagina in range(paginas):
        corpo = meli.request("GET", "/orders/search", {
            "seller": conta["id"],
            "order.status": "paid",
            "sort": "date_desc",
            "offset": pagina * POR_PAGINA,
            "limit": POR_PAGINA,
        })
        achados = corpo.get("results") or []
        if not achados:
            break
        pedidos.extend(achados)
        if len(achados) < POR_PAGINA:
            break
    else:
        truncou = True

    por_data = {}
    sem_data = []
    ja_liberou = 0.0
    descartados = {"nao_e_venda": 0, "fora_do_calendario": 0, "sem_valor": 0}
    antes_da_janela = 0

    for pedido in pedidos:
        for pagamento in (pedido.get("payments") or []):
            situacao = (pagamento.get("status") or "").lower()
            if situacao and situacao not in PAGO:
                continue
            tipo = (pagamento.get("payment_type") or
                    pagamento.get("operation_type") or "").lower()
            if any(t in tipo for t in FORA_DO_CALENDARIO):
                descartados["fora_do_calendario"] += 1
                continue
            if not e_venda(pagamento):
                descartados["nao_e_venda"] += 1
                continue
            valor = _valor(pagamento)
            if valor is None:
                descartados["sem_valor"] += 1
                continue

            liberacao = quando(_primeiro(pagamento, CAMPOS_LIBERACAO))
            if liberacao is None:
                sem_data.append(valor)
                continue
            data = liberacao.date()
            if data < desde:
                antes_da_janela += 1
                continue
            if data <= hoje:
                ja_liberou += valor
            else:
                por_data[data] = round(por_data.get(data, 0.0) + valor, 2)

    itens = [{"data": d.isoformat(),
              "dias_ate_liberar": (d - hoje).days,
              "valor": por_data[d]}
             for d in sorted(por_data)]

    a_receber = round(sum(i["valor"] for i in itens), 2)
    proximos7 = round(sum(i["valor"] for i in itens if i["dias_ate_liberar"] <= 7), 2)

    faltando, lacunas, avisos = [], {}, []

    if sem_data:
        faltando.append("data_de_liberacao")
        lacunas["data_de_liberacao"] = (
            "%d pagamento(s), somando R$ %.2f, vieram sem data de liberação — "
            "não dá para dizer quando caem, e por isso ficaram fora do total"
            % (len(sem_data), sum(sem_data)))
    faltando.append("saldo_da_carteira")
    lacunas["saldo_da_carteira"] = (
        "isto não é o saldo do Mercado Pago: saque, estorno e taxa fora de pedido "
        "vivem noutra linha do tempo, num relatório que leva minutos para gerar")
    faltando.append("o_que_vazou")
    lacunas["o_que_vazou"] = (
        "disputa, chargeback e reembolso não aparecem aqui — é leitura pesada, "
        "feita fora do calendário de liberação")

    for chave, rotulo in (("nao_e_venda", "não eram venda (fatura do Meli)"),
                          ("fora_do_calendario", "eram saque ou transferência"),
                          ("sem_valor", "vieram sem valor")):
        if descartados[chave]:
            avisos.append("%d pagamento(s) %s e ficaram de fora" % (descartados[chave], rotulo))
    if antes_da_janela:
        avisos.append("%d pagamento(s) liberaram antes da janela de %d dias"
                      % (antes_da_janela, dias))
    if truncou:
        avisos.append("a leitura parou no teto de %d páginas; há pedidos mais antigos "
                      "não considerados" % paginas)

    resumo = {
        "a_receber": a_receber,
        "libera_em_7_dias": proximos7,
        "ja_liberado_na_janela": round(ja_liberou, 2),
        "datas_com_liberacao": len(itens),
        "pedidos_lidos": len(pedidos),
    }

    return {
        "conta": conta,
        "periodo": {"de": desde.isoformat(), "ate": hoje.isoformat()},
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

    def opcao(nome, padrao, teto):
        if nome in args:
            pos = args.index(nome)
            if pos + 1 < len(args):
                try:
                    return max(1, min(teto, int(args[pos + 1])))
                except ValueError:
                    print("%s precisa de um numero. Usando %d." % (nome, padrao))
        return padrao

    d = coletar(dias=opcao("--dias", DIAS_PADRAO, 180),
                paginas=opcao("--paginas", MAX_PAGINAS, 60))
    contrato.gravar("elo-caixa", conta=d["conta"], periodo=d["periodo"],
                    resumo=d["resumo"], itens=d["itens"], faltando=d["faltando"],
                    lacunas=d["lacunas"], avisos=d["avisos"])

    r = d["resumo"]
    print("A receber: R$ %.2f  ·  nos proximos 7 dias: R$ %.2f"
          % (r["a_receber"], r["libera_em_7_dias"]))
    for i in d["itens"][:5]:
        print("  %s  em %2d dia(s)  R$ %.2f" % (i["data"], i["dias_ate_liberar"], i["valor"]))
    for a in d["avisos"]:
        print("  aviso: %s" % a)
    print("\nVeja no painel:  python3 painel.py")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_main())
    except (meli.SemAutorizacao, meli.CredenciaisIncompletas, meli.ErroDaAPI) as e:
        sys.exit("PARADO: %s" % e)
