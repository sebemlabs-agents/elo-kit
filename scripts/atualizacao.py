#!/usr/bin/env python3
"""Le e liga a atualizacao automatica do catalogo elo-kit.

Sem isto, uma correcao publicada nunca chega na maquina da pessoa: catalogo
que nao e da Anthropic vem com atualizacao automatica DESLIGADA por padrao.

Uso:
    python3 atualizacao.py            diz se esta ligada
    python3 atualizacao.py --ligar    liga (faz copia dos arquivos antes)

Nao toca em nenhuma outra configuracao, e so mexe na entrada do elo-kit.

Compatibilidade: Python 3.8+.
"""
import json
import os
import shutil
import sys
from pathlib import Path

CATALOGO = "elo-kit"


class SemClaude(RuntimeError):
    """A pasta de configuracao do Claude nao foi encontrada."""


def pasta_config():
    bruto = os.environ.get("CLAUDE_CONFIG_DIR")
    base = Path(bruto).expanduser() if bruto else Path.home() / ".claude"
    if not base.is_dir():
        raise SemClaude(
            "Nao achei a pasta de configuracao do Claude em %s. "
            "O Claude Code ja foi aberto nesta maquina?" % base
        )
    return base


def _pasta_plugins(base):
    bruto = os.environ.get("CLAUDE_CODE_PLUGIN_CACHE_DIR")
    return Path(bruto).expanduser() if bruto else base / "plugins"


def _ler(caminho):
    if not caminho.exists():
        return None
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def _entrada_catalogo(dado):
    """known_marketplaces.json ja apareceu nas duas formas."""
    if not isinstance(dado, dict):
        return None
    mapa = dado.get("marketplaces") if isinstance(dado.get("marketplaces"), dict) else dado
    alvo = mapa.get(CATALOGO)
    return alvo if isinstance(alvo, dict) else None


def estado(base=None):
    """Devolve 'ligada', 'desligada' ou 'nao instalado'."""
    base = base or pasta_config()

    cfg = _ler(base / "settings.json") or {}
    extra = cfg.get("extraKnownMarketplaces")
    if isinstance(extra, dict) and isinstance(extra.get(CATALOGO), dict):
        if CATALOGO in extra and "autoUpdate" in extra[CATALOGO]:
            return "ligada" if extra[CATALOGO]["autoUpdate"] else "desligada"

    conhecidos = _entrada_catalogo(_ler(_pasta_plugins(base) / "known_marketplaces.json"))
    if conhecidos is None and not (isinstance(extra, dict) and CATALOGO in extra):
        return "nao instalado"
    if conhecidos and "autoUpdate" in conhecidos:
        return "ligada" if conhecidos["autoUpdate"] else "desligada"
    return "desligada"


def ligar(base=None):
    """Liga nos dois lugares. Devolve a lista de arquivos alterados."""
    base = base or pasta_config()
    if estado(base) == "nao instalado":
        raise SemClaude(
            "O catalogo elo-kit nao esta registrado nesta maquina. "
            "Instale o pacote primeiro."
        )

    alterados = []

    s = base / "settings.json"
    cfg = _ler(s)
    if isinstance(cfg, dict):
        extra = cfg.setdefault("extraKnownMarketplaces", {})
        if isinstance(extra, dict) and isinstance(extra.get(CATALOGO), dict):
            if extra[CATALOGO].get("autoUpdate") is not True:
                shutil.copy(str(s), str(s) + ".bak-elo")
                extra[CATALOGO]["autoUpdate"] = True
                s.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
                alterados.append(s.name)

    k = _pasta_plugins(base) / "known_marketplaces.json"
    dado = _ler(k)
    alvo = _entrada_catalogo(dado)
    if alvo is not None and alvo.get("autoUpdate") is not True:
        shutil.copy(str(k), str(k) + ".bak-elo")
        alvo["autoUpdate"] = True
        k.write_text(json.dumps(dado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        alterados.append(k.name)

    return alterados


def _main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    agora = estado()
    if agora == "nao instalado":
        print("O pacote elo-kit nao esta instalado nesta maquina.")
        return 1

    if "--ligar" not in args:
        if agora == "ligada":
            print("Atualizacao automatica: LIGADA. As correcoes chegam sozinhas.")
        else:
            print("Atualizacao automatica: DESLIGADA.")
            print("Para ligar:  python3 atualizacao.py --ligar")
        return 0

    if agora == "ligada":
        print("Ja estava ligada. Nada a fazer.")
        return 0

    mudou = ligar()
    print("Atualizacao automatica LIGADA.")
    if mudou:
        print("Alterado: %s (copia de seguranca .bak-elo ao lado)" % ", ".join(mudou))
    print("Vale a partir da proxima vez que o Claude for aberto.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_main())
    except SemClaude as e:
        sys.exit("PARADO: %s" % e)
