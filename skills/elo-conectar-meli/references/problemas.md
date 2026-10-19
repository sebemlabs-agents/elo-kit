# Solução de problemas — conexão com o Mercado Livre

Procure o sintoma na primeira coluna. Se não estiver aqui, diga ao usuário que não sabe e não
tente adivinhar — errar o diagnóstico custa mais que admitir.

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `python3 pasta.py` para dizendo que a pasta sincroniza | a pasta está dentro de Dropbox, iCloud, Google Drive ou OneDrive | **não contorne.** Peça uma pasta fora do serviço de sincronização e comece ali. O token não pode ir para a nuvem sem o usuário saber |
| Toda chamada falha antes de chegar ao Mercado Livre, ou erro de rede/proxy | `api.mercadolibre.com` não está nos domínios permitidos do Claude | Configurações → Capabilities → domínios permitidos. Em conta de empresa, só o administrador libera. Teste: `curl -s -D - -o /dev/null https://api.mercadolibre.com/ \| grep -ci x-request-id` — `1` = chegou, `0` = bloqueado antes |
| `Faltam valores em credenciais.txt` | arquivo não preenchido ou não salvo | `python3 meli.py check` mostra o que está vazio sem revelar valor. Peça para abrir, preencher e salvar |
| Erro de autorização citando `redirect_uri` | endereço diferente do cadastrado | a linha `MELI_REDIRECT_URI` precisa ser idêntica à do DevCenter, caractere por caractere |
| `O state nao confere` | a URL colada é de outra tentativa | rode `python3 autorizar.py` de novo e use a URL nova |
| `invalid_grant` na autorização | o código expirou (vale poucos minutos) ou já foi usado | refaça os dois passos da etapa 5, sem demora entre eles |
| `invalid_grant` depois de dias funcionando | refresh token expirou (6 meses sem uso), senha da conta mudou, Secret renovado, ou permissão revogada | atualize o `credenciais.txt` se o Secret mudou, e refaça a autorização |
| `invalid_operator_user_id` | autorizou com conta de operador ou colaborador | repita com a conta **administradora** da loja |
| `tokens.json sem refresh_token` | a aplicação não entregou acesso offline | veja "Acesso contínuo" em `devcenter.md` |
| `403 PA_UNAUTHORIZED_RESULT_FROM_POLICIES` | falta permissão funcional | marque as quatro no DevCenter e autorize de novo |
| `401` depois de semanas | acesso expirado | refaça a etapa 5 |
| `429` | muitas chamadas seguidas | espere alguns segundos. Numa sala com muita gente na mesma rede isso é esperado: siga o combinado de todo mundo na mesma tela, comando só no ok |
| A conexão cai algumas horas depois de funcionar | duas cópias usando a mesma credencial | o refresh token é de uso único. Não copie `tokens.json` para outra máquina nem rode a mesma credencial em dois lugares |
| Não consegue apagar `RETORNO.txt` | o ambiente só apaga com permissão do usuário | o `autorizar.py` esvazia o arquivo; avise que ele pode apagar quando quiser |
| `python3` não existe ou é versão antiga | Python não instalado, ou 3.7 e anterior | o pacote precisa de 3.8 ou mais novo. No Mac normalmente já vem; no Windows, instale do site oficial marcando "Add to PATH" |
| Tudo funciona, mas o apelido em `meli.py me` não é a loja dele | autorizou a conta errada | refaça a etapa 5 logado na conta certa |

## Três coisas que não são erro

**O navegador mostra erro ao voltar da autorização.** É esperado, e é o desenho: o endereço
`.invalid` não existe de propósito, então o código fica só na barra de endereço do usuário.

**O painel vem vazio na primeira vez.** Nenhuma skill rodou ainda. Ele explica isso na tela.

**`HTTP 400` em um anúncio durante uma coleta.** Anúncio encerrado não responde consulta de
promoção. A skill pula, conta quantos pulou e segue.

## "Falha ao adicionar marketplace", ao colar o endereço do repositório

A máquina já tem esse catálogo registrado por outro formato de endereço — normalmente a
forma curta `sebemlabs-agents/elo-kit`, gravada numa instalação anterior pelo terminal. O
Claude trata a URL inteira como fonte diferente e recusa, em vez de sobrescrever.

**O que fazer:** cole a forma curta `sebemlabs-agents/elo-kit`. Se o catálogo já estiver
registrado, nem é preciso adicionar: o pacote aparece direto na aba **Descobrir**.

Para começar do zero: `claude plugin marketplace remove elo-kit` desregistra o catálogo (e
desinstala os plugins vindos dele).


## Windows: `python3` não é reconhecido

No Windows o comando quase sempre é **`py -3`**, não `python3`. Digitar `python3` costuma
abrir a Loja da Microsoft em vez de rodar o Python. Teste `py -3 --version` e, se responder
3.8 ou mais novo, use `py -3` em todos os comandos.

Se nem `py -3` nem `python` responderem, instale do site oficial marcando **"Add python.exe
to PATH"** na primeira tela.

## Windows: a pasta Documentos é recusada

No Windows, `Documentos` normalmente está **dentro do OneDrive**, e o pacote recusa — como
deve. Use uma pasta na raiz do perfil, por exemplo `C:\Users\<nome>\elo-meli`.

Não contorne a verificação: o token da conta não pode ir para a nuvem sem o dono saber.
