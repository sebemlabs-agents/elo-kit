---
name: elo-margem
description: Calcula a margem de contribuição por anúncio — quanto sobra depois da comissão do marketplace, do frete, do custo e do imposto. Cruza a planilha de custo do usuário com os preços dos anúncios. Use quando ele falar em margem, lucro, "quanto eu ganho nesse produto", "vale a pena vender", "estou no prejuízo", rentabilidade, ou quando outra skill esbarrar na falta do custo por SKU. Precisa da planilha de custo; o resto pode vir da conta conectada.
---

# Margem por anúncio — pacote Elo

Quanto sobra em cada anúncio depois de tudo:

```
preço − comissão − frete − custo − imposto = margem de contribuição
```

Foi a **dor número um declarada** nas mentorias. Cinco mentorados diferentes, e um deles
resumiu assim: não ter visibilidade da margem por venda era o problema maior que ele tinha.

## Antes de rodar — os scripts da pasta

Se `margem.py` não estiver na pasta dele, copie todos os `.py` de
`${CLAUDE_PLUGIN_ROOT}/scripts/` para lá, **sem sobrescrever `credenciais.txt` nem
`tokens.json`**.

## Esta skill começa pela planilha, sempre

**Nenhuma API do mundo tem o custo do produto dele.** Nem o Mercado Livre, nem o Mercado
Pago, nem o ERP de outra pessoa. O custo mora na planilha dele, e é por isso que esta skill
não existe sem arquivo.

Se ele não tiver a planilha pronta, não tente contornar. Peça o mínimo: **SKU, custo e
imposto**. Poucas linhas já valem — dez produtos com margem real ensinam mais que trezentos
sem custo.

## O caminho

**1. Leia a planilha** com a skill `elo-planilha`, que descreve as colunas e os tipos. Não
pule: mapear coluna pelo nome que você imagina é como se produz número errado com cara de
certo.

**2. Confirme o mapeamento com ele.** "Entendi que `Vlr. Custo` é o custo unitário e
`Imposto %` é a alíquota, confere?" Quando a coluna for ambígua, pergunte.

**3. Complete com o que a conta tem.** Se ele estiver conectado, o preço de cada anúncio vem
da API — `python3 meli.py get /items/MLB...`. Se não estiver, o preço também sai da planilha.

**4. Monte as linhas e calcule:**

```
python3 margem.py linhas.json --capturado-em <data do arquivo>
```

Cada linha aceita `mlb`/`sku`/`produto`, `preco`, `custo`, `taxa` ou `taxa_pct`, `frete`,
`imposto` ou `imposto_pct`.

## A regra que não se negocia

**Componente que não veio não vira zero.** Falta o custo, a linha fica sem margem e o arquivo
diz qual componente faltou.

Zero de custo transforma prejuízo em lucro na tela. É o erro mais caro que este pacote
poderia cometer, porque não parece erro: o número aparece bonito e a pessoa decide com ele.

**Zero declarado é diferente de ausente.** Quem escreve `frete: 0` está dizendo que não paga
frete naquele anúncio, e a conta roda normalmente. Quem deixa vazio não está dizendo nada —
e aí a conta não roda. Explique essa diferença quando o frete faltar; quase sempre a pessoa
tem a informação e só não preencheu.

## Como apresentar

**Comece pelos negativos.** Se existe anúncio com margem negativa, é a primeira coisa que ele
precisa ver — está pagando para vender, e geralmente não sabe. Depois a margem média, depois
a lista.

**A média é ponderada pelo preço**, não pela contagem de anúncios. Média simples faz um
chaveiro de R$ 5 pesar igual a uma geladeira de R$ 3.000, e inverte a leitura.

**Diga quantos ficaram sem conta.** "47 de 300 com margem calculada" não é resultado — é um
aviso de que falta custo em 253 produtos. E isso é informação acionável, não falha.

## O que esta skill não resolve

- **A comissão exata por anúncio** varia com tipo de anúncio, categoria e campanha. Se ele
  informar a taxa, usamos a dele; se informar percentual, calculamos sobre o preço. **Não
  invente a comissão.**
- **Frete** depende do modo de envio e de quem paga. Pergunte; não estime.
- **Imposto** depende do regime dele. Pergunte; não assuma Simples.

Quando ele pedir "a margem certa", a resposta honesta é: *a conta é esta, e a precisão é a
dos números que você me deu.* Melhorar o resultado é melhorar a planilha.

## O gancho natural

Esta é a skill que mais puxa as outras. Quando a `elo-promocoes` mostrar um desconto exigido e
ele perguntar "vale a pena aderir?", a resposta só existe aqui — e só com o custo na mão.

É o argumento para a planilha de custo deixar de ser lição de casa chata e virar a chave de
tudo.
