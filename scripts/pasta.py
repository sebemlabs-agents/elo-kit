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
MELI_REDIRECT_URI=https://radar-meli.invalid/callback
"""


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


def preparar(caminho=None):
    """Confere a pasta e deixa os arquivos de apoio no lugar.

    Nunca sobrescreve credenciais.txt — quem ja preencheu nao perde nada."""
    pasta = Path(caminho or BASE)
    conferir(pasta)
    pasta.mkdir(parents=True, exist_ok=True)

    criados = []
    cred = pasta / "credenciais.txt"
    if not cred.exists():
        cred.write_text(CREDENCIAIS_EXEMPLO, encoding="utf-8")
        criados.append(cred.name)

    gi = pasta / ".gitignore"
    if not gi.exists():
        gi.write_text(GITIGNORE, encoding="utf-8")
        criados.append(gi.name)

    protegidos = []
    for nome in ARQUIVOS_SENSIVEIS:
        alvo = pasta / nome
        if alvo.exists():
            try:
                os.chmod(alvo, 0o600)
                protegidos.append(nome)
            except OSError:
                pass

    return {"pasta": str(pasta), "criados": criados, "protegidos": protegidos}


def _main():
    try:
        r = preparar()
    except PastaSincronizada as e:
        print("PARADO: %s" % e)
        return 1
    print("Pasta pronta: %s" % r["pasta"])
    if r["criados"]:
        print("Criados: %s" % ", ".join(r["criados"]))
    if r["protegidos"]:
        print("Permissao fechada em: %s" % ", ".join(r["protegidos"]))
    print("\nProximo passo: abra credenciais.txt, preencha App ID e Client Secret, salve,")
    print("e rode: python3 meli.py check")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
