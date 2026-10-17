#!/usr/bin/env python3
"""Conecta a conta do Mercado Livre (OAuth 2.0 com PKCE). Roda uma vez; depois o
meli.py renova o acesso sozinho.

Pensado para rodar junto com o Claude sem que nenhum segredo apareca no chat:
a URL de autorizacao (que carrega o App ID) vai para um arquivo, e a URL de
retorno (que carrega o code) e lida de outro arquivo, esvaziado depois do uso.

Passo 1 — gerar a URL de autorizacao:
    python3 autorizar.py
    -> grava ABRIR_NO_NAVEGADOR.txt nesta pasta. Abra o arquivo, copie a URL e
       cole no navegador, logado na conta ADMINISTRADORA do Mercado Livre.

Passo 2 — depois de autorizar, o navegador vai mostrar erro ao abrir o endereco
de retorno. Isso e esperado: o dominio .invalid nao existe de proposito, e o
code fica so na barra de endereco do seu navegador. Copie a URL INTEIRA, cole
no arquivo RETORNO.txt nesta pasta, salve, e rode:
    python3 autorizar.py --arquivo RETORNO.txt

A URL de retorno so e aceita por arquivo: passar pela linha de comando faria o
code aparecer no historico do terminal e no chat.

Compatibilidade: Python 3.8+.
"""
import base64
import hashlib
import json
import os
import secrets
import sys
import urllib.parse
from pathlib import Path

import pasta as pasta_mod
from meli import (BASE, CredenciaisIncompletas, ErroDaAPI, carregar_env,
                  trocar_code_por_token)

# Dominio por pais. O Brasil e o padrao; os outros ficam aqui porque a conta de
# alguns participantes pode ser de outro site do Mercado Livre.
AUTH_POR_SITE = {
    "MLB": "https://auth.mercadolivre.com.br/authorization",
    "MLA": "https://auth.mercadolibre.com.ar/authorization",
    "MLM": "https://auth.mercadolibre.com.mx/authorization",
    "MLC": "https://auth.mercadolibre.cl/authorization",
    "MLU": "https://auth.mercadolibre.com.uy/authorization",
    "MCO": "https://auth.mercadolibre.com.co/authorization",
}
STATE_FILE = BASE / ".oauth_state"
URL_FILE = BASE / "ABRIR_NO_NAVEGADOR.txt"
RETORNO_PADRAO = "RETORNO.txt"


class RetornoInvalido(RuntimeError):
    """A URL de retorno colada no arquivo nao serve."""


def b64url(dados):
    return base64.urlsafe_b64encode(dados).decode().rstrip("=")


def esvaziar(caminho):
    """Apaga um arquivo temporario; se o sistema nao deixar, esvazia."""
    try:
        os.remove(caminho)
        return "apagado"
    except OSError:
        try:
            Path(caminho).write_text("", encoding="utf-8")
            return "esvaziado (pode apagar quando quiser)"
        except OSError:
            return "NAO consegui apagar nem esvaziar — apague manualmente"


def gerar_url(site="MLB"):
    pasta_mod.conferir(BASE)
    cfg = carregar_env()
    state = secrets.token_urlsafe(16)
    verifier = b64url(secrets.token_bytes(32))
    challenge = b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    STATE_FILE.write_text(
        json.dumps({"state": state, "code_verifier": verifier}), encoding="utf-8"
    )
    try:
        os.chmod(STATE_FILE, 0o600)
    except OSError:
        pass
    params = {
        "response_type": "code",
        "client_id": cfg["MELI_APP_ID"],
        "redirect_uri": cfg["MELI_REDIRECT_URI"],
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    base_auth = AUTH_POR_SITE.get(site.upper(), AUTH_POR_SITE["MLB"])
    URL_FILE.write_text(
        "Copie a linha abaixo e cole no navegador, logado na conta ADMINISTRADORA\n"
        "do Mercado Livre (conta de operador ou colaborador nao consegue autorizar):\n\n"
        + base_auth + "?" + urllib.parse.urlencode(params) + "\n\n"
        "Depois de autorizar, o navegador vai mostrar erro ao abrir a pagina de\n"
        "retorno. Isso e esperado — o endereco nao existe de proposito, e o codigo\n"
        "fica so na sua barra de endereco.\n\n"
        "Copie a URL INTEIRA da barra e cole no arquivo RETORNO.txt, nesta pasta.\n",
        encoding="utf-8",
    )
    return URL_FILE


def ler_sessao():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8") or "{}")
    except ValueError:
        return {}


def extrair_code(entrada):
    """Tira o code da URL de retorno, conferindo o state."""
    entrada = (entrada or "").strip().strip('"').strip("'")
    if not entrada:
        raise RetornoInvalido(
            "O arquivo de retorno esta vazio. Cole a URL inteira da barra de "
            "endereco nele, salve e rode de novo."
        )
    if not entrada.startswith("http"):
        return entrada, ler_sessao().get("code_verifier")
    q = urllib.parse.parse_qs(urllib.parse.urlparse(entrada).query)
    if "error" in q:
        raise RetornoInvalido(
            "O Mercado Livre devolveu erro: %s"
            % (q.get("error_description") or q["error"])[0]
        )
    code = (q.get("code") or [None])[0]
    state = (q.get("state") or [None])[0]
    if not code:
        raise RetornoInvalido(
            "Nao achei o parametro 'code' nessa URL. Confira se copiou a URL inteira."
        )
    sessao = ler_sessao()
    if sessao.get("state") and state != sessao["state"]:
        raise RetornoInvalido(
            "O state nao confere — essa URL e de outra tentativa. Refaca o passo 1: "
            "python3 autorizar.py"
        )
    return code, sessao.get("code_verifier")


def concluir(arquivo=RETORNO_PADRAO):
    """Troca o code pelo acesso e limpa os arquivos temporarios."""
    alvo = Path(arquivo)
    if not alvo.is_absolute():
        alvo = BASE / arquivo
    if not alvo.exists():
        raise RetornoInvalido(
            "Nao achei %s. Crie o arquivo nesta pasta e cole a URL de retorno nele."
            % alvo.name
        )
    entrada = alvo.read_text(encoding="utf-8")
    # os temporarios saem de qualquer jeito: o code e de uso unico e nao deve
    # ficar parado no disco, deu certo ou nao.
    try:
        code, verifier = extrair_code(entrada)
        return trocar_code_por_token(code, verifier), esvaziar(alvo)
    finally:
        esvaziar(STATE_FILE)
        esvaziar(URL_FILE)


def _main():
    args = sys.argv[1:]

    if not args or args[0] == "--site":
        site = args[1] if len(args) > 1 else "MLB"
        arq = gerar_url(site)
        print("OK — URL de autorizacao gravada em %s (conteudo nao mostrado aqui)." % arq.name)
        print("\nProximos passos:")
        print("  1. abra %s e copie a URL" % arq.name)
        print("  2. cole no navegador logado na conta ADMINISTRADORA e autorize")
        print("  3. copie a URL inteira que o navegador mostrar (vai dar erro, e esperado)")
        print("  4. cole em %s, salve" % RETORNO_PADRAO)
        print("  5. rode: python3 autorizar.py --arquivo %s" % RETORNO_PADRAO)
        return 0

    if args[0] != "--arquivo" or len(args) < 2:
        print("Uso:")
        print("  python3 autorizar.py                      # passo 1: gera a URL")
        print("  python3 autorizar.py --arquivo RETORNO.txt  # passo 2: conclui")
        print("\nA URL de retorno so e aceita por arquivo, nunca na linha de comando.")
        return 2

    t, limpeza = concluir(args[1])
    print("\nConectado. Acesso salvo em tokens.json (conteudo nao mostrado).")
    print("  conta  : %s" % t["user_id"])
    print("  retorno: %s" % limpeza)
    if not t.get("refresh_token"):
        print("\n  ATENCAO: o Mercado Livre nao devolveu renovacao automatica.")
        print("  O acesso vai parar em cerca de 6 horas. Confira no DevCenter se a")
        print("  aplicacao tem acesso offline e autorize de novo.")
    else:
        print("  renovacao automatica: ligada")
    print("\nConfirme a conta agora:  python3 meli.py me\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_main())
    except (pasta_mod.PastaSincronizada, CredenciaisIncompletas, RetornoInvalido,
            ErroDaAPI) as e:
        sys.exit("PARADO: %s" % e)
