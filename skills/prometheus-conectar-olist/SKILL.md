---
name: prometheus-conectar-olist
description: Conecta o ERP Olist (Tiny) em somente leitura e importa o CUSTO dos produtos para a pasta do usuário — o dado que nenhum marketplace entrega e sem o qual a margem não fecha. Use quando o usuário pedir para conectar a Olist ou o Tiny, quando ele disser que usa o ERP, ou quando uma skill precisar de custo e não houver planilha. Use também quando ele relatar erro, conexão vencida ou dúvida da Olist — "a Olist pediu para reconectar", "deu 401", "estourou o limite", "invalid_grant". Não use para Mercado Livre nem Shopee: cada um tem a sua skill.
---

# Conectar a Olist — o custo que falta na margem

Esta skill existe por um motivo específico: **a API de marketplace nenhum entrega o custo
do produto.** É por isso que o pacote pede uma planilha de custo. Quem tem o ERP não
precisa dela — o custo vem da fonte, com histórico.

## O desenho é diferente das outras duas conexões, e o motivo importa

Na Olist o acesso vale **4 horas** e a renovação vale **1 DIA**.

| | Renovação vence em |
|---|---|
| Mercado Livre | 6 meses |
| Shopee | 30 dias |
| **Olist** | **1 dia** |

Com um dia, uma conexão viva estaria vencida em quase toda segunda visita. E **custo de
produto não muda todo dia.**

Por isso aqui a gente **importa**: conecta, puxa o custo para a pasta, e o painel usa o
arquivo. A margem continua funcionando dias depois, com a conexão já vencida.

**Diga isso a ela antes de conectar.** Quando a Olist pedir para reconectar, ela precisa
saber que é o prazo da Olist, não defeito do pacote nem erro dela.

## Dois pré-requisitos que podem barrar

- Plano **Construa ou superior**. Abaixo disso não existe API v3 na conta.
- Extensão **Gestão de Aplicativos** instalada.

Se ela não tiver, não insista: siga com a planilha de custo, que resolve o mesmo problema.

---

## 1. O aplicativo no ERP

No ERP dela: **menu > configurações > aba geral > Aplicativos > + novo aplicativo**.

- **Nome:** o que ela reconheça depois.
- **URLs de Redirecionamento:** o mesmo endereço que ela usou nos outros canais — domínio
  dela ou o do projeto Supabase.
- **Permissões:** marque os módulos e escolha **Leitura**. Nunca "incluir e editar", nunca
  "excluir" — o pacote não escreve.

> **As chaves não aparecem ao salvar.** Ela precisa **entrar de novo no aplicativo e
> editar** para ver Client ID e Client Secret, na seção *Chaves de acesso*. É o mesmo
> tropeço do Mercado Livre — avise antes.

**Máximo 5 aplicativos por conta.** Se ela já integra outras plataformas, pode estar no
limite.

## 2. Preencher as credenciais (ela faz, fora do chat)

Em `credenciais.txt`, as três linhas:

```
OLIST_CLIENT_ID=
OLIST_CLIENT_SECRET=
OLIST_REDIRECT_URI=
```

## 3. Conectar e importar

```
python3 autorizar_olist.py
```

Abre `ABRIR_OLIST.txt`, ela cola no navegador **logado no ERP**, autoriza, copia a barra
inteira para `RETORNO_OLIST.txt`. Então:

```
python3 autorizar_olist.py --arquivo RETORNO_OLIST.txt
```

## 4. Puxar o custo — dos produtos que interessam, não de todos

**O limite é de 30 chamadas por minuto, por CONTA e não por aplicativo.** Mil produtos
levariam mais de meia hora e ainda atrapalhariam as outras integrações dela.

Então puxe o custo **dos produtos que estão sendo analisados** — os que apareceram na fila
de promoções, os que ela perguntou. Não varra o catálogo.

O custo importado vira `prometheus-custos.json` na pasta, com `capturado_em` — que é a
idade do dado. **Sempre diga essa idade quando usar o custo numa conta de margem.** Custo
de três semanas atrás apresentado como de hoje é decisão errada com cara de certa.

---

## Erros reais e o que fazer

| Sintoma | Causa | O que fazer |
|---|---|---|
| "Precisa reconectar" | o refresh de 1 dia venceu | **é o esperado.** O custo já importado continua na pasta; reconecte só para trazer custo novo |
| `401` | **não é chave errada** | é o usuário logado sem permissão no módulo. Confira o perfil do usuário, não a credencial |
| `429` ou travou | passou de 30 chamadas por minuto | o limite é da conta inteira. Espere e puxe menos produtos |
| Não acha as chaves depois de salvar | elas não aparecem ao salvar | entre de novo no aplicativo e clique em editar |
| Parou de funcionar depois de mexer nas permissões | a Olist invalida a chave | é documentado: ao mudar permissão, gere chave nova e atualize o `credenciais.txt` |

## Regras que valem o tempo todo

- **Somente leitura.** O `olist.py` levanta `PermissionError` para qualquer método que não
  seja `GET`. Alterar produto ou pedido se faz no próprio ERP, por ela.
- **Segredo nunca passa pelo chat.** Não leia `credenciais.txt`, `tokens-olist.json`,
  `ABRIR_OLIST.txt` nem `RETORNO_OLIST.txt`.
- **Custo tem idade.** Use o `capturado_em` do arquivo, sempre.
- **Dado ausente não é zero.** Produto sem custo cadastrado no ERP fica sem margem, com a
  linha em branco — nunca com zero.
