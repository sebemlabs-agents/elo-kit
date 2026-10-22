#!/usr/bin/env python3
"""Importa da Olist (Tiny) o que o marketplace nao tem: o CUSTO do produto.

Por que isto e importacao e nao conexao viva: na Olist o access_token vale 4
horas e o refresh_token vale UM DIA. Uma conexao viva estaria vencida em quase
toda segunda visita — e custo de produto nao muda todo dia. Entao a gente puxa
o custo uma vez, grava na pasta, e o painel usa o arquivo. A margem continua
funcionando dias depois, com a conexao ja vencida.

O limite da conta e de 30 chamadas por minuto, compartilhado entre todos os
aplicativos dela. Por isso o custo se puxa dos produtos que interessam, nao do
catalogo inteiro.

SOMENTE LEITURA: api() levanta PermissionError para qualquer metodo que nao
seja GET, antes de a chamada sair do computador.

Compatibilidade: Python 3.8+, sem dependencia externa.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
TOKENS_FILE = BASE / "tokens-olist.json"
CUSTOS_FILE = BASE / "prometheus-custos.json"

CONTAS = "https://accounts.tiny.com.br/realms/tiny/protocol/openid-connect"
AUTORIZAR = CONTAS + "/auth"
TOKEN = CONTAS + "/token"
API = "https://api.tiny.com.br/public-api/v3"

MARGEM_SEG = 300


class SemAutorizacao(RuntimeError):
    """Ainda nao foi importado nada da Olist nesta pasta."""


class PrecisaReconectar(RuntimeError):
    """O refresh de 1 dia venceu. Nao e erro da pessoa, e o prazo da Olist."""


class ErroDaAPI(RuntimeError):
    """A Olist respondeu com erro."""


def link_de_autorizacao(client_id, redirect_uri):
    """OAuth2 padrao, no Keycloak da Tiny. Escopo minimo: openid."""
    q = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid",
        "response_type": "code",
    })
    return "%s?%s" % (AUTORIZAR, q)


def ler_retorno(endereco):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(endereco).query)
    code = (q.get("code") or [""])[0]
    if not code:
        raise ValueError(
            "Nao achei o code nesse endereco. Cole a barra INTEIRA do navegador "
            "depois de autorizar — ela tem ?code=..."
        )
    return code


def _form(dados):
    req = urllib.request.Request(
        TOKEN,
        data=urllib.parse.urlencode(dados).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8", "replace")
        if "invalid_grant" in corpo:
            raise PrecisaReconectar(_recado_de_reconexao())
        raise ErroDaAPI("A Olist recusou a troca de token (HTTP %s)." % e.code)


def _recado_de_reconexao():
    return (
        "A conexao com a Olist venceu — e isso e esperado: la o refresh dura "
        "apenas 1 dia, diferente do Mercado Livre, que dura meses. Nao se perdeu "
        "nada: o custo que ja foi importado continua na pasta. Para trazer custo "
        "novo, reconecte com:  python3 autorizar_olist.py"
    )


def salvar_tokens(dado):
    import pasta
    agora = int(time.time())
    conteudo = {
        "access_token": dado["access_token"],
        "refresh_token": dado.get("refresh_token", ""),
        "expires_at": agora + int(dado.get("expires_in", 14400)),
        # A documentacao diz 1 dia; respeitamos o que o servidor mandar quando
        # ele mandar, e caimos no 1 dia so na ausencia.
        "refresh_expires_at": agora + int(dado.get("refresh_expires_in", 86400)),
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


def trocar_code_por_token(code, client_id, client_secret, redirect_uri):
    return salvar_tokens(_form({
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }))


def _carregar():
    if not TOKENS_FILE.exists():
        raise SemAutorizacao(
            "Ainda nao conectei a Olist nesta pasta. Rode: python3 autorizar_olist.py")
    return json.loads(TOKENS_FILE.read_text(encoding="utf-8"))


def token_valido(client_id, client_secret):
    """Devolve um access_token util, renovando se precisar.

    Se o refresh de 1 dia tambem venceu, nao tenta nem chamar o servidor: diz
    para reconectar, com o motivo. O erro cru do Keycloak nao ajuda ninguem."""
    t = _carregar()
    agora = int(time.time())
    if t["expires_at"] - MARGEM_SEG > agora:
        return t["access_token"]
    if t.get("refresh_expires_at", 0) <= agora:
        raise PrecisaReconectar(_recado_de_reconexao())
    novo = _form({
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": t["refresh_token"],
    })
    return salvar_tokens(novo)["access_token"]


def api(metodo, caminho, token=None, **parametros):
    """Chamada a API. SO GET — qualquer outro metodo para aqui."""
    if metodo.upper() != "GET":
        raise PermissionError(
            "Este pacote e somente leitura: recusei %s em %s antes de a chamada "
            "sair do seu computador. Alterar produto, pedido ou preco se faz no "
            "proprio ERP, por voce." % (metodo.upper(), caminho)
        )
    url = API + caminho
    if parametros:
        url += "?" + urllib.parse.urlencode(parametros)
    req = urllib.request.Request(
        url, headers={"Authorization": "Bearer %s" % token, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise ErroDaAPI(
                "A Olist recusou (401). Na documentacao dela isso quase nunca e "
                "chave errada: e o USUARIO logado sem permissao no modulo que a "
                "API pediu. Confira o perfil do usuario, nao a credencial.")
        if e.code == 429:
            raise ErroDaAPI(
                "Passou do limite de chamadas. O limite e por CONTA e nao por "
                "aplicativo — 30 por minuto no plano Construa. Espere um pouco "
                "e puxe menos produtos de uma vez.")
        raise ErroDaAPI("A Olist respondeu HTTP %s." % e.code)


def custo_do_produto(id_produto, token):
    """GET /produtos/{id}/preco devolve precoCusto e precoCustoMedio."""
    d = api("GET", "/produtos/%s/preco" % id_produto, token=token)
    return {
        "id_produto": id_produto,
        "preco_custo": d.get("precoCusto"),
        "custo_medio": d.get("precoCustoMedio"),
    }


def gravar_custos(itens):
    """Grava o custo importado na pasta, no contrato de dados do pacote.

    capturado_em e a hora da importacao — e o que diz a idade do custo. Sem
    isso o painel apresentaria custo de semanas atras como se fosse de hoje."""
    agora = time.strftime("%Y-%m-%dT%H:%M:%S%z") or time.strftime("%Y-%m-%dT%H:%M:%S")
    doc = {
        "contrato": "1",
        "skill": "prometheus-conectar-olist",
        "fonte": "olist",
        "gerado_em": agora,
        "capturado_em": agora,
        "itens": list(itens),
    }
    CUSTOS_FILE.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"arquivo": str(CUSTOS_FILE), "itens": len(doc["itens"])}


def custos_guardados():
    """O que a margem usa. Devolve None quando nunca foi importado."""
    if not CUSTOS_FILE.exists():
        return None
    return json.loads(CUSTOS_FILE.read_text(encoding="utf-8"))
