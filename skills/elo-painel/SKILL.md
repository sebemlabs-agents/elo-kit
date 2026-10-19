---
name: elo-painel
description: Gera e atualiza o painel.html local a partir dos dados que as skills do pacote Elo gravaram na pasta do usuário — vendas, promoções, dinheiro a receber, devoluções e o que mais estiver presente. Use quando o usuário pedir para ver, abrir, atualizar ou regerar o painel, o dashboard ou "a tela" do pacote, ou depois de rodar qualquer skill elo-*.
---

# Painel do pacote Elo

Monta `painel.html` na pasta do usuário a partir dos arquivos `elo-*.json` que as skills
gravaram. **Este painel nunca chama a API** — a skill coleta e grava, o painel lê e formata.

## Como usar

```
python3 painel.py
```

Sem argumento, usa a pasta onde o script está. Para outra pasta: `python3 painel.py /caminho`.

Depois abra `painel.html` no navegador. No Mac, `open painel.html`; no Windows,
`start painel.html`.

## O que o painel garante

Estas quatro coisas são contrato, não estilo — se alguma deixar de valer, é bug:

1. **Skill ausente não é erro.** O bloco simplesmente não aparece. É isso que permite entregar
   quatro skills agora e mais quatro depois sem mexer no painel.
2. **Dado de demonstração aparece marcado**, de forma visível e permanente — bloco com borda e
   selo próprios. Nunca apresente número de demonstração como se fosse da conta do usuário.
3. **Lacuna é impressa com explicação.** Campo que a API não trouxe aparece como "não veio",
   com o motivo em português, em vez de virar zero.
4. **A idade do dado aparece.** Dado de ontem lido como de hoje é decisão errada.

## Ao apresentar o resultado

Leia o painel e resuma em português, nesta ordem: primeiro o que exige ação hoje, depois o
resto. Para cada número, diga de onde veio. Se houver lacuna, diga o que não foi possível
calcular e o que falta para calcular — não preencha com estimativa.

Se o painel estiver em dados de demonstração, **diga isso na primeira linha.**

## Quando não há nada

Painel vazio não é falha: significa que a conexão existe mas nenhuma skill rodou. Ofereça
rodar a primeira — normalmente a de promoções, que é a que devolve decisão mais rápido.

## Se faltar script na pasta

O pacote cresce, e a pasta do usuário não se atualiza sozinha. Se alguma skill reclamar que
o arquivo `.py` não existe, copie todos os scripts de `${CLAUDE_PLUGIN_ROOT}/scripts/` para a
pasta dele e rode de novo.

**Sem tocar em `credenciais.txt` e `tokens.json`.** Esses são dele, não do pacote.
