# Sistema de Controle Financeiro com Excel

Este projeto usa **Excel como base de dados** e uma interface web feita em **Streamlit**.

## O que ele faz
- dashboard com total gasto, pago e pendente
- filtro por cartão, mês e status
- cadastro rápido de lançamentos
- edição direta dos lançamentos
- atualização automática da aba **Resumo Mensal**
- exportação do Excel atualizado

## Arquivos
- `app.py` → interface do sistema
- `base_financeira_template.xlsx` → base inicial em Excel
- `requirements.txt` → dependências

## Como rodar
1. Instale o Python 3.11 ou superior.
2. No terminal, entre na pasta do projeto.
3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Rode o sistema:

```bash
streamlit run app.py
```

## Observações
- O sistema salva tudo no arquivo `base_financeira_template.xlsx`.
- Se você quiser trocar o arquivo principal, defina a variável de ambiente `FINANCE_FILE` apontando para outro `.xlsx`.
- O campo **Mês da fatura** deve ficar no formato `AAAA-MM`.
