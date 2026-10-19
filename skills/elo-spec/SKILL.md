---
name: elo-spec
description: Transforma o painel local num plano escrito para subir os dados para Supabase e publicar a tela na Vercel — esquema de tabelas tirado dos dados reais da pessoa, segurança ligada desde o início, e a fronteira do que sobe e do que fica na máquina. Não envia nada. Use quando o usuário quiser colocar o painel na nuvem, compartilhar com a equipe, "subir para o Supabase", "publicar na Vercel", "deixar isso online", "minha equipe precisa ver", ou perguntar como tirar o painel da máquina dele.
---

# Levar o painel para a nuvem — pacote Elo

Lê o que as skills já gravaram e escreve **um plano**, não uma promessa:

```
python3 spec.py
```

Sai um `spec-nuvem.md` na pasta. **Entregue o link no chat** para ele abrir com um clique.

## Antes de rodar — os scripts da pasta

O pacote cresce: skills novas trazem scripts novos, e **a pasta do usuário não se atualiza
sozinha**. Antes do primeiro comando desta skill, confira se o script existe na pasta dele.
Se não existir, copie de `${CLAUDE_PLUGIN_ROOT}/scripts/` para lá — todos os `.py`, de uma vez.

**Nunca sobrescreva `credenciais.txt`, `tokens.json` nem os arquivos da pasta dele.** Só os
scripts do pacote.

É um passo chato e invisível, e é exatamente por isso que ele some: sem os scripts novos, a
skill nova falha dizendo que o arquivo não existe, e parece que a atualização não funcionou.

## O que esta skill faz e o que ela não faz

**Faz:** lê os arquivos reais desta pasta e monta o esquema de tabelas a partir **dos dados
dele** — nome, tipo e tamanho de cada coluna saem do que está lá, não de um modelo pronto.

**Não faz:** não cria conta, não sobe nada, não toca em credencial. Nenhuma linha vai para
lugar nenhum. O documento é para ele executar depois, com alguém junto se quiser.

Diga isso antes de rodar. "Vou preparar o plano para subir" é diferente de "vou subir", e a
diferença importa para quem tem medo de quebrar o que já funciona.

## A fronteira — repita, mesmo que ele não pergunte

**Os dados sobem. A credencial não.**

Quem continua chamando a API do Mercado Livre é a máquina dele. A nuvem guarda só o resultado
já calculado. Se `tokens.json` ou `credenciais.txt` subirem junto, ele entrega a própria conta
de venda para qualquer pessoa que consiga ler aquele banco — e isso inclui gente que ele nem
sabe que tem acesso.

Esta é a parte do documento que você lê em voz alta com ele. O resto ele lê sozinho.

## Por que as tabelas nascem trancadas

O plano liga a segurança de linha em todas as tabelas e **não escreve nenhuma política de
leitura**. Na prática: recém-criada, a tabela não é lida por ninguém, nem por ele.

É de propósito, e é a decisão de desenho mais importante aqui. O erro mais comum em painel
feito com IA é subir a tabela aberta e descobrir depois — e "depois" costuma ser quando
alguém de fora já leu. **Enquanto não existe política, não existe vazamento.**

Escrever a política é uma decisão real: *quem pode ler quais linhas?* Quase sempre a resposta
é "cada pessoa lê as linhas da conta dela". Se ele não souber responder, isso não é falha
dele — é exatamente o assunto que o bloco de segurança trata. **Não escreva a política por
ele no chute.**

## Antes de rodar, confira a origem

Se alguma skill estiver com dados de demonstração, o plano avisa — mas avise você também,
antes. Subir demonstração para a nuvem faz o painel da equipe **nascer mentindo**, e ninguém
vai lembrar de conferir depois.

## Se não houver dado

A skill recusa pasta vazia, e está certa: esquema chutado é o que faz a migração falhar
depois. Rode uma skill do pacote antes — a de promoções ou a de caixa — e volte.

## Como apresentar

Três coisas, nesta ordem: **o que ele já tem** (as tabelas e quantas linhas), **o que sobe e o
que fica**, e **o que o documento não decide por ele** — quem pode ver, quanto tempo guardar,
e quem paga a conta de nuvem.

Essa última parte parece chata e é a que evita arrependimento. Painel na nuvem tem dono e tem
custo quando o uso cresce.

## O degrau seguinte

No fim do documento há um ponteiro para o pacote `superpowers`, para quem quiser testes,
revisão e planos por etapa. **É ponteiro, não pré-requisito** — nada aqui depende de instalar
mais nada. Só mencione se ele demonstrar que quer ir mais fundo.
