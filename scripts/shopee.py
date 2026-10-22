#!/usr/bin/env python3
"""Cliente SOMENTE LEITURA da conta Shopee do proprio vendedor.

Por que este arquivo existe separado do meli.py: a Shopee nao usa OAuth puro.
Cada chamada leva uma assinatura HMAC-SHA256 sobre partner_id + caminho +
timestamp, e errar a base da assinatura e o erro mais caro do fluxo — ela
recusa sem dizer por que.

SOMENTE LEITURA: api() levanta PermissionError para qualquer metodo que nao
seja GET, antes de a chamada sair do computador. A garantia e codigo, nao
promessa.

Host: openplatform.shopee.com.br (o do Brasil; a documentacao global usa outro).

Compatibilidade: Python 3.8+, sem dependencia externa.
"""
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
TOKENS_FILE = BASE / "tokens-shopee.json"

HOST = "https://openplatform.shopee.com.br"
CAMINHO_AUTH = "/api/v2/shop/auth_partner"
CAMINHO_TOKEN = "/api/v2/auth/token/get"
CAMINHO_REFRESH = "/api/v2/auth/access_token/get"

# A Shopee devolve access_token de 4 horas e refresh_token de 30 dias.
# Confirmado em producao (expire_in: 14400) e na documentacao.
MARGEM_SEG = 600


class SemAutorizacao(RuntimeError):
    """Ainda nao foi feita a autorizacao (nao existe tokens-shopee.json)."""


class ErroDaAPI(RuntimeError):
    """A Shopee respondeu com erro."""


def assinar(partner_id, caminho, agora, partner_key):
    """A base e a concatenacao crua: partner_id + caminho + timestamp.

    Sem separador, sem query string, nessa ordem. E o detalhe que a
    documentacao mostra de relance e que quebra silenciosamente quando errado."""
    base = ("%s%s%s" % (partner_id, caminho, agora)).encode("utf-8")
    chave = partner_key.encode("utf-8") if isinstance(partner_key, str) else partner_key
    return hmac.new(chave, base, hashlib.sha256).hexdigest()


# TLDs reservados pela IANA que nunca resolvem. O .invalid e o que a pessoa
# escreve por habito, porque e o que o Mercado Livre usa — e e justamente o que
# a Shopee recusa. Barrar aqui evita a mensagem inutil que ela devolve.
RESERVADOS = (".invalid", ".test", ".example", ".localhost")


def conferir_retorno(uri):
    """A Shopee so aceita dominio HTTPS que exista de verdade.

    Testado em 22/10/2026: `.invalid` e nome sem ponto sao recusados na propria
    tela de criacao do aplicativo. Conferimos aqui para a pessoa nao descobrir
    no meio do fluxo, com um erro que nao diz a causa."""
    p = urllib.parse.urlparse(uri)
    if p.scheme != "https" or not p.netloc or "." not in p.netloc:
        raise ValueError(
            "O endereco de retorno precisa ser um dominio HTTPS de verdade, como "
            "https://seu-projeto.supabase.co. A Shopee recusa http, e recusa nome "
            "sem ponto."
        )
    host = p.netloc.split(":")[0].lower().rstrip(".")
    if host.endswith(RESERVADOS):
        raise ValueError(
            "'%s' e um dominio reservado, que nao existe de proposito — e o truque "
            "que a gente usa no Mercado Livre, e e justamente o que a Shopee NAO "
            "aceita. Use um dominio seu, ou o endereco do seu projeto Supabase."
            % host
        )
    return uri


def link_de_autorizacao(partner_id, partner_key, redirect, agora=None):
    """Monta o endereco que a pessoa abre no navegador para autorizar."""
    conferir_retorno(redirect)
    agora = int(agora if agora is not None else time.time())
    sign = assinar(partner_id, CAMINHO_AUTH, agora, partner_key)
    q = urllib.parse.urlencode(
        {"partner_id": partner_id, "timestamp": agora, "sign": sign,
         "redirect": redirect}
    )
    return "%s%s?%s" % (HOST, CAMINHO_AUTH, q)


def ler_retorno(endereco):
    """Tira o code e o shop_id do endereco que a pessoa colou.

    Ela cola a barra inteira do navegador; a gente nao pede para ela achar o
    pedaco certo."""
    q = urllib.parse.parse_qs(urllib.parse.urlparse(endereco).query)
    code = (q.get("code") or [""])[0]
    if not code:
        raise ValueError(
            "Nao achei o code nesse endereco. Cole a barra INTEIRA do navegador "
            "depois de autorizar — ela tem ?code=... e &shop_id=..."
        )
    loja = (q.get("shop_id") or q.get("main_account_id") or [""])[0]
    return code, int(loja) if loja else None


def _post(caminho, corpo, partner_id, partner_key):
    agora = int(time.time())
    sign = assinar(partner_id, caminho, agora, partner_key)
    q = urllib.parse.urlencode(
        {"partner_id": partner_id, "timestamp": agora, "sign": sign})
    req = urllib.request.Request(
        "%s%s?%s" % (HOST, caminho, q),
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        dado = json.loads(r.read().decode("utf-8"))
    if dado.get("error"):
        raise ErroDaAPI(_explicar(dado))
    return dado


def _explicar(dado):
    erro = dado.get("error", "")
    msg = dado.get("message", "")
    if "invalid_code" in erro or "expire" in (erro + msg).lower():
        return ("O codigo expirou ou ja foi usado. Ele vale 10 minutos e uma vez so: "
                "gere o link de novo e autorize sem demora entre um passo e outro.")
    if "sign" in erro:
        return ("A Shopee recusou a assinatura. Confira se o partner_id e a chave "
                "sao do mesmo ambiente — a de teste nao serve na producao.")
    return "A Shopee respondeu: %s %s" % (erro, msg)


def salvar_tokens(dado, partner_id, shop_id):
    """Guarda o acesso na pasta da pessoa e confere se a permissao fechou."""
    import pasta
    conteudo = {
        "partner_id": partner_id,
        "shop_id": shop_id,
        "access_token": dado["access_token"],
        "refresh_token": dado.get("refresh_token", ""),
        "expires_at": int(time.time()) + int(dado.get("expire_in", 14400)),
        "atualizado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    TOKENS_FILE.write_text(
        json.dumps(conteudo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    conteudo["protegido"] = True
    conteudo["motivo"] = None
    try:
        os.chmod(TOKENS_FILE, 0o600)
    except OSError:
        conteudo["protegido"] = False
        conteudo["motivo"] = "sem_permissao_para_mudar"
    else:
        if not pasta.fechado(TOKENS_FILE):
            conteudo["protegido"] = False
            conteudo["motivo"] = "nao_verificado_neste_sistema"
    return conteudo


def trocar_code_por_token(code, shop_id, partner_id, partner_key):
    corpo = {"code": code, "partner_id": partner_id}
    if shop_id:
        corpo["shop_id"] = shop_id
    return salvar_tokens(
        _post(CAMINHO_TOKEN, corpo, partner_id, partner_key), partner_id, shop_id)


def renovar(partner_key):
    """Troca o refresh_token por um par novo.

    O refresh da Shopee e de USO UNICO, igual ao do Mercado Livre: duas
    renovacoes ao mesmo tempo derrubam a conexao. Por isso nao se copia
    tokens-shopee.json para outra maquina."""
    t = _carregar()
    dado = _post(CAMINHO_REFRESH,
                 {"refresh_token": t["refresh_token"], "shop_id": t["shop_id"],
                  "partner_id": t["partner_id"]},
                 t["partner_id"], partner_key)
    return salvar_tokens(dado, t["partner_id"], t["shop_id"])


def _carregar():
    if not TOKENS_FILE.exists():
        raise SemAutorizacao(
            "Ainda nao conectei nenhuma loja da Shopee nesta pasta. "
            "Rode: python3 autorizar_shopee.py")
    return json.loads(TOKENS_FILE.read_text(encoding="utf-8"))


def api(metodo, caminho, **parametros):
    """Chamada a API. SO GET — qualquer outro metodo para aqui."""
    if metodo.upper() != "GET":
        raise PermissionError(
            "Este pacote e somente leitura: recusei %s em %s antes de a chamada "
            "sair do seu computador. Alterar anuncio, preco ou pedido se faz no "
            "painel da Shopee, por voce." % (metodo.upper(), caminho)
        )
    t = _carregar()
    partner_key = os.environ.get("SHOPEE_PARTNER_KEY") or _chave_do_arquivo()
    agora = int(time.time())
    sign = assinar(t["partner_id"], caminho, agora, partner_key)
    q = {"partner_id": t["partner_id"], "timestamp": agora, "sign": sign,
         "access_token": t["access_token"], "shop_id": t["shop_id"]}
    q.update(parametros)
    url = "%s%s?%s" % (HOST, caminho, urllib.parse.urlencode(q))
    with urllib.request.urlopen(url, timeout=30) as r:
        dado = json.loads(r.read().decode("utf-8"))
    if dado.get("error"):
        raise ErroDaAPI(_explicar(dado))
    return dado


def _chave_do_arquivo():
    import meli
    cfg = meli._ler_arquivo_env()
    chave = cfg.get("SHOPEE_PARTNER_KEY", "")
    if not chave:
        raise ErroDaAPI(
            "Falta SHOPEE_PARTNER_KEY em credenciais.txt. Abra o arquivo, "
            "preencha depois do '=' e salve. Nunca cole a chave no chat.")
    return chave
