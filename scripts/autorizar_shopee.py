#!/usr/bin/env python3
"""Conecta a conta Shopee do vendedor, em dois passos.

    python3 autorizar_shopee.py
        -> grava ABRIR_SHOPEE.txt nesta pasta. A pessoa abre, copia o endereco,
           cola no navegador logado na conta de vendedor e autoriza.

    python3 autorizar_shopee.py --arquivo RETORNO_SHOPEE.txt
        -> troca o code pelo acesso e guarda em tokens-shopee.json.

O code vale 10 MINUTOS e uma vez so. Nao demore entre um passo e outro.
Nenhum valor secreto e impresso aqui.
"""
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

import meli  # noqa: E402
import seguro  # noqa: E402
import shopee  # noqa: E402

ABRIR = BASE / "ABRIR_SHOPEE.txt"
RETORNO = BASE / "RETORNO_SHOPEE.txt"
# A Shopee nao tem parametro `state`: o `redirect` vai dentro do endereco
# assinado com a partner_key, entao ninguem de fora monta um link que devolva
# para o endereco da pessoa. O que falta e o vinculo com ESTA tentativa — e
# isso e local: um pedido em andamento, de uso unico, com prazo. Sem ele, uma
# mesma URL de retorno serviria duas vezes, e o refresh da Shopee e de uso
# unico: a segunda troca derrubaria a conexao que acabou de funcionar.
PEDIDO = BASE / ".oauth_state_shopee"
VALIDADE_PEDIDO = 1800
CHAVES = ("SHOPEE_PARTNER_ID", "SHOPEE_PARTNER_KEY", "SHOPEE_REDIRECT_URI")


def _credenciais():
    cfg = meli._ler_arquivo_env()
    faltando = [k for k in CHAVES if not cfg.get(k)]
    if faltando:
        raise SystemExit(
            "PARADO: faltam valores em credenciais.txt: %s.\n"
            "Abra o arquivo, preencha depois do '=' e salve. Nunca cole no chat."
            % ", ".join(faltando))
    return int(cfg["SHOPEE_PARTNER_ID"]), cfg["SHOPEE_PARTNER_KEY"], cfg["SHOPEE_REDIRECT_URI"]


def passo1():
    pid, chave, redirect = _credenciais()
    seguro.gravar_protegido(
        PEDIDO, json.dumps({"em": int(time.time()), "redirect": redirect}))
    ABRIR.write_text(shopee.link_de_autorizacao(pid, chave, redirect) + "\n",
                     encoding="utf-8")
    RETORNO.write_text("", encoding="utf-8")
    print("Pronto. Agora, sem demora:")
    print("  1. Abra ABRIR_SHOPEE.txt e copie o endereco")
    print("  2. Cole no navegador LOGADO na sua conta de vendedor e autorize")
    print("  3. A pagina que abrir nao vai mostrar nada util — e esperado")
    print("  4. Copie a barra INTEIRA do navegador e cole em RETORNO_SHOPEE.txt")
    print("  5. Salve e rode:  python3 autorizar_shopee.py --arquivo RETORNO_SHOPEE.txt")
    print("\nO codigo vale 10 minutos e uma vez so.")
    return 0


def _pedido_em_andamento():
    """Diz se o passo 1 foi dado aqui e ainda vale."""
    try:
        d = json.loads(PEDIDO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if int(time.time()) - int(d.get("em", 0)) > VALIDADE_PEDIDO:
        return None
    return d


def passo2(caminho):
    pid, chave, redirect = _credenciais()
    pedido = _pedido_em_andamento()
    if not pedido:
        raise SystemExit(
            "PARADO: nao ha conexao em andamento (ou ela ficou velha demais).\n"
            "Comece pelo passo 1:  python3 autorizar_shopee.py")
    if pedido.get("redirect") and pedido["redirect"] != redirect:
        raise SystemExit(
            "PARADO: o endereco de retorno em credenciais.txt mudou depois do "
            "passo 1. Rode o passo 1 de novo:  python3 autorizar_shopee.py")
    endereco = Path(caminho).read_text(encoding="utf-8").strip()
    if not endereco:
        raise SystemExit("PARADO: %s esta vazio. Cole a barra do navegador e salve."
                         % caminho)
    try:
        code, loja = shopee.ler_retorno(endereco, redirect)
    except ValueError as e:
        raise SystemExit("PARADO: %s" % e)
    r = shopee.trocar_code_por_token(code, loja, pid, chave)
    Path(caminho).write_text("", encoding="utf-8")
    # Uso unico: gasto o pedido para a mesma URL nao ser trocada duas vezes.
    try:
        PEDIDO.unlink()
    except OSError:
        pass
    print("\nConectado. Acesso salvo em tokens-shopee.json (conteudo nao mostrado).")
    print("  loja   : %s" % r["shop_id"])
    print("  retorno: esvaziado")
    if not r.get("refresh_token"):
        print("  ATENCAO: nao veio refresh_token — a conexao vai cair em 4 horas.")
    else:
        print("  renovacao automatica: ligada (o refresh vence em 30 dias sem uso)")
    if r.get("protegido") is False:
        import pasta
        print("  ATENCAO: nao foi possivel confirmar a restricao de leitura do")
        print("           tokens-shopee.json — %s"
              % pasta.MOTIVOS_SEM_PROTECAO[r["motivo"]])
    return 0


def _main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args and args[0] == "--arquivo":
        if len(args) < 2:
            print("Uso: python3 autorizar_shopee.py --arquivo RETORNO_SHOPEE.txt")
            return 2
        return passo2(args[1])
    return passo1()


if __name__ == "__main__":
    raise SystemExit(_main())
