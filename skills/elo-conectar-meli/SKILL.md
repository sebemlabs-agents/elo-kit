---
name: elo-conectar-meli
description: Conecta a conta do Mercado Livre do usuário em somente leitura, na pasta dele, e deixa o pacote Elo pronto para usar. Conduz a criação do aplicativo no DevCenter, a autorização OAuth sem expor segredo no chat, a confirmação da conta e o primeiro painel. Use sempre que o usuário pedir para conectar, reconectar, instalar ou configurar o Mercado Livre, o pacote Elo ou qualquer skill elo-*, ou quando outra skill do pacote falhar por falta de conexão — mesmo que ele não diga "conectar".
---

# Conectar o Mercado Livre — pacote Elo

Esta skill tem uma missão só: levar o usuário de "nunca conectei nada" até **os números da
própria loja na tela**, em cerca de 10 minutos, pelo mesmo caminho que todas as outras
pessoas seguem.

O caminho é fixo de propósito. Na edição anterior deste material, cada pessoa escolhia a URL
de retorno e o Mercado Livre respondia com uma mensagem que não diz onde está o erro — e um
bloco de 75 minutos virou atendimento um a um. Aqui a URL vem escrita no pacote e o usuário
copia. **Não invente endereço, não sugira variação, não improvise ordem de passos.**

## Regras que valem o tempo todo

Estas regras existem porque a credencial dá acesso à conta de venda da pessoa:

- **Somente leitura.** O `meli.py` levanta `PermissionError` para qualquer método que não
  seja `GET`, antes de a chamada sair do computador. Nunca tente contornar, nem se o usuário
  pedir para aderir a uma promoção ou mudar um preço. Quando ele pedir, explique que a
  decisão é dele e se faz no painel do Mercado Livre — e, se útil, entregue o texto pronto
  para ele colar lá.
- **Segredo nunca passa pelo chat.** App ID, Client Secret, código de autorização, tokens e a
  URL de retorno ficam só em arquivos da pasta. **Não leia** `credenciais.txt`, `.env`,
  `tokens.json`, `RETORNO.txt`, `ABRIR_NO_NAVEGADOR.txt` nem `.oauth_state` por nenhuma
  ferramenta — nem `cat`, nem leitor de arquivo, nem cópia para o seu contexto. Para saber se
  estão preenchidos, use `python3 meli.py check`, que responde apenas "preenchido" ou
  "VAZIO". Se o usuário colar um segredo no chat mesmo assim, avise que o certo é renovar o
  Client Secret no DevCenter depois.
- **Confirme a conta antes de analisar qualquer coisa.** Depois de conectar, rode
  `python3 meli.py me`, mostre apelido e id, e pergunte se é a conta certa.
- **Dado ausente não é zero.** Se a API não trouxe um número, diga que não veio. Separe o que
  é fato da API, o que é cálculo e o que é desconhecido.
- **A decisão é do vendedor.** Prioridade e percentual sugerido são apoio. Margem depende do
  custo de cada produto, que a API não tem.

## Onde os comandos rodam

Os scripts precisam ficar numa **pasta do computador do usuário conectada ao Claude**, e
rodar num shell que veja essa pasta. Se nenhuma pasta estiver conectada, peça para ele criar
uma pasta nova — sugestão: `elo-meli` — e conectá-la. Use uma pasta só para isto; não misture
com outros arquivos.

Todos os comandos abaixo rodam de dentro dessa pasta.

---

## Instalação — siga em ordem, confirmando cada etapa

### 0. Descobrir como o Python se chama nesta máquina

Antes de qualquer outro comando. **No Windows `python3` quase nunca existe** — costuma ser
`py -3`, e às vezes `python`. Teste nesta ordem e **pare no primeiro que responder 3.8 ou
mais novo**:

```
python3 --version
py -3 --version
python --version
```

Daqui em diante, **use sempre o que funcionou**, em todos os comandos desta skill. Neste
arquivo está escrito `python3`; troque pelo da máquina dele.

Se nenhum responder, ou se vier 3.7 ou anterior, o usuário precisa instalar o Python do site
oficial — no Windows, marcando **"Add python.exe to PATH"** na primeira tela do instalador.
Sem isso, nada do pacote roda.

### 1. Preparar a pasta (e a verificação que mais importa)

Copie para a pasta do usuário todos os arquivos de `scripts/` deste pacote, com os mesmos
nomes. Depois rode:

**Atenção no Windows:** a pasta `Documentos` costuma estar **dentro do OneDrive**, e o passo
abaixo vai recusar — corretamente. Peça uma pasta na raiz do perfil, como
`C:\Users\<nome>\elo-meli`, antes de copiar qualquer coisa.

```
python3 pasta.py
```

Ele faz quatro coisas: **recusa a pasta se ela estiver dentro de Dropbox, iCloud, Google
Drive ou OneDrive**, cria `credenciais.txt` se ainda não existir (nunca sobrescreve), instala
`.gitignore` e fecha a permissão dos arquivos sensíveis.

Se ele parar por sincronização, **pare também**. Não contorne. Peça para o usuário criar uma
pasta fora do serviço de sincronização e comece de novo ali. O token da conta dele não pode
ir para a nuvem sem ele saber.

Em seguida valide que os scripts estão inteiros:

```
python3 -m py_compile *.py
```

### 2. Conferir o acesso à API

```
python3 -c "import http.client as h; c=h.HTTPSConnection('api.mercadolibre.com',timeout=15); c.request('GET','/sites/MLB'); print('ok', c.getresponse().status)"
```

Usa o mesmo caminho de rede que os scripts vão usar, e funciona igual no Mac e no Windows —
`curl` e `grep` não existem no Windows por padrão.

**Qualquer `ok` serve, inclusive `ok 403`.** Sem login o Meli responde 403, e isso prova que
a resposta veio dele: o caminho está aberto. O que reprova é erro de rede, de DNS ou de
certificado — aí o domínio `api.mercadolibre.com` precisa ser liberado nas
configurações do Claude (Configurações → Capabilities → domínios permitidos). **Em conta de
empresa, quem libera é o administrador** — então isso pode não ser resolvível na hora. Se for
o caso, pare, explique, e ofereça o modo demonstração (etapa 7).

### 3. O aplicativo no DevCenter

Pergunte se o usuário já tem aplicação no DevCenter do Mercado Livre.

- **Não tem, ou não sabe:** siga `references/devcenter.md` com ele. Ele faz os cliques, você
  explica.
- **Já tem** (porque integra ERP, por exemplo): vá na seção "Reaproveitar uma aplicação que já
  existe" do mesmo arquivo. A regra é **adicionar** a URL de retorno e as permissões, nunca
  substituir — trocar a URL de um aplicativo em produção derruba a integração do ERP dele.

Os três pontos que mais dão erro: a URL de redirecionamento idêntica à do `credenciais.txt`,
o escopo de leitura, e as quatro permissões funcionais.

### 4. Preencher as credenciais (o usuário faz, fora do chat)

Peça para ele abrir `credenciais.txt` na pasta (TextEdit no Mac, Bloco de Notas no Windows),
colar o **App ID** e o **Client Secret** depois do `=` nas duas linhas indicadas, salvar e
avisar aqui. Então rode:

```
python3 meli.py check
```

Ele responde apenas "preenchido" ou "VAZIO" por campo, sem mostrar valor.

### 5. Conectar a conta

1. `python3 autorizar.py` — grava `ABRIR_NO_NAVEGADOR.txt`. **Não mostre o conteúdo.**
2. Crie um arquivo vazio `RETORNO.txt` na pasta, para o usuário só precisar abrir e colar.
3. Explique a ele: abrir `ABRIR_NO_NAVEGADOR.txt`, copiar o endereço, colar no navegador
   **logado na conta administradora do Mercado Livre**, e autorizar. O navegador vai mostrar
   erro de página — **isso é esperado**, o endereço não existe de propósito e o código fica só
   na barra dele. Copiar a URL inteira da barra, colar em `RETORNO.txt`, salvar, avisar.
   Peça para fazer sem demora: o código vale poucos minutos.
4. `python3 autorizar.py --arquivo RETORNO.txt` — troca o código pelo acesso, esvazia os
   temporários e diz se a renovação automática ficou ligada.
5. `python3 meli.py me` — confirme com ele que o apelido é o da conta dele.

Se a conta for de outro país, o passo 1 aceita o site: `python3 autorizar.py --site MLA`.

Qualquer erro aqui: `references/problemas.md`.

### 6. O primeiro painel

```
python3 painel.py
```

Gera `painel.html` na pasta. Nesta etapa ele vem vazio, explicando que nenhuma skill rodou
ainda — e isso é esperado. Abra com o usuário para ele ver onde os blocos vão aparecer.

A partir daqui, qualquer skill `elo-*` que ele rodar grava um arquivo na pasta e aparece como
um bloco no painel. **Skill ausente não é erro.**

### 7. Quando não dá para conectar

Se o usuário não conseguir criar a aplicação — limite da conta, dados do titular pendentes de
validação, conta de operador, domínio bloqueado pelo administrador, ou aplicativo de produção
que ele não quer mexer — **não insista e não trave a conversa**. Ele segue no modo
demonstração: as skills rodam com dados preparados, o painel marca isso de forma visível e
permanente, e ele constrói tudo igual. Depois cria a aplicação com calma.

Nunca apresente dado de demonstração como se fosse da conta dele.

### 8. Fechar com o recibo

Termine com um resumo curto, que é o que faz a pessoa sentir que está pronto:

- a loja conectada, por **apelido e id** — para ela confirmar que é a conta certa;
- até quando o acesso vale e se a renovação automática está ligada;
- a pasta onde tudo mora;
- **o que isto nunca faz:** não altera preço, estoque, anúncio nem pedido, não adere a
  promoção, não responde pergunta, não envia mensagem;
- **onde desligar:** a administração de permissões no painel de aplicações do Mercado Livre.
  Saber revogar é o que gera confiança, mais que qualquer explicação de protocolo.

Lembre também que `credenciais.txt` e `tokens.json` não devem ser apagados nem
compartilhados — e que a pasta não deve ser movida para dentro de um serviço de sincronização.

---

## O que dizer sobre expiração

Não prometa que o acesso nunca cai, porque cai: o refresh token expira depois de 6 meses sem
uso, o aplicativo para se ficar 4 meses sem nenhuma chamada, e a autorização é invalidada se
a pessoa trocar a senha, renovar o Client Secret ou revogar a permissão.

O que se promete é outra coisa: **quando cair, reconectar é um comando** — repetir a etapa 5.

## Comandos do dia a dia

| O usuário diz | Rode |
|---|---|
| "está conectado?" | `python3 meli.py check` e `python3 meli.py me` |
| "qual conta está conectada?" | `python3 meli.py me` |
| "atualiza o painel" | `python3 painel.py` |
| "reconectar", erro 401 ou 403, `invalid_grant` | etapa 5 de novo (e a 4, se o Secret mudou) |
| "quero ver um dado cru da API" | `python3 meli.py get /algum/path` |
