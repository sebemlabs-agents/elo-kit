# Mudanças do elo-kit

A versão fica em `.claude-plugin/plugin.json`. **Toda mudança que a pessoa deve receber
precisa subir a versão** — sem isso o Claude considera a cópia dela atualizada e deixa o
botão "Atualizar" cinza, mesmo com o GitHub à frente.

## 0.2.0

- **Funciona no Windows.** A skill descobre como o Python se chama na máquina (`python3`,
  `py -3`, `python`) antes do primeiro comando; a checagem de rede deixou de usar `curl` e
  `grep`, que não existem lá; e o guia avisa que `Documentos` costuma ficar dentro do
  OneDrive, onde o pacote recusa gravar.
- **Skill nova: `elo-criativos`.** Produto cru vira título, descrição, benefícios e objeções.
  Não precisa de conexão nem de chave de API.
- **A tabela de problemas ficou alcançável a qualquer momento**, não só durante a instalação.
- **Descrição única e verdadeira** nos três manifestos: descreve o que o pacote faz hoje, em
  vez de prometer skills que ainda não existem.
- **Guias com as duas telas de instalação** do aplicativo, e sem pedir checagem de Python
  antes de começar.

## 0.1.0

- Conexão só-leitura com o Mercado Livre (`elo-conectar-meli`), painel local (`elo-painel`),
  contrato de dados e 43 testes.
