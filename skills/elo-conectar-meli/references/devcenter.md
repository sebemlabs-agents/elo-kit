# Criar (ou reaproveitar) a aplicação no DevCenter do Mercado Livre

Leia este arquivo quando o usuário ainda não tem App ID e Client Secret, ou quando já tem uma
aplicação e precisa reaproveitá-la. **Ele faz os cliques, você explica.** Nunca peça para ele
colar App ID ou Client Secret no chat: esses valores vão direto no `credenciais.txt`, que ele
mesmo preenche.

Fonte: documentação oficial do Mercado Livre — "Autenticação e Autorização" e "Permissões
funcionais" (developers.mercadolivre.com.br).

---

## Antes de começar

- Use a **conta dona da operação** — a conta administradora que vende. A aplicação fica presa
  à conta que a criou, e o Mercado Livre recomenda que seja a do titular.
- Conta de **operador ou colaborador não consegue autorizar**: devolve
  `invalid_operator_user_id`. Se o usuário não sabe qual tem, pergunte quem acessa o
  financeiro da loja — normalmente é a administradora.
- Se os dados do titular estiverem **pendentes de validação** no Mercado Livre, a criação pode
  não concluir. Nesse caso vá para o modo demonstração e ele resolve depois.

---

## Passo a passo

1. Acesse `https://developers.mercadolivre.com.br/devcenter` e faça login.
2. Clique em **Criar aplicação** e preencha:
   - **Nome** e **nome curto**: algo que ele reconheça depois, por exemplo
     `painel da minha loja`.
   - **Descrição**: por exemplo `leitura de pedidos e promoções para análise interna`.
   - **Logo**: qualquer imagem.
3. **URL de redirecionamento** — cadastre exatamente isto:

   ```
   https://radar-meli.invalid/callback
   ```

   Precisa ser `https`. O domínio `.invalid` é reservado e nunca abre — **é de propósito**:
   depois de autorizar, o navegador mostra erro e o código de autorização fica só na barra de
   endereço do próprio usuário, sem passar por servidor de ninguém.

   Se o DevCenter recusar esse endereço, use outro `https` qualquer que ele controle e ajuste
   a linha `MELI_REDIRECT_URI` do `credenciais.txt` para ficar **idêntica, caractere por
   caractere**.

4. **PKCE**: ligado. Os scripts usam PKCE com S256.
5. **Escopos**: comece com **somente leitura**, mais **acesso offline** se a tela oferecer —
   é o acesso offline que permite a rotina diária funcionar sem pedir login de novo.

   Se depois da autorização o `autorizar.py` avisar que **não veio renovação automática**,
   volte aqui e habilite leitura e escrita: em algumas contas o acesso offline só é liberado
   junto. **Mesmo assim nada é alterado** — o `meli.py` recusa qualquer chamada que não seja
   leitura antes de sair do computador. É essa a garantia, não o escopo.

6. **Permissões funcionais** — marque as quatro:
   - Usuários (normalmente já vem ligada)
   - Publicação e sincronização — a lista de anúncios
   - Vendas e envios — os pedidos
   - Promoções, cupons e descontos

   Faltar uma delas produz `HTTP 403 PA_UNAUTHORIZED_RESULT_FROM_POLICIES`, que **não diz qual
   faltou**. Por isso as quatro vão marcadas desde o começo.

7. **Tópicos e notificações**: não precisa marcar nada. Se o formulário exigir uma URL de
   notificações, pode usar o mesmo endereço `.invalid`.
8. Salve. Na lista de aplicações, abra a sua e localize o **ID do aplicativo (client id)** e a
   **chave secreta (client secret)**.
9. O usuário copia esses dois valores para o `credenciais.txt`. **Não para o chat.**

---

## Reaproveitar uma aplicação que já existe

Caso comum: o usuário já integra Bling, Olist, Tiny ou outro sistema, e já tem aplicação.

**A regra é adicionar, nunca substituir.**

1. Abra a aplicação existente no DevCenter.
2. Na URL de redirecionamento, **acrescente** `https://radar-meli.invalid/callback` à lista,
   mantendo a que já está lá.
3. Nas permissões funcionais, **marque as que faltam** das quatro acima, sem desmarcar nada.
4. Pegue o App ID e o Client Secret dessa aplicação.

**Se a tela não permitir mais de uma URL de redirecionamento, pare.** Trocar a URL de uma
aplicação que sustenta o ERP dele derruba a integração em produção, no meio de uma conversa.
Nesse caso: ou ele cria uma aplicação nova, ou vai para o modo demonstração e resolve depois,
com calma, fora do horário de operação.

Observação sobre o limite de aplicações por titular: há material afirmando que no Brasil cada
titular cria apenas uma, e há prática indicando que dá para criar várias. **Não afirme nenhuma
das duas.** Peça para ele olhar a lista de aplicações da conta dele — a resposta está na tela.
Se não der para criar outra, o caminho é o de reaproveitamento acima.

---

## Acesso contínuo

A rotina diária precisa de renovação automática. Depois da autorização, o `autorizar.py` diz
se o Mercado Livre devolveu o refresh token. Se avisar que não veio, confira nas configurações
da aplicação se há opção de acesso offline e autorize de novo.

O refresh token do Mercado Livre é de **uso único**: cada renovação devolve um novo, que
substitui o anterior. O `meli.py` já cuida disso — por isso não se deve copiar `tokens.json`
para outra máquina nem rodar a mesma credencial em dois lugares ao mesmo tempo. Dois
consumidores renovando a mesma credencial derrubam um ao outro, e o sintoma aparece horas
depois, parecendo falha de rede.

---

## Erros comuns nesta etapa

| O que aparece | O que é | O que fazer |
|---|---|---|
| "your client callback has to match with the redirect_uri param" | a URL do `credenciais.txt` não é idêntica à cadastrada | compare caractere por caractere, inclusive barra final |
| `invalid_operator_user_id` | autorizou com conta de operador | repita com a conta administradora |
| `403 PA_UNAUTHORIZED_RESULT_FROM_POLICIES` | falta permissão funcional | marque as quatro, salve e autorize de novo |
| "Sorry, the application cannot connect to your account" | URL divergente, conta de colaborador, ou dados do titular pendentes de validação | confira os três, nessa ordem |
| Client Secret renovado no DevCenter | o valor antigo parou de valer | atualize o `credenciais.txt` e autorize de novo |
