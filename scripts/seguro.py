#!/usr/bin/env python3
"""Primitivas de seguranca que todos os canais compartilham.

Tres problemas que nenhum canal resolve sozinho, levantados na revisao
cross-vendor de 22/10/2026:

1. Gravar segredo em dois tempos. `write_text` seguido de `chmod` deixa o
   arquivo legivel por outros usuarios durante um instante. Em maquina de uso
   compartilhado — recepcao, balcao, computador de familia — esse instante
   basta. `gravar_protegido` cria o arquivo ja restrito e so entao o coloca
   no lugar, de uma vez.

2. urllib reenvia cabecalho em redirecionamento. Se o servidor responder 302
   para outro endereco, o `Authorization: Bearer ...` vai junto, para um host
   que a gente nao escolheu. `abrir` recusa redirecionamento em qualquer
   chamada que leve credencial.

3. O retorno do navegador chega colado a mao. Conferir que ele veio do mesmo
   endereco que foi cadastrado evita trocar por token um `?code=` que a pessoa
   copiou de outro lugar — e, no uso normal, pega o erro mais comum: colar a
   URL errada.

Compatibilidade: Python 3.8+, sem dependencia externa.
"""
import os
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path


class RedirecionamentoRecusado(RuntimeError):
    """O servidor pediu para reenviar a credencial a outro endereco."""


class RetornoDeOutroEndereco(ValueError):
    """O endereco colado nao e o mesmo que foi cadastrado no canal."""


class _SemRedirecionamento(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RedirecionamentoRecusado(
            "O servidor respondeu com um redirecionamento (HTTP %s), e seguir "
            "esse redirecionamento reenviaria a sua credencial para outro "
            "endereco. Recusei antes de reenviar. Se isso insistir, o problema "
            "esta do lado do canal — nao e erro seu." % code
        )


_ABRIDOR = urllib.request.build_opener(_SemRedirecionamento)


def abrir(req, timeout=30):
    """urlopen que NAO segue redirecionamento.

    Use em toda chamada que leve credencial — token, assinatura ou segredo
    de cliente. Erros HTTP continuam chegando como urllib.error.HTTPError,
    igual ao urlopen, para o tratamento de cada canal seguir funcionando."""
    return _ABRIDOR.open(req, timeout=timeout)


def fechado(arquivo):
    """Diz se o arquivo esta de fato fora do alcance de grupo e de outros.

    Mede o resultado em vez de confiar no chmod: e a unica forma de o relato
    ser verdadeiro nos dois sistemas."""
    try:
        return os.stat(arquivo).st_mode & 0o077 == 0
    except OSError:
        return False


def gravar_protegido(destino, conteudo):
    """Grava arquivo de segredo ja restrito ao dono, sem janela de exposicao.

    Escreve num temporario na MESMA pasta — para a substituicao ser atomica —
    com a permissao fechada desde a abertura, e so depois substitui o destino.
    Se a maquina cair no meio, o destino continua com o conteudo anterior
    inteiro; nunca truncado.

    Devolve {"protegido": bool, "motivo": str|None}. Nao recusa gravar quando
    nao consegue confirmar a restricao: no Windows a permissao e controlada por
    outro mecanismo, que este pacote ainda nao le, e recusar deixaria todo
    usuario de Windows sem conexao. Quem chama avisa a pessoa."""
    destino = Path(destino)
    dados = conteudo.encode("utf-8") if isinstance(conteudo, str) else conteudo
    fd, tmp = tempfile.mkstemp(dir=str(destino.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(dados)
        os.replace(tmp, str(destino))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    if fechado(destino):
        return {"protegido": True, "motivo": None}
    try:
        os.chmod(destino, 0o600)
    except OSError:
        return {"protegido": False, "motivo": "sem_permissao_para_mudar"}
    if fechado(destino):
        return {"protegido": True, "motivo": None}
    return {"protegido": False, "motivo": "nao_verificado_neste_sistema"}


def _partes(endereco):
    p = urllib.parse.urlparse(endereco)
    host = (p.hostname or "").lower().rstrip(".")
    porta = p.port or (443 if p.scheme == "https" else 80 if p.scheme == "http" else None)
    caminho = (p.path or "/").rstrip("/") or "/"
    return p.scheme.lower(), host, porta, caminho


def resumo(endereco):
    """So esquema, host e caminho — nunca a query, que carrega o code."""
    e, h, _, c = _partes(endereco)
    return "%s://%s%s" % (e, h, c) if h else "(endereco nao reconhecido)"


def conferir_origem(endereco, cadastrado):
    """Recusa retorno que nao veio do endereco cadastrado no canal.

    Compara esquema, host, porta e caminho; ignora a query, que e justamente
    a parte que muda. Nunca ecoa a query na mensagem de erro."""
    if _partes(endereco) != _partes(cadastrado):
        raise RetornoDeOutroEndereco(
            "Esse endereco nao veio de onde deveria. O canal foi cadastrado "
            "para devolver em %s, e o que voce colou e de %s.\n"
            "Cole a barra do navegador da pagina que abriu DEPOIS de autorizar "
            "— nao o endereco de outra aba." % (resumo(cadastrado), resumo(endereco))
        )
    return True
