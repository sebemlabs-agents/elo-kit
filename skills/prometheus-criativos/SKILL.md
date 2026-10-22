---
name: prometheus-criativos
description: Transforma um produto cru em pacote de conteúdo pronto para anúncio — título, descrição, benefícios e objeções respondidas — a partir de um briefing que a skill ajuda a montar e recusa se estiver pobre. Não precisa de conexão com o Mercado Livre nem de chave de API. Use quando o usuário pedir ajuda com título, descrição, texto, conteúdo, copy ou anúncio de um produto, quiser melhorar um anúncio que já existe, ou quando ele travou na conexão e precisa de algo que funcione mesmo assim.
---

# Conteúdo de produto — pacote Elo

Entra produto cru, sai o pacote de conteúdo: **título, descrição, benefícios e objeções
respondidas.**

Esta é a única skill do pacote que **não precisa de nada**: nem conta conectada, nem chave de
API, nem internet além do que você já usa. Quem travou na conexão com o Mercado Livre
constrói aqui do mesmo jeito — e é por isso que ela existe.

## A regra que define a qualidade: briefing primeiro

A maior parte do conteúdo ruim de marketplace nasce de gerar em cima de nada. Então a ordem
aqui é fixa: **primeiro o briefing, depois o conteúdo.** E **briefing pobre é recusado**, não
preenchido com suposição.

É a mesma regra do Van Gogh, o sistema que faz isso na operação Sebem, e ela existe porque
texto genérico não vende — e pior, parece que vende, até você comparar a conversão.

### O que faz um briefing ser suficiente

Mínimo para seguir — se faltar algo daqui, **pergunte em vez de inventar**:

1. **O que é o produto**, em uma frase, do jeito que o cliente chamaria.
2. **Para quem é** — quem compra, e para resolver o quê.
3. **Três specs que importam** na decisão. Medida, potência, capacidade, material, voltagem —
   o que for decisivo na categoria.
4. **O preço**, ou a faixa.

Melhora muito, e vale perguntar:

5. **O que o concorrente faz pior**, ou o que o cliente reclama dos outros.
6. **A dúvida que mais aparece** antes de comprar, ou o motivo mais comum de devolução.
7. **Garantia, prazo, o que acompanha.**

### Se o produto já existe no Mercado Livre

Se o usuário estiver conectado (skill `prometheus-conectar-meli`), você pode puxar o anúncio atual e
usar como base do briefing, em vez de pedir tudo de novo:

```
python3 meli.py get /items/MLB1234567890
```

Isso traz título, preço, specs e fotos. Use como matéria-prima e **pergunte só o que faltar**.
Se ele não estiver conectado, siga pelo briefing manual — o resultado é o mesmo.

## Como escrever cada peça

**Título.** O que a pessoa digitaria na busca, não o que o fabricante chama. Começa pelo tipo
de produto, depois marca e modelo, depois o atributo decisivo da categoria. Sem adjetivo de
propaganda, sem "frete grátis", sem emoji. Se a categoria tem um número que decide a compra
(litros, polegadas, watts, quilos), ele entra.

**Benefícios, não características.** Característica é o que o produto tem; benefício é o que
muda na vida de quem compra. `70 kg de capacidade` é característica. `Assa 12 frangos de uma
vez, dá conta do almoço de domingo sem fazer duas rodadas` é benefício. Escreva o benefício
**e** mantenha a característica ao lado, porque é ela que sustenta a promessa.

**Objeções respondidas.** Liste as três dúvidas que seguram a compra e responda cada uma com
fato, não com adjetivo. Se a objeção for verdadeira — é grande, é pesado, precisa de
instalação —, **responda com a verdade e o contexto**, nunca escondendo. Objeção escondida
vira devolução, e devolução custa entre 20% e 65% do valor do produto.

**Descrição.** Começa resolvendo a dúvida principal, não com história da marca. Depois os
benefícios, depois as specs completas, depois o que acompanha e a garantia. Blocos curtos.
Quem lê descrição de marketplace está decidindo, não passeando.

## O que não fazer

- **Não invente spec.** Se você não sabe a potência, pergunte. Número errado em anúncio vira
  reclamação e devolução.
- **Não prometa prazo, frete ou garantia** que o usuário não informou.
- **Não copie texto de concorrente**, nem peça para o usuário copiar.
- **Não escreva superlativo sem lastro** — "o melhor do mercado" não convence e pode dar
  problema. Troque por comparação verdadeira e verificável.
- **Não publique nada.** Esta skill escreve; publicar é o usuário quem faz, no painel do
  Mercado Livre. O pacote inteiro é somente leitura.

## Gravar no painel

Depois de produzir o pacote, grave no formato do contrato para aparecer no painel:

```
python3 criativos.py pacote.json
```

Onde `pacote.json` é uma lista de produtos, cada um assim:

```json
[
  {
    "produto": "Assador giratório 70 kg",
    "titulo": "Assador Giratório Industrial 70kg Inox 127/220v",
    "descricao": "...",
    "beneficios": ["Assa 12 frangos de uma vez — ...", "..."],
    "objecoes": [
      {"duvida": "Cabe na minha cozinha?", "resposta": "Ocupa 90x60cm de chão ..."}
    ],
    "specs": {"capacidade": "70 kg", "voltagem": "127/220v"}
  }
]
```

O script valida contra o contrato e grava `prometheus-criativos.json` na pasta. Depois,
`python3 painel.py` para ver no painel junto com o resto.

Campo que você não tem: deixe de fora, e informe em `faltando` ao chamar o script com
`--faltando`. **Nunca preencha com suposição** — o painel sabe mostrar lacuna, e lacuna
honesta vale mais que texto inventado.

## Como apresentar ao usuário

Entregue o pacote **pronto para copiar**, peça por peça, com título e descrição em blocos
separados para ele colar no Mercado Livre. Depois diga, em uma linha, **o que você assumiu** e
**o que ficou faltando** — é isso que ele precisa conferir antes de publicar.

E termine lembrando: o texto é rascunho de quem conhece a categoria em geral; **quem conhece o
produto é ele.** Peça para revisar antes de publicar.
