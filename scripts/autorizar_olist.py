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


def _consumir(arquivo, comando):
    """Gasta a tentativa ANTES da troca, nao depois.

    O unlink e atomico: se a pessoa rodar duas vezes ao mesmo tempo, quem
    apagar primeiro leva, e a outra execucao nao acha tentativa nenhuma.
    Consumir depois da troca deixava as duas passarem — e o refresh destes
    canais e de uso unico, entao a segunda troca derrubaria a conexao que
    acabou de funcionar.

    Falha ao apagar NAO e ignorada: sem conseguir gastar a tentativa, nao da
    para garantir uso unico, e o certo e parar."""
    try:
        arquivo.unlink()
    except FileNotFoundError:
        raise SystemExit(
            "PARADO: esta conexao ja foi concluida (ou outra execucao a levou).\n"
            "Se precisar conectar de novo, comece pelo passo 1:  %s" % comando)
    except OSError:
        raise SystemExit(
            "PARADO: nao consegui encerrar a tentativa em andamento, e sem isso "
            "nao da para garantir que ela seja usada uma unica vez.\n"
            "Apague este arquivo e comece pelo passo 1:\n  %s\n  %s"
            % (arquivo, comando))


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
    # Conferir o endereco ANTES de gastar a tentativa: colar errado e o erro
    # mais comum, e nao custa refazer o passo 1 por causa disso.
    try:
        code = olist.ler_retorno(endereco, redirect, esperado)
    except (ValueError, seguro.RetornoDeOutroEndereco) as e:
        raise SystemExit("PARADO: %s" % e)
    _consumir(ESTADO, "python3 autorizar_olist.py")
    r = olist.trocar_code_por_token(code, cid, segredo, redirect)
    Path(caminho).write_text("", encoding="utf-8")
    print("\nConectado. Acesso salvo em tokens-olist.json (conteudo nao mostrado).")
    print("  retorno: esvaziado")
    # Nao afirmar prazo: dizer o que o servidor mandou nesta conexao. O numero
    # varia com a configuracao da conta, e cada renovacao reinicia a contagem.
    import time as _t
    agora = int(_t.time())
    horas = (r.get("refresh_expires_at", 0) - agora) / 3600.0
    if horas > 0:
        print("\nA Olist informou que esta renovacao vale %.0f horas sem uso." % horas)
    else:
        print("\nA Olist nao informou prazo de renovacao nesta conexao.")
    print("Cada vez que ela e usada o prazo reinicia — por isso quem roda")
    print("integracao o dia todo nunca ve vencer, e quem abre de vez em quando ve.")
    print("Nada se perde: o custo importado fica na pasta e o painel segue")
    print("funcionando depois que a conexao vence.")
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
