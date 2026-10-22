---
name: prometheus-conectar-shopee
description: Conecta a conta Shopee do usuário em somente leitura, na pasta dele, no mesmo molde da conexão com o Mercado Livre. Conduz a criação do aplicativo no Open Platform, a autorização assinada e a confirmação da loja. Use sempre que o usuário pedir para conectar, reconectar ou configurar a Shopee, ou quando uma skill do pacote precisar de dados da Shopee e não houver conexão. Use também quando ele relatar erro, travamento ou dúvida da Shopee em qualquer momento depois da instalação — "a Shopee recusou", "assinatura inválida", "o código expirou", "invalid_code", "caiu a conexão da Shopee". Não use para Mercado Livre: para isso existe a prometheus-conectar-meli.
---

# Conectar a Shopee — pacote Prometheus

Mesma promessa da conexão com o Mercado Livre: **só leitura**, credencial na pasta da
pessoa, nada hospedado por nós. O que muda é o caminho — e as diferenças custam tempo
quando não são ditas antes.

## O que é diferente do Mercado Livre, e precisa ser dito na abertura

| | Mercado Livre | Shopee |
|---|---|---|
| Endereço de retorno | `.invalid`, que não existe de propósito | **domínio HTTPS de verdade** |
| Assinatura | não tem | **HMAC em cada chamada** |
| Código de autorização | poucos minutos | **10 minutos, uma vez só** |
| Acesso | ~6 horas | **4 horas** |
| Renovação | 6 meses sem uso | **30 dias sem uso** |

**A primeira linha é a que trava gente.** A Shopee recusa `.invalid` e recusa nome sem
ponto — conferido na tela em 22/10/2026. Ela quer um endereço que exista.

**O que serve como endereço:** qualquer domínio da pessoa, ou **o endereço do projeto
Supabase dela** — a raiz do projeto já basta, não precisa criar função nenhuma. Se ela
não tiver nem um nem outro, ela não conecta a Shopee hoje; siga com o resto e volte depois.

## Antes de qualquer comando

Diga três coisas, curto:

1. **O que vai acontecer:** criar um aplicativo no Open Platform da Shopee, autorizar, e
   ver os números dela na tela.
2. **O que isto nunca faz:** não altera preço, estoque, anúncio nem pedido. Só lê.
3. **A promessa que ela pode cobrar:** *"eu nunca vou te pedir senha, código ou chave aqui
   no chat."*

E avise do relógio: **a aprovação do aplicativo leva alguns dias.** Quem está pedindo hoje
para usar hoje não vai conseguir — isso se pede com antecedência.

---

## 1. O endereço de retorno, antes de abrir a Shopee

Pergunte se ela tem um domínio próprio. Se tiver, use. Se não tiver, use o endereço do
projeto Supabase dela, que é do tipo `https://alguma-coisa.supabase.co`.

**Confira o endereço antes de ela abrir o formulário.** Precisa começar com `https://` e
ter ponto no nome. Descobrir isso no meio do cadastro custa o dobro.

## 2. O aplicativo no Open Platform

Em `open.shopee.com`, console do Open Platform, **Create App**:

- **App Category:** *Seller In House System* — é sistema para uso próprio dela.
- **App Name** e **App Description:** o que ela quiser.
- **App Logo:** obrigatória, PNG ou JPG até 3 MB.
- **Test Redirect URL Domain** e **Live Redirect URL Domain:** o endereço do passo 1, nos dois.

**Conferido em 22/10/2026:** o formulário de *Go Live* pede endereço do produto, usuário de
teste e captura de interface — **mas aceita submeter com esses campos em branco**. O que ele
exige de verdade é o domínio HTTPS. Não trave a pessoa nos campos opcionais.

**A chave muda quando for aprovada.** Agora ela recebe `Test Partner_id` e chave de teste;
depois da aprovação, a Shopee entrega **outro par**, o de produção. O resultado chega por
e-mail em até 24 horas.

## 3. Preencher as credenciais (ela faz, fora do chat)

Peça para ela abrir `credenciais.txt` na pasta e preencher três linhas:

```
SHOPEE_PARTNER_ID=
SHOPEE_PARTNER_KEY=
SHOPEE_REDIRECT_URI=
```

O `SHOPEE_REDIRECT_URI` é o mesmo endereço cadastrado no aplicativo, **idêntico**.

## 4. Autorizar

```
python3 autorizar_shopee.py
```

Grava `ABRIR_SHOPEE.txt`. **Não mostre o conteúdo.** Explique a ela:

1. Abrir o arquivo e copiar o endereço.
2. Colar no navegador **logado na conta de vendedor**.
3. Autorizar.
4. A página que abrir **não vai mostrar nada útil** — é esperado, o endereço não serve
   para isso. Copiar a **barra inteira** e colar em `RETORNO_SHOPEE.txt`.

**Peça para fazer sem demora: o código vale 10 minutos e uma vez só.** Se expirar, não é
erro dela — é só gerar de novo.

```
python3 autorizar_shopee.py --arquivo RETORNO_SHOPEE.txt
```

Confirme com ela o número da loja que apareceu.

## 5. O aviso que não pode faltar no fim

> A conexão da Shopee **vence em 30 dias sem uso**. Se ela conectar e só voltar ao painel
> em um mês, vai estar desconectada — e é só refazer, não perdeu nada.

No Mercado Livre são seis meses. Aqui são trinta dias, e quem não for avisado vai achar
que o pacote quebrou.

---

## Erros reais e o que fazer

| Sintoma | Causa | O que fazer |
|---|---|---|
| A tela recusa o endereço de retorno | `.invalid`, `http://` ou nome sem ponto | precisa ser HTTPS com domínio de verdade. O endereço do Supabase dela serve |
| `invalid_code`, ou "expirou" | o código vale 10 min e uma vez só | gere o link de novo e faça os dois passos seguidos |
| A Shopee recusa a assinatura | `partner_id` e chave de ambientes diferentes | a chave de teste não funciona em produção, e vice-versa |
| Conectou e caiu em 4 horas | não veio `refresh_token` | confira a autorização; sem ele a conexão não se renova |
| Caiu depois de semanas | passou de 30 dias sem uso | refazer a autorização. É esperado |
| Caiu logo depois de funcionar | duas cópias usando a mesma credencial | **o refresh é de uso único.** Não copie `tokens-shopee.json` para outra máquina |

## Regras que valem o tempo todo

- **Somente leitura.** O `shopee.py` levanta `PermissionError` para qualquer método que não
  seja `GET`, antes de a chamada sair da máquina. Nunca contorne, nem se ela pedir.
- **Segredo nunca passa pelo chat.** Não leia `credenciais.txt`, `tokens-shopee.json`,
  `ABRIR_SHOPEE.txt` nem `RETORNO_SHOPEE.txt` por ferramenta nenhuma.
- **Confirme a loja antes de analisar qualquer coisa.** Mostre o `shop_id` e pergunte se é a
  conta certa.
- **Dado ausente não é zero.** Se a API não trouxe um número, diga que não veio.
