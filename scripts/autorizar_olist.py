#!/usr/bin/env python3
"""Conecta a Olist (Tiny) em dois passos e importa o custo dos produtos.

    python3 autorizar_olist.py
        -> grava ABRIR_OLIST.txt. A pessoa abre, copia, cola no navegador
           logado no ERP e autoriza.

    python3 autorizar_olist.py --arquivo RETORNO_OLIST.txt
        -> troca o code pelo acesso e guarda em tokens-olist.json.

Na Olist o acesso vale 4 horas e a renovacao vale 1 DIA. Por isso o custo e
importado para a pasta: o painel usa o arquivo e continua funcionando depois
que a conexao vence.
"""
import json
import secrets
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

import meli  # noqa: E402
import seguro  # noqa: E402
import olist  # noqa: E402

ABRIR = BASE / "ABRIR_OLIST.txt"
RETORNO = BASE / "RETORNO_OLIST.txt"
# Vincula o retorno a esta tentativa. Vale 1 hora: o code da Olist expira em
# muito menos que isso, entao o prazo daqui nunca e o que trava a pessoa.
ESTADO = BASE / ".oauth_state_olist"
VALIDADE_ESTADO = 3600
CHAVES = ("OLIST_CLIENT_ID", "OLIST_CLIENT_SECRET", "OLIST_REDIRECT_URI")


def _credenciais():
    cfg = meli._ler_arquivo_env()
    faltando = [k for k in CHAVES if not cfg.get(k)]
    if faltando:
        raise SystemExit(
            "PARADO: faltam valores em credenciais.txt: %s.\n"
            "No ERP: menu > configuracoes > aba geral > Aplicativos > + novo aplicativo.\n"
            "Salve, ENTRE DE NOVO no aplicativo e edite para ver as chaves.\n"
            "Nunca cole esses valores no chat." % ", ".join(faltando))
    return cfg["OLIST_CLIENT_ID"], cfg["OLIST_CLIENT_SECRET"], cfg["OLIST_REDIRECT_URI"]


def passo1():
    cid, _, redirect = _credenciais()
    state = secrets.token_urlsafe(16)
    seguro.gravar_protegido(
        ESTADO, json.dumps({"state": state, "em": int(time.time())}))
    ABRIR.write_text(olist.link_de_autorizacao(cid, redirect, state) + "\n",
                     encoding="utf-8")
    RETORNO.write_text("", encoding="utf-8")
    print("Pronto. Agora:")
    print("  1. Abra ABRIR_OLIST.txt e copie o endereco")
    print("  2. Cole no navegador LOGADO no seu ERP e autorize")
    print("  3. Copie a barra INTEIRA do navegador e cole em RETORNO_OLIST.txt")
    print("  4. Salve e rode:  python3 autorizar_olist.py --arquivo RETORNO_OLIST.txt")
    return 0


def _estado_pendente():
    """Devolve o state da tentativa em andamento, ou None se nao houver."""
    try:
        d = json.loads(ESTADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if int(time.time()) - int(d.get("em", 0)) > VALIDADE_ESTADO:
        return None
    return d.get("state")


def passo2(caminho):
    cid, segredo, redirect = _credenciais()
    endereco = Path(caminho).read_text(encoding="utf-8").strip()
    if not endereco:
        raise SystemExit("PARADO: %s esta vazio. Cole a barra do navegador e salve."
                         % caminho)
    esperado = _estado_pendente()
    if not esperado:
        raise SystemExit(
            "PARADO: nao ha conexao em andamento (ou ela ficou velha demais).\n"
            "Comece pelo passo 1:  python3 autorizar_olist.py")
    try:
        code = olist.ler_retorno(endereco, redirect, esperado)
    except (ValueError, seguro.RetornoDeOutroEndereco) as e:
        raise SystemExit("PARADO: %s" % e)
    r = olist.trocar_code_por_token(code, cid, segredo, redirect)
    Path(caminho).write_text("", encoding="utf-8")
    # Uso unico: gasto o state para a mesma URL nao servir duas vezes.
    try:
        ESTADO.unlink()
    except OSError:
        pass
    print("\nConectado. Acesso salvo em tokens-olist.json (conteudo nao mostrado).")
    print("  retorno: esvaziado")
    print("\nA renovacao da Olist vence em 1 DIA — e normal, e nao e erro seu.")
    print("Por isso o custo e importado para a pasta: o painel segue funcionando")
    print("depois que a conexao vence. Para trazer custo novo, reconecte.")
    if r.get("protegido") is False:
        import pasta
        print("\n  ATENCAO: nao foi possivel confirmar a restricao de leitura do")
        print("           tokens-olist.json — %s" % pasta.MOTIVOS_SEM_PROTECAO[r["motivo"]])
    return 0


def _main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args and args[0] == "--arquivo":
        if len(args) < 2:
            print("Uso: python3 autorizar_olist.py --arquivo RETORNO_OLIST.txt")
            return 2
        return passo2(args[1])
    return passo1()


if __name__ == "__main__":
    raise SystemExit(_main())
