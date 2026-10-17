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

## Começar

### 1. Instalar o pacote

No **Claude Code**:

```bash
claude plugin marketplace add sebemlabs-agents/elo-kit
claude plugin install elo-kit@elo-kit
```

No **Codex**:

```bash
codex plugin marketplace add sebemlabs-agents/elo-kit
codex plugin add elo-kit@elo-kit
```

### 2. Criar a pasta onde tudo vai morar

Uma pasta nova, só para isto, **fora** de Dropbox, iCloud, Google Drive e OneDrive — o pacote
verifica isso e para se a pasta sincronizar, porque a sua credencial não pode ir para a nuvem
sem você saber.

Sugestão: uma pasta chamada `elo-meli` em Documentos. Conecte essa pasta ao Claude.

### 3. Pedir a conexão

Peça ao assistente, nestas palavras ou parecidas:

> **conecta minha conta do Mercado Livre**

A skill `elo-conectar-meli` conduz o resto: cria o aplicativo no DevCenter do Mercado Livre,
faz a autorização sem nenhum segredo passar pelo chat, confirma qual conta conectou e gera o
primeiro painel. Leva cerca de **10 minutos**.

Depois disso, peça o que quiser: *"quais promoções estão acabando?"*, *"quanto o Meli me
deve?"*, *"atualiza o painel"*.

## O que vem dentro

| Skill | O que entrega |
|---|---|
| `elo-conectar-meli` | acesso só-leitura à sua conta, na sua pasta |
| `elo-painel` | o painel local com os blocos das skills que você rodou |

Mais skills entram pelo mesmo caminho: cada uma grava um arquivo no formato do
[CONTRATO.md](./CONTRATO.md) e aparece como um bloco no painel.

## Requisitos

- **Python 3.8 ou mais novo.** No Mac normalmente já vem; confira com `python3 --version`.
- **Conta administradora** de vendedor no Mercado Livre. Conta de operador ou colaborador não
  consegue autorizar — o Mercado Livre recusa.
- Uma pasta sua, fora de serviço de sincronização.

Nenhuma dependência é instalada: os scripts são Python puro.

## Guias em PDF

- **[Guia do participante](./docs/playbook-participante.html)** — para quem vai conectar
  sozinho, de forma assíncrona: pré-requisitos, os três passos, o que fazer quando trava e
  como desligar depois.
- **[Playbook de condução](./docs/playbook-conexao.html)** — para quem acompanha alguém
  conectando pela primeira vez: onde observar, onde ficar calado, o que cronometrar e a ficha
  de observação.

Os dois geram PDF com `Google Chrome --headless --print-to-pdf`.

## Se algo der errado

A skill traz a tabela de problemas com os erros reais e o que fazer em cada um —
`skills/elo-conectar-meli/references/problemas.md`. Os três mais comuns:

- **A URL de retorno precisa ser idêntica** à cadastrada no DevCenter, caractere por caractere.
- **Conta de operador não autoriza.** Use a conta administradora da loja.
- **`api.mercadolibre.com` precisa estar liberado** nos domínios permitidos do Claude. Em
  conta de empresa, quem libera é o administrador.

## Para desenvolver

```
python3 -m pytest tests -q
```

## Licença

MIT — Marciano Chula / Elo. Ver [LICENSE](./LICENSE).
