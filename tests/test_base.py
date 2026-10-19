"""Testes da base do pacote: cliente so-leitura, pasta, contrato e painel.

Rodar:  python3 -m pytest tests -q        (na raiz do repositorio)
"""
import json
import sys
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import contrato  # noqa: E402
import meli  # noqa: E402
import criativos  # noqa: E402
import painel  # noqa: E402
import pasta as pasta_mod  # noqa: E402
import atualizacao  # noqa: E402


CONTA = {"id": 123456789, "apelido": "LOJA EXEMPLO", "site": "MLB"}
PERIODO = {"de": "2026-07-19", "ate": "2026-10-17"}


# ---------------------------------------------------------------- so leitura

def test_cliente_recusa_metodo_que_nao_e_get():
    with pytest.raises(PermissionError):
        meli.request("POST", "/items/MLB123")


@pytest.mark.parametrize("metodo", ["PUT", "DELETE", "PATCH", "post", "put"])
def test_recusa_todos_os_metodos_de_escrita(metodo):
    with pytest.raises(PermissionError):
        meli.request(metodo, "/items/MLB123")


def test_mensagem_de_recusa_diz_que_nada_foi_alterado():
    with pytest.raises(PermissionError) as erro:
        meli.request("DELETE", "/items/MLB123")
    assert "nada e alterado" in str(erro.value).lower()


def test_check_nunca_devolve_valor_de_credencial(tmp_path, monkeypatch):
    arq = tmp_path / "credenciais.txt"
    arq.write_text(
        "MELI_APP_ID=1234567890\nMELI_CLIENT_SECRET=segredo-que-nao-pode-vazar\n"
        "MELI_REDIRECT_URI=https://radar-meli.invalid/callback\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(meli, "ENV_FILE", arq)
    monkeypatch.setattr(meli, "TOKENS_FILE", tmp_path / "tokens.json")
    situacao = meli.situacao_credenciais()
    bruto = json.dumps(situacao, ensure_ascii=False)
    assert "segredo-que-nao-pode-vazar" not in bruto
    assert "1234567890" not in bruto
    assert situacao["chaves"]["MELI_CLIENT_SECRET"] == "preenchido"


def test_credenciais_vazias_sao_reportadas_sem_derrubar(tmp_path, monkeypatch):
    arq = tmp_path / "credenciais.txt"
    arq.write_text("MELI_APP_ID=\nMELI_CLIENT_SECRET=\nMELI_REDIRECT_URI=\n", encoding="utf-8")
    monkeypatch.setattr(meli, "ENV_FILE", arq)
    monkeypatch.setattr(meli, "TOKENS_FILE", tmp_path / "tokens.json")
    monkeypatch.delenv("MELI_APP_ID", raising=False)
    monkeypatch.delenv("MELI_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("MELI_REDIRECT_URI", raising=False)
    assert meli.situacao_credenciais()["chaves"]["MELI_APP_ID"] == "VAZIO"
    with pytest.raises(meli.CredenciaisIncompletas):
        meli.carregar_env()


def test_erro_de_conta_de_operador_vira_mensagem_em_portugues():
    msg = meli.traduzir_erro(400, '{"error":"invalid_operator_user_id"}')
    assert "administradora" in msg.lower()


def test_erro_de_redirect_uri_explica_o_que_conferir():
    msg = meli.traduzir_erro(400, '{"message":"your client callback has to match with the redirect_uri param"}')
    assert "caractere por caractere" in msg.lower()


# -------------------------------------------------------------------- pasta

def test_recusa_pasta_dentro_de_servico_de_sincronizacao(tmp_path):
    alvo = tmp_path / "Dropbox" / "radar-meli"
    alvo.mkdir(parents=True)
    with pytest.raises(pasta_mod.PastaSincronizada, match="sincroniz"):
        pasta_mod.preparar(alvo)


@pytest.mark.parametrize(
    "trecho", ["Dropbox", "OneDrive", "Google Drive", "iCloud Drive", "CloudStorage"]
)
def test_detecta_os_servicos_mais_comuns(tmp_path, trecho):
    alvo = tmp_path / trecho / "pasta"
    alvo.mkdir(parents=True)
    assert pasta_mod.servico_de_sincronizacao(alvo) is not None


def test_pasta_comum_passa(tmp_path):
    alvo = tmp_path / "Documentos" / "radar-meli"
    alvo.mkdir(parents=True)
    assert pasta_mod.servico_de_sincronizacao(alvo) is None


def test_preparar_cria_apoio_e_nunca_sobrescreve_credenciais(tmp_path):
    cred = tmp_path / "credenciais.txt"
    cred.write_text("MELI_APP_ID=ja-estava-aqui\n", encoding="utf-8")
    r = pasta_mod.preparar(tmp_path)
    assert cred.read_text(encoding="utf-8") == "MELI_APP_ID=ja-estava-aqui\n"
    assert (tmp_path / ".gitignore").exists()
    assert "credenciais.txt" not in r["criados"]


def test_gitignore_cobre_os_arquivos_sensiveis(tmp_path):
    pasta_mod.preparar(tmp_path)
    gi = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    for nome in ("credenciais.txt", "tokens.json", ".oauth_state", "RETORNO.txt"):
        assert nome in gi


# ------------------------------------------------------------------ contrato

def test_periodo_sem_pedidos_marca_faltando_em_vez_de_zero(tmp_path):
    dado = contrato.gravar(
        "elo-caixa", CONTA, PERIODO, resumo={}, itens=[],
        faltando=["pedidos"],
        lacunas={"pedidos": "nao houve pedido pago neste periodo"},
        pasta=tmp_path,
    )
    assert dado["itens"] == []
    assert "pedidos" in dado["faltando"]
    assert dado["resumo"] == {}


def test_lacuna_sem_explicacao_e_recusada(tmp_path):
    with pytest.raises(contrato.ContratoInvalido, match="sem explicacao"):
        contrato.gravar(
            "elo-margem", CONTA, PERIODO, resumo={}, itens=[],
            faltando=["custo"], pasta=tmp_path,
        )


def test_dinheiro_como_texto_e_recusado(tmp_path):
    with pytest.raises(contrato.ContratoInvalido, match="dinheiro"):
        contrato.gravar(
            "elo-margem", CONTA, PERIODO, resumo={},
            itens=[{"mlb": "MLB1", "preco": "1.234,56"}], pasta=tmp_path,
        )


def test_resumo_aninhado_e_recusado(tmp_path):
    with pytest.raises(contrato.ContratoInvalido, match="aninhado"):
        contrato.gravar(
            "elo-promocoes", CONTA, PERIODO,
            resumo={"totais": {"a": 1}}, itens=[], pasta=tmp_path,
        )


def test_fonte_invalida_e_recusada(tmp_path):
    with pytest.raises(contrato.ContratoInvalido, match="fonte"):
        contrato.gravar(
            "elo-promocoes", CONTA, PERIODO, resumo={}, itens=[],
            fonte="producao", pasta=tmp_path,
        )


def test_conta_sem_id_e_recusada_quando_le_a_conta(tmp_path):
    with pytest.raises(contrato.ContratoInvalido, match="conta"):
        contrato.gravar(
            "elo-promocoes", {"apelido": "X"}, PERIODO, resumo={}, itens=[],
            fonte="api", pasta=tmp_path,
        )


def test_gravar_e_carregar_fecham_o_ciclo(tmp_path):
    contrato.gravar(
        "elo-promocoes", CONTA, PERIODO,
        resumo={"promocoes_na_janela": 4}, itens=[{"nome": "SETEMBRO"}],
        pasta=tmp_path,
    )
    lido = contrato.carregar("elo-promocoes", pasta=tmp_path)
    assert lido["resumo"]["promocoes_na_janela"] == 4
    assert lido["contrato"] == contrato.CONTRATO
    assert contrato.carregar("elo-inexistente", pasta=tmp_path) is None


def test_gerado_em_tem_fuso(tmp_path):
    dado = contrato.gravar("elo-caixa", CONTA, PERIODO, {}, [], pasta=tmp_path)
    assert dado["gerado_em"][-5] in "+-"


def test_carregar_todos_ignora_versao_desconhecida(tmp_path):
    contrato.gravar("elo-caixa", CONTA, PERIODO, {}, [], pasta=tmp_path)
    (tmp_path / "elo-doutro-mundo.json").write_text(
        json.dumps({"contrato": "99", "skill": "elo-doutro-mundo"}), encoding="utf-8"
    )
    achados = contrato.carregar_todos(tmp_path)
    assert [d["skill"] for d in achados] == ["elo-caixa"]


def test_skill_local_nao_precisa_de_conta(tmp_path):
    """Skill que nao le a conta (conteudo de produto) nao tem conta pra nomear."""
    dado = contrato.gravar(
        "elo-criativos", None, None, resumo={"produtos": 1},
        itens=[{"titulo": "Serra circular"}], fonte="local", pasta=tmp_path,
    )
    assert dado["fonte"] == "local"
    assert dado["conta"]["id"] is None


def test_fonte_api_continua_exigindo_conta(tmp_path):
    with pytest.raises(contrato.ContratoInvalido, match="conta"):
        contrato.gravar(
            "elo-promocoes", {"apelido": "X"}, PERIODO, resumo={}, itens=[],
            fonte="api", pasta=tmp_path,
        )


# ----------------------------------------------------------------- criativos

def test_criativos_recusa_produto_sem_nome():
    with pytest.raises(ValueError, match="produto"):
        criativos.preparar([{"titulo": "Serra circular"}])


def test_criativos_recusa_lista_vazia():
    with pytest.raises(ValueError, match="vazia"):
        criativos.preparar([])


def test_criativos_nao_inventa_campo_ausente():
    itens, avisos = criativos.preparar([{"produto": "Serra circular"}])
    assert itens[0]["titulo"] is None
    assert itens[0]["beneficios"] == []
    assert any("sem titulo" in a or "sem título" in a for a in avisos)


def test_criativos_preserva_o_que_foi_escrito():
    itens, _ = criativos.preparar([{
        "produto": "Assador 70kg",
        "titulo": "Assador Giratório Industrial 70kg Inox 127/220v",
        "beneficios": ["Assa 12 frangos de uma vez"],
        "objecoes": [{"duvida": "Cabe na cozinha?", "resposta": "Ocupa 90x60cm"}],
        "specs": {"capacidade": "70 kg"},
    }])
    i = itens[0]
    assert i["titulo"].startswith("Assador Giratório")
    assert i["objecoes"][0]["duvida"] == "Cabe na cozinha?"
    assert i["specs"]["capacidade"] == "70 kg"


# -------------------------------------------------------------------- painel

def test_painel_mostra_lacuna_quando_campo_esta_em_faltando(tmp_path):
    dado = contrato.montar(
        "elo-margem", CONTA, PERIODO, resumo={}, itens=[],
        faltando=["custo"],
        lacunas={"custo": "o custo deste SKU nao veio na sua planilha"},
    )
    html = painel.render([dado])
    assert "não veio da API" in html
    assert "nao veio na sua planilha" in html


def test_painel_marca_demonstracao_de_forma_visivel(tmp_path):
    dado = contrato.montar("elo-promocoes", CONTA, PERIODO, {}, [], fonte="demo")
    html = painel.render([dado])
    assert "dados de demonstração" in html
    assert "em-demo" in html


def test_painel_nao_marca_demonstracao_quando_fonte_e_api(tmp_path):
    dado = contrato.montar("elo-promocoes", CONTA, PERIODO, {}, [])
    html = painel.render([dado])
    assert "dados de demonstração" not in html


def test_painel_desenha_so_as_skills_presentes():
    a = contrato.montar("elo-promocoes", CONTA, PERIODO, {"x": 1}, [])
    html = painel.render([a])
    assert "Promoções terminando" in html
    assert "Devoluções" not in html


def test_painel_vazio_explica_em_vez_de_quebrar():
    html = painel.render([])
    assert "Nenhuma skill rodou ainda" in html


def test_painel_mostra_null_como_nao_veio_nao_como_zero():
    dado = contrato.montar(
        "elo-margem", CONTA, PERIODO, {},
        [{"mlb": "MLB1", "preco": 149.90, "custo": None, "margem": None}],
    )
    html = painel.render([dado])
    assert "não veio" in html
    assert ">0<" not in html


def test_painel_escapa_conteudo_da_api():
    dado = contrato.montar(
        "elo-promocoes", {"id": 1, "apelido": "<script>alert(1)</script>", "site": "MLB"},
        PERIODO, {}, [{"nome": "<img onerror=x>"}],
    )
    html = painel.render([dado])
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_idade_do_dado_aparece():
    antigo = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(time.time() - 7200))
    dado = contrato.montar("elo-caixa", CONTA, PERIODO, {}, [])
    dado["gerado_em"] = antigo
    assert "há 2 h" in painel.render([dado])


# ---------------------------------------------------------------- atualizacao

def _base_falsa(tmp_path, auto=None, com_settings=True, registrado=True):
    base = tmp_path / ".claude"
    (base / "plugins").mkdir(parents=True)
    cfg = {"extraKnownMarketplaces": {}}
    if registrado and com_settings:
        entrada = {"source": {"source": "github", "repo": "sebemlabs-agents/elo-kit"}}
        if auto is not None:
            entrada["autoUpdate"] = auto
        cfg["extraKnownMarketplaces"]["elo-kit"] = entrada
    cfg["outraCoisa"] = {"preservar": True}
    (base / "settings.json").write_text(json.dumps(cfg), encoding="utf-8")
    conhecidos = {}
    if registrado:
        conhecidos["elo-kit"] = {"source": {}, "installLocation": "/x"}
        if auto is not None:
            conhecidos["elo-kit"]["autoUpdate"] = auto
    (base / "plugins" / "known_marketplaces.json").write_text(
        json.dumps(conhecidos), encoding="utf-8")
    return base


def test_atualizacao_desligada_por_padrao(tmp_path):
    assert atualizacao.estado(_base_falsa(tmp_path)) == "desligada"


def test_atualizacao_le_ligada(tmp_path):
    assert atualizacao.estado(_base_falsa(tmp_path, auto=True)) == "ligada"


def test_atualizacao_le_desligada_explicita(tmp_path):
    assert atualizacao.estado(_base_falsa(tmp_path, auto=False)) == "desligada"


def test_atualizacao_sem_catalogo_diz_nao_instalado(tmp_path):
    assert atualizacao.estado(_base_falsa(tmp_path, registrado=False)) == "nao instalado"


def test_ligar_muda_os_dois_arquivos(tmp_path):
    base = _base_falsa(tmp_path)
    mudou = atualizacao.ligar(base)
    assert set(mudou) == {"settings.json", "known_marketplaces.json"}
    assert atualizacao.estado(base) == "ligada"


def test_ligar_preserva_o_resto_das_configuracoes(tmp_path):
    base = _base_falsa(tmp_path)
    atualizacao.ligar(base)
    cfg = json.loads((base / "settings.json").read_text(encoding="utf-8"))
    assert cfg["outraCoisa"] == {"preservar": True}
    assert cfg["extraKnownMarketplaces"]["elo-kit"]["source"]["repo"] == \
        "sebemlabs-agents/elo-kit"


def test_ligar_faz_copia_de_seguranca(tmp_path):
    base = _base_falsa(tmp_path)
    atualizacao.ligar(base)
    assert (base / "settings.json.bak-elo").exists()


def test_ligar_duas_vezes_nao_reescreve(tmp_path):
    base = _base_falsa(tmp_path)
    atualizacao.ligar(base)
    assert atualizacao.ligar(base) == []


def test_ligar_recusa_quando_nao_instalado(tmp_path):
    with pytest.raises(atualizacao.SemClaude):
        atualizacao.ligar(_base_falsa(tmp_path, registrado=False))


def test_estado_aceita_known_marketplaces_aninhado(tmp_path):
    base = _base_falsa(tmp_path, com_settings=False)
    k = base / "plugins" / "known_marketplaces.json"
    k.write_text(json.dumps({"marketplaces": {"elo-kit": {"autoUpdate": True}}}),
                 encoding="utf-8")
    assert atualizacao.estado(base) == "ligada"


# ---------------------------------------------------- URL de retorno propria

def test_apelido_tira_acento_e_simbolo():
    assert pasta_mod.apelido("Açaí do João & Cia") == "acai-do-joao-cia"


def test_apelido_nao_deixa_hifen_duplo_nem_nas_pontas():
    a = pasta_mod.apelido("  --Loja   Sebem!!  ")
    assert a == "loja-sebem"


def test_apelido_recusa_nome_sem_letra_nem_numero():
    with pytest.raises(ValueError):
        pasta_mod.apelido(" --- ")


def test_apelido_limita_o_tamanho():
    assert len(pasta_mod.apelido("x" * 120)) <= 40


def test_uri_sem_nome_usa_a_padrao():
    assert pasta_mod.uri_de(None) == pasta_mod.URI_PADRAO


def test_uri_com_nome_e_https_e_invalid():
    u = pasta_mod.uri_de("Loja Sebem")
    assert u == "https://loja-sebem.invalid/callback"
    assert u.startswith("https://") and ".invalid/" in u


def test_preparar_grava_a_uri_da_pessoa(tmp_path):
    r = pasta_mod.preparar(tmp_path, nome="Loja Sebem")
    texto = (tmp_path / "credenciais.txt").read_text(encoding="utf-8")
    assert "MELI_REDIRECT_URI=https://loja-sebem.invalid/callback" in texto
    assert r["uri"] == "https://loja-sebem.invalid/callback"


def test_preparar_sem_nome_mantem_a_padrao(tmp_path):
    pasta_mod.preparar(tmp_path)
    texto = (tmp_path / "credenciais.txt").read_text(encoding="utf-8")
    assert "MELI_REDIRECT_URI=%s" % pasta_mod.URI_PADRAO in texto


def test_preparar_nunca_sobrescreve_credenciais_ja_preenchidas(tmp_path):
    (tmp_path / "credenciais.txt").write_text("MELI_APP_ID=123\n", encoding="utf-8")
    pasta_mod.preparar(tmp_path, nome="Outra Loja")
    assert (tmp_path / "credenciais.txt").read_text(encoding="utf-8") == "MELI_APP_ID=123\n"
