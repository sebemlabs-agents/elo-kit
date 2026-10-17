# elo-kit

Pacote de skills que conecta a sua conta do Mercado Livre **em somente leitura** e transforma
os dados em decisão: promoções terminando, dinheiro a receber, conteúdo de produto e mais.

Funciona no **Claude** e no **Codex**, instalado com um comando.

## O que este pacote nunca faz

- Não altera preço, estoque, anúncio nem pedido.
- Não adere a promoção, não responde pergunta, não envia mensagem.
- Não guarda a sua credencial em servidor nenhum: ela fica na sua máquina, numa pasta sua.
- Não pede e não aceita segredo pelo chat.

A garantia não é promessa: o cliente HTTP do pacote recusa qualquer chamada que não seja
leitura **antes de ela sair do seu computador**.

## Instalar

No Claude Code:

```
/plugin marketplace add <owner>/elo-kit
```

No Codex:

```
codex plugin marketplace add <owner>/elo-kit
```

Depois peça ao assistente: **"conecta minha conta do Mercado Livre"**. A skill
`elo-conectar-meli` conduz o resto — criação do aplicativo, autorização e primeiro painel —
em cerca de 10 minutos.

## O que vem dentro

| Skill | O que entrega |
|---|---|
| `elo-conectar-meli` | acesso só-leitura à sua conta, na sua pasta |
| `elo-painel` | o painel local com os blocos das skills que você rodou |

Mais skills entram pelo mesmo caminho: cada uma grava um arquivo no formato do
[CONTRATO.md](./CONTRATO.md) e aparece como um bloco no painel.

## Requisitos

- Python 3.8 ou mais novo (no Mac normalmente já vem).
- Conta **administradora** de vendedor no Mercado Livre — operador e colaborador não
  conseguem autorizar.
- Uma pasta sua, **fora** de Dropbox, iCloud, Google Drive e OneDrive. O pacote verifica isso
  e para se a pasta sincronizar.

Nenhuma dependência é instalada: os scripts são Python puro.

## Para desenvolver

```
python3 -m pytest tests -q
```

## Licença

MIT. Ver [LICENSE](./LICENSE).
