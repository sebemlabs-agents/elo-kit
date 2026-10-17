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
import painel  # noqa: E402
import pasta as pasta_mod  # noqa: E402


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


def test_conta_sem_id_e_recusada(tmp_path):
    with pytest.raises(contrato.ContratoInvalido, match="conta"):
        contrato.gravar(
            "elo-promocoes", {"apelido": "X"}, PERIODO, resumo={}, itens=[],
            pasta=tmp_path,
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
