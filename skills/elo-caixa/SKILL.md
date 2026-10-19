---
name: elo-caixa
description: Mostra quanto as vendas do Mercado Livre ainda vão liberar e em que dia cada valor cai. Somente leitura. Use quando o usuário perguntar sobre dinheiro a receber, recebimento, quando o Meli paga, liberação, fluxo de caixa, "quanto vai cair essa semana", "quanto o Meli me deve", ou pedir para atualizar o painel. Não é o saldo da carteira do Mercado Pago. Precisa da conta conectada pela skill elo-conectar-meli.
---

# Dinheiro a receber — pacote Elo

Responde uma pergunta só, e responde direito: **do que ele já vendeu, quanto ainda vai cair e
em que dia.**

```
python3 caixa.py
```

Últimos 60 dias de pedidos. Para mudar: `--dias 90`. Depois `python3 painel.py` e
**entregue o link no chat.**

## Antes de rodar — os scripts da pasta

O pacote cresce: skills novas trazem scripts novos, e **a pasta do usuário não se atualiza
sozinha**. Antes do primeiro comando desta skill, confira se o script existe na pasta dele.
Se não existir, copie de `${CLAUDE_PLUGIN_ROOT}/scripts/` para lá — todos os `.py`, de uma vez.

**Nunca sobrescreva `credenciais.txt`, `tokens.json` nem os arquivos da pasta dele.** Só os
scripts do pacote.

É um passo chato e invisível, e é exatamente por isso que ele some: sem os scripts novos, a
skill nova falha dizendo que o arquivo não existe, e parece que a atualização não funcionou.

## A primeira coisa a dizer: isto não é o saldo da carteira

Diga isso antes de mostrar o número, não depois. Quem pergunta "quanto o Meli me deve" muitas
vezes quer o saldo do Mercado Pago — e vai comparar o que você mostrou com o que vê no app.
Se os números não baterem e ele não tiver sido avisado, ele perde a confiança na ferramenta
inteira, não só neste bloco.

**O que esta skill mostra:** o calendário de liberação das vendas. O que entrou, quando cai.

**O que ela não mostra:** saque, estorno, taxa cobrada fora de pedido, disputa e chargeback.
Isso vive no relatório de liquidação do Mercado Pago, que leva minutos para ser gerado e não
cabe numa pergunta de chat. É um degrau acima.

A frase que funciona: *"isto é o que as suas vendas vão liberar. O saldo da carteira é outra
conta, e tem saque e estorno no meio."*

## Como apresentar

Comece pelo **total a receber** e pelo **que cai nos próximos 7 dias** — esses dois números
são a razão de alguém abrir isto de manhã. Depois o calendário, data a data.

Não some tudo numa frase só. "R$ 48 mil a receber" sem o calendário é um número bonito e
inútil; "R$ 3.120 na terça" é o que paga fornecedor.

## As armadilhas que este script já evita

Elas vieram de operação real, cada uma custou uma volta, e vale saber que existem — porque se
o número parecer estranho, a causa provavelmente está aqui:

- **Id de pagamento alfanumérico não é venda.** É fatura do Mercado Livre. Pagamento de venda
  tem id numérico e longo. Um valor alto e esquisito no meio do caixa costuma ser isso.
- **Saque não tem data de liberação.** Vive pela data da transação, numa linha do tempo
  diferente. Nunca entra no calendário.
- **Pagamento sem data de liberação não vira zero nem vira palpite.** Fica fora do total e é
  declarado como lacuna, com o valor que ficou de fora.

O script **conta e relata tudo que descartou**. Se ele disser "3 pagamentos ficaram de fora",
isso é informação, não erro — e é o que permite confiar no resto.

## Quando o número não bate com o painel do Meli

Vai acontecer, e a explicação quase sempre é uma destas três: **a janela** (o padrão lê 60
dias; liberação chega a sair 38 dias depois da venda), **o que foi descartado** (leia os
avisos), ou **a comparação errada** — o painel do Mercado Pago mostra saldo, que inclui saque
e estorno.

Não tente reconciliar no chute. Diga qual das três é, ou diga que não sabe.

## Virar rotina

É a skill mais útil agendada de todas: a pessoa abre o painel de manhã e sabe o que cai na
semana, sem entrar no Mercado Livre. Ofereça agendar quando ela demonstrar que o número fez
sentido.

## Se der erro

`references/problemas.md` da skill de conexão. Aqui o mais comum é **403 por falta da
permissão de vendas e envios** no DevCenter — sem ela não há leitura de pedidos, e sem
pedidos não há calendário.
