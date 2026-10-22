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
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import seguro

BASE = Path(__file__).resolve().parent
TOKENS_FILE = BASE / "tokens-shopee.json"

HOST = "https://openplatform.shopee.com.br"
CAMINHO_AUTH = "/api/v2/shop/auth_partner"
CAMINHO_TOKEN = "/api/v2/auth/token/get"
CAMINHO_REFRESH = "/api/v2/auth/access_token/get"

# Os UNICOS caminhos em que este pacote faz POST. A promessa de somente leitura
# vale pouco se existir uma funcao que assina POST para qualquer caminho: seria
# o atalho para mudar preco ou anuncio. Fora destes dois, _post recusa antes da
# rede.
CAMINHOS_DE_POST = (CAMINHO_TOKEN, CAMINHO_REFRESH)

# A Shopee devolve access_token de 4 horas e refresh_token de 30 dias.
# Confirmado em producao (expire_in: 14400) e na documentacao.
MARGEM_SEG = 600


_RECADO_CODIGO = (
    "O codigo expirou ou ja foi usado. Ele vale 10 minutos e uma vez so: gere o "
    "link de novo e autorize sem demora entre um passo e outro.")


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
    no meio do fluxo, com um erro que nao diz a causa.

    Le o `hostname`, nao o `netloc`: em `https://usuario:senha@site.com` o
    netloc carrega usuario e senha, o que faria a conferencia olhar para o
    lugar errado e, pior, imprimir credencial na mensagem de erro."""
    p = urllib.parse.urlparse(uri)
    if p.username or p.password:
        raise ValueError(
            "Esse endereco de retorno tem usuario e senha embutidos (a parte "
            "antes do @). Use o endereco limpo, so o dominio — por exemplo "
            "https://seu-projeto.supabase.co."
        )
    host = (p.hostname or "").lower().rstrip(".")
    if p.scheme != "https" or not host or "." not in host:
        raise ValueError(
            "O endereco de retorno precisa ser um dominio HTTPS de verdade, como "
            "https://seu-projeto.supabase.co. A Shopee recusa http, e recusa nome "
            "sem ponto."
        )
    if host.endswith(RESERVADOS):
        raise ValueError(
            "Esse endereco usa um dominio reservado, que nao existe de proposito "
            "— e o truque que a gente usa no Mercado Livre, e e justamente o que "
            "a Shopee NAO aceita. Use um dominio seu, ou o endereco do seu "
            "projeto Supabase."
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


def _colher(q):
    code = (q.get("code") or [""])[0]
    loja = (q.get("shop_id") or q.get("main_account_id") or [""])[0]
    return code, loja


def ler_retorno(endereco, cadastrado=None):
    """Tira o code e o shop_id do endereco que a pessoa colou.

    Ela cola a barra inteira do navegador; a gente nao pede para ela achar o
    pedaco certo. Quando o endereco cadastrado e conhecido, confere que o
    retorno veio DAQUELE DOMINIO.

    Procura o code em dois lugares, e o segundo foi aprendido num ensaio em
    22/10/2026: aplicativo com login costuma redirecionar a visita sem sessao
    e levar a URL original DENTRO de um parametro, percent-encoded
    (`?redirect=%2F%3Fcode%3D...`). O code esta la, so que um nivel abaixo.
    Sem isto o pacote dizia "nao achei o code" para alguem que tinha
    autorizado certinho - e a pessoa nao tem como adivinhar.

    A Shopee nao tem parametro `state`: o `redirect` vai dentro do endereco
    assinado com a partner_key, entao ninguem de fora monta um link que
    devolva para o endereco da pessoa."""
    if cadastrado:
        seguro.conferir_origem(endereco, cadastrado)
    q = urllib.parse.parse_qs(urllib.parse.urlparse(endereco).query)
    code, loja = _colher(q)
    if not code:
        for valores in q.values():
            for v in valores:
                for tentativa in (v, urllib.parse.unquote(v)):
                    dentro = urllib.parse.parse_qs(
                        urllib.parse.urlparse(tentativa).query)
                    c, l = _colher(dentro)
                    if c:
                        return c, int(l) if l else (int(loja) if loja else None)
    if not code:
        raise ValueError(
            "Nao achei o code nesse endereco. Cole a barra INTEIRA do navegador "
            "depois de autorizar - ela tem code=... e shop_id=..."
        )
    return code, int(loja) if loja else None


def _post(caminho, corpo, partner_id, partner_key):
    if caminho not in CAMINHOS_DE_POST:
        raise PermissionError(
            "Este pacote e somente leitura: recusei POST em %s antes de a "
            "chamada sair do seu computador. Os unicos POST permitidos sao os "
            "da propria conexao." % caminho
        )
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
    with seguro.abrir(req, timeout=30) as r:
        dado = json.loads(r.read().decode("utf-8"))
    if dado.get("error"):
        raise ErroDaAPI(_explicar(dado))
    return dado


# Forma de codigo de erro da Shopee: snake_case minusculo, com pelo menos um
# sublinhado — error_param, error_sign, invalid_code. Conferida no valor CRU,
# nunca no minusculado: um token em base64 minusculado viraria uma palavra
# aceitavel, e era justamente o que esta forma precisa barrar. Token tem
# maiuscula e nao tem sublinhado; nao atravessa.
_TEM_FORMA_DE_CODIGO = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")


def _explicar(dado):
    """Traduz o erro da Shopee sem repetir o texto que ela mandou.

    Classifica pelo CODIGO (`error`), que e de maquina, e nao pelo `message`,
    que e texto livre em ingles: uma palavra solta no meio de uma frase faria o
    pacote dar o diagnostico errado e mandar a pessoa refazer o que estava
    certo. O message so entra quando nao veio codigo nenhum.

    E nada do corpo remoto e impresso. Se um dia a Shopee devolver no texto um
    pedaco da chamada — assinatura, token, parametro — repetir isso seria vazar
    segredo pela mensagem de erro. Do corpo sai apenas o codigo, filtrado."""
    cru = str(dado.get("error", ""))[:64]
    codigo = cru.lower()
    if "invalid_code" in codigo or "expire" in codigo:
        return _RECADO_CODIGO
    if "sign" in codigo:
        return ("A Shopee recusou a assinatura. Confira se o partner_id e a chave "
                "sao do mesmo ambiente — a de teste nao serve na producao.")
    if "partner" in codigo or "auth" in codigo:
        return ("A Shopee nao reconheceu a aplicacao. Confira o partner_id, e se a "
                "aplicacao ja foi aprovada para producao.")
    if not codigo and "expire" in str(dado.get("message", "")).lower():
        return _RECADO_CODIGO
    # Só repete o codigo quando ele TEM FORMA de codigo de erro: minusculas,
    # digitos e sublinhado, curto. Filtrar caractere nao bastava — um token
    # tambem passa pelo filtro. Credencial tem maiuscula, e comprida e nao e
    # palavra; nada disso atravessa esta forma. O que nao couber nela some.
    if len(cru) <= 32 and _TEM_FORMA_DE_CODIGO.match(cru):
        return ("A Shopee recusou a chamada (codigo: %s). Nao mostro a resposta "
                "dela aqui porque ela pode trazer pedacos da sua credencial."
                % cru)
    return ("A Shopee recusou a chamada e nao devolveu um codigo que eu "
            "reconheca. Nao mostro a resposta dela aqui porque ela pode trazer "
            "pedacos da sua credencial — veja o erro no console do Open "
            "Platform, em Shop Authorization.")


def salvar_tokens(dado, partner_id, shop_id):
    """Guarda o acesso na pasta da pessoa, ja com a permissao fechada.

    Grava por substituicao atomica: o arquivo nasce restrito ao dono e so
    depois toma o lugar do antigo. Gravar primeiro e fechar depois deixaria o
    token legivel por outros usuarios da maquina nesse intervalo."""
    conteudo = {
        "partner_id": partner_id,
        "shop_id": shop_id,
        "access_token": dado["access_token"],
        "refresh_token": dado.get("refresh_token", ""),
        "expires_at": int(time.time()) + int(dado.get("expire_in", 14400)),
        "atualizado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    estado = seguro.gravar_protegido(
        TOKENS_FILE, json.dumps(conteudo, indent=2, ensure_ascii=False) + "\n")
    conteudo.update(estado)
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
    # Sem seguir redirecionamento: a URL leva access_token e assinatura na
    # query, e um 302 os reenviaria para um host que nao escolhemos.
    with seguro.abrir(urllib.request.Request(url), timeout=30) as r:
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
