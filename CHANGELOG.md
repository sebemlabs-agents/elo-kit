# Mudanças do prometheus

**O manifesto não fixa versão de propósito.** Sem `version`, o Claude usa o commit como
versão: todo push publicado vira uma versão nova, e quem está com atualização automática
ligada recebe sozinho, sem rodar nada e sem reinstalar.

Fixar `version` aqui faria o oposto — prenderia todo mundo na cópia antiga até alguém lembrar
de mudar o número à mão. Já aconteceu: o pacote ficou em `0.1.0` por cinco mudanças seguidas
e o botão "Atualizar" aparecia cinza, com o GitHub três commits à frente.

Este arquivo existe para contar o que mudou, não para controlar entrega.

## Outubro de 2026

- **Funciona no Windows.** A skill descobre como o Python se chama na máquina (`python3`,
  `py -3`, `python`) antes do primeiro comando; a checagem de rede deixou de usar `curl` e
  `grep`, que não existem lá; e o guia avisa que `Documentos` costuma ficar dentro do
  OneDrive, onde o pacote recusa gravar.
- **Skill nova: `prometheus-criativos`.** Produto cru vira título, descrição, benefícios e objeções.
  Não precisa de conexão nem de chave de API.
- **A tabela de problemas ficou alcançável a qualquer momento**, não só durante a instalação.
- **Descrição única e verdadeira** nos três manifestos: descreve o que o pacote faz hoje, em
  vez de prometer skills que ainda não existem.
- **Guias com as duas telas de instalação** do aplicativo, e sem pedir checagem de Python
  antes de começar.

## O começo

- Conexão só-leitura com o Mercado Livre (`prometheus-conectar-meli`), painel local (`prometheus-painel`),
  contrato de dados e 43 testes.

## 19 de outubro, tarde

- **`prometheus-promocoes`**: a fila do que termina na janela, com anúncios dentro, desconto mínimo
  e o que já foi aderido. Recorte do radar que roda na operação, trazido para o contrato.
- **`prometheus-caixa`**: o calendário de liberação das vendas — quanto cai e quando. Não é o saldo
  da carteira, e a skill diz isso antes de mostrar número.
- **`prometheus-spec`**: lê o painel local e escreve o plano para subir para Supabase e Vercel, com
  o esquema tirado dos dados reais, segurança de linha ligada e nenhuma política — a tabela
  nasce trancada de propósito.
- **Correção silenciosa que teria estragado o primeiro teste:** skill nova chega pela
  atualização, mas o script dela não aparece sozinho na pasta de quem já instalou. As skills
  agora conferem e copiam de `${CLAUDE_PLUGIN_ROOT}/scripts/` antes do primeiro comando.
- **`prometheus-planilha`**: lê qualquer CSV ou XLSX — exportação de marketplace, relatório de ERP,
  custo feito à mão — descreve as colunas e deixa o mapeamento com quem entende a planilha.
  Sem formato obrigatório, sem dependência instalada. O contrato ganha a origem `export`, e
  com ela `capturado_em`: dado de arquivo tem duas idades, e o painel mostra as duas.
- **`prometheus-margem`**: a dor número um declarada nas mentorias. Preço menos comissão, frete,
  custo e imposto. Componente ausente não vira zero — a linha fica sem margem e diz qual
  faltou; zero declarado é diferente de vazio. Média ponderada pelo preço, e os negativos
  aparecem primeiro.
- **Pendência resolvida:** não existe limite de uma aplicação por titular no DevCenter.
  Verificado em conta de vendedor brasileira com três aplicações simultâneas. Quem já tem
  aplicação de ERP passa a ter o caminho seguro como primeira opção: criar uma nova, sem
  encostar na que sustenta a integração em produção.
