#!/usr/bin/env python3
"""Prepara a pasta do vendedor antes de qualquer credencial ser gravada.

Por que isto existe: o risco mais provavel neste pacote nao e invasao, e a
pasta estar dentro de um servico de sincronizacao. Se credenciais.txt ou
tokens.json cairem dentro de Dropbox, iCloud, Google Drive ou OneDrive, o
token da conta vai para a nuvem sem ninguem perceber. Entao a verificacao
acontece ANTES de gravar, e para o processo quando detecta.

CLI:
    python3 pasta.py             # verifica e prepara a pasta onde o script esta

Compatibilidade: Python 3.8+.
"""
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent

# Nomes de pasta que denunciam sincronizacao. Comparados em minusculas contra
# cada parte do caminho.
SERVICOS = {
    "dropbox": "Dropbox",
    "onedrive": "OneDrive",
    "google drive": "Google Drive",
    "googledrive": "Google Drive",
    "my drive": "Google Drive",
    "icloud drive": "iCloud Drive",
    "icloud~": "iCloud",
    "mobile documents": "iCloud Drive",
    "cloudstorage": "servico de nuvem do macOS",
    "mega": "MEGA",
    "pcloud": "pCloud",
    "sync.com": "Sync.com",
    "nextcloud": "Nextcloud",
}

ARQUIVOS_SENSIVEIS = (
    "credenciais.txt",
    ".env",
    "tokens.json",
    ".oauth_state",
    "ABRIR_NO_NAVEGADOR.txt",
    "RETORNO.txt",
)

# Conjunto FECHADO de motivos. O relato nunca carrega texto de excecao nem
# saida de comando: so um destes codigos, para nao vazar nada por acidente.
MOTIVOS_SEM_PROTECAO = {
    # Dizer "este sistema nao protege" seria falso: o Windows protege, por DACL,
    # que nao e o que o modo POSIX descreve e nao e o que conseguimos ler aqui.
    # O que podemos afirmar e so isto: nao foi verificado.
    "nao_verificado_neste_sistema":
        "o pacote nao conseguiu confirmar a restricao de leitura neste sistema "
        "(no Windows a permissao e controlada por outro mecanismo, que o pacote "
        "ainda nao le)",
    "sem_permissao_para_mudar":
        "o sistema nao deixou mudar a permissao deste arquivo",
}


GITIGNORE = """credenciais.txt
.env
tokens.json
tokens.backup.json
.oauth_state
ABRIR_NO_NAVEGADOR.txt
RETORNO.txt
elo-*.json
painel.html
dados.json
__pycache__/
*.pyc
"""

CREDENCIAIS_EXEMPLO = """# Credenciais da SUA aplicacao do Mercado Livre
# (developers.mercadolivre.com.br/devcenter -> Minhas aplicacoes)
#
# Preencha as duas primeiras linhas depois do "=" e salve.
# NUNCA cole estes valores no chat, em print ou em mensagem para alguem.
MELI_APP_ID=
MELI_CLIENT_SECRET=
#
# Precisa ser IDENTICO ao "URL de redirecionamento" cadastrado na aplicacao.
# .invalid e um dominio reservado que nunca abre: o code nao sai do seu navegador.
MELI_REDIRECT_URI=%(uri)s
"""

URI_PADRAO = "https://radar-meli.invalid/callback"


def apelido(nome):
    """Transforma o nome da loja num rotulo seguro para dominio.

    Quem digita duas vezes erra uma. Por isso ninguem digita a URL: ela e
    gerada aqui e a pessoa copia do arquivo para o DevCenter.
    """
    import re
    import unicodedata

    cru = unicodedata.normalize("NFKD", str(nome or ""))
    cru = cru.encode("ascii", "ignore").decode("ascii").lower()
    limpo = re.sub(r"[^a-z0-9]+", "-", cru).strip("-")
    limpo = re.sub(r"-{2,}", "-", limpo)[:40].strip("-")
    if not limpo or not limpo[0].isalnum():
        raise ValueError(
            "Nao consegui formar um apelido com '%s'. "
            "Use letras e numeros, por exemplo o nome da loja." % nome
        )
    return limpo


def uri_de(nome=None):
    """Devolve a URL de retorno desta pessoa."""
    if not nome:
        return URI_PADRAO
    return "https://%s.invalid/callback" % apelido(nome)


class PastaSincronizada(RuntimeError):
    """A pasta esta dentro de um servico de sincronizacao de arquivos."""


def servico_de_sincronizacao(caminho):
    """Nome do servico detectado no caminho, ou None.

    Olha cada parte do caminho porque a pasta pode estar varios niveis abaixo
    (ex.: ~/Library/CloudStorage/GoogleDrive-.../Meu Drive/projetos/radar)."""
    partes = [p.lower() for p in Path(caminho).resolve().parts]
    for parte in partes:
        for marca, nome in SERVICOS.items():
            if marca in parte:
                return nome
    return None


def conferir(caminho=None):
    """Levanta PastaSincronizada quando a pasta nao serve para guardar segredo."""
    caminho = Path(caminho or BASE)
    servico = servico_de_sincronizacao(caminho)
    if servico:
        raise PastaSincronizada(
            "Esta pasta esta dentro do %s, que sincroniza arquivos com a nuvem. "
            "A credencial da sua conta nao pode ficar ai. Crie uma pasta fora do "
            "servico de sincronizacao (por exemplo em Documentos, fora do %s) e "
            "rode de novo." % (servico, servico)
        )
    return True


def fechado(arquivo):
    """Diz se o arquivo esta de fato fora do alcance de grupo e de outros.

    Mede o resultado em vez de confiar no chmod: e a unica forma de o relato
    ser verdadeiro nos dois sistemas."""
    try:
        return os.stat(arquivo).st_mode & 0o077 == 0
    except OSError:
        return False


def preparar(caminho=None, nome=None):
    """Confere a pasta e deixa os arquivos de apoio no lugar.

    `nome` e o nome da loja: vira a URL de retorno propria da pessoa.
    Nunca sobrescreve credenciais.txt — quem ja preencheu nao perde nada."""
    pasta = Path(caminho or BASE)
    conferir(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    uri = uri_de(nome)

    criados = []
    cred = pasta / "credenciais.txt"
    if not cred.exists():
        cred.write_text(CREDENCIAIS_EXEMPLO % {"uri": uri}, encoding="utf-8")
        criados.append(cred.name)

    gi = pasta / ".gitignore"
    if not gi.exists():
        gi.write_text(GITIGNORE, encoding="utf-8")
        criados.append(gi.name)

    protegidos = []
    nao_protegidos = []
    for nome in ARQUIVOS_SENSIVEIS:
        alvo = pasta / nome
        if not alvo.exists():
            continue
        try:
            os.chmod(alvo, 0o600)
        except OSError:
            nao_protegidos.append({"arquivo": nome,
                                   "motivo": "sem_permissao_para_mudar"})
            continue
        # Nao basta o chmod nao dar erro. No Windows ele honra so o atributo de
        # somente-leitura e ignora o resto em silencio. Entao conferimos o que
        # ficou de fato: nenhum bit de grupo nem de outros.
        if fechado(alvo):
            protegidos.append(nome)
        else:
            nao_protegidos.append({"arquivo": nome,
                                   "motivo": "nao_verificado_neste_sistema"})

    try:
        os.chmod(pasta, 0o700)
    except OSError:
        pass

    return {"pasta": str(pasta), "criados": criados, "protegidos": protegidos,
            "nao_protegidos": nao_protegidos, "pasta_fechada": fechado(pasta),
            "uri": uri}


def _main():
    nome = None
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if "--nome" in args:
        pos = args.index("--nome")
        if pos + 1 < len(args):
            nome = args[pos + 1]
    try:
        r = preparar(nome=nome)
    except (PastaSincronizada, ValueError) as e:
        print("PARADO: %s" % e)
        return 1
    print("Pasta pronta: %s" % r["pasta"])
    if r["criados"]:
        print("Criados: %s" % ", ".join(r["criados"]))
    if r["protegidos"]:
        print("Permissao fechada em: %s" % ", ".join(r["protegidos"]))
    for item in r["nao_protegidos"]:
        print("ATENCAO: nao foi possivel fechar a permissao de %s — %s"
              % (item["arquivo"], MOTIVOS_SEM_PROTECAO[item["motivo"]]))
    if r["nao_protegidos"]:
        print("Os arquivos seguem nesta pasta e o pacote nao envia nada para")
        print("fora. O que nao da para prometer e que outro usuario desta")
        print("maquina nao consiga abrir o arquivo — isso o pacote nao verificou.")
    if not r["pasta_fechada"]:
        print("ATENCAO: nao foi possivel confirmar a restricao de leitura da")
        print("propria pasta. Arquivo fechado dentro de pasta aberta nao protege.")
    print("\nURL de retorno desta pasta (copie do arquivo, nao digite):")
    print("  %s" % r["uri"])
    print("\nProximo passo: cadastre essa URL na aplicacao do DevCenter, depois abra")
    print("credenciais.txt, preencha App ID e Client Secret, salve, e rode:")
    print("  python3 meli.py check")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
