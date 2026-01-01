# 🤖 Streamlit uTalk Dashboard & Template Creator

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B?logo=streamlit&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-success)
![API](https://img.shields.io/badge/API-Umbler%20uTalk-orange)

Painel administrativo (Frontend) desenvolvido para gerenciar a API do **Umbler uTalk** (WhatsApp Business API).

Este projeto resolve dores comuns de quem usa a API crua: **criação facilitada de templates** (com validação de regras do Meta) e **encerramento seguro de atendimentos** sem perda de dados de contato.

---

## ✨ Funcionalidades Principais

### 1. 🛠️ Criador de Templates Inteligente
Interface visual para criar templates HSM (Marketing, Utilidade, Autenticação) sem erro.
- **Validação Regex em Tempo Real:** Impede o envio se o texto começar/terminar com variáveis (Regra estrita do WhatsApp).
- **Controle de Variáveis:** Garante que o número de variáveis no texto (`{{1}}`, `{{2}}`) bata exatamente com os exemplos fornecidos.
- **Feedback Visual:** Alertas claros de sucesso ou rejeição pela API.

### 2. 🚫 Gestão de Atendimentos (Smart Close)
Um sistema robusto para localizar e encerrar conversas travadas ou finalizadas.
- **Busca Híbrida:** Pesquisa contatos simultaneamente em *Sessões Abertas* (prioridade) e na *Base Geral*.
- **Encerramento Seguro (Safe Close):** Utiliza uma estratégia avançada de `GET + PUT (Full Update)` para alterar o status da conversa para `Closed` **sem excluir o contato** da agenda (contornando limitações de `DELETE` da API).
- **Identificação Visual:** Mostra nome, telefone e data da última interação.

### 3. 📂 Biblioteca de Templates
- Listagem completa com paginação automática (Lazy Loading).
- Visualização de Status com color code (`APPROVED` 🟢, `REJECTED` 🔴, `PENDING` 🟠).
- Opção de **Clonar Template**: Usa um template existente como base para criar um novo.

---

## 📸 Screenshots

*(Espaço reservado para você colocar prints da tela)*

| Lista de Templates | Criar Template | Fechar Conversa |
|:---:|:---:|:---:|
| *Coloque print aqui* | *Coloque print aqui* | *Coloque print aqui* |

---

## 🚀 Instalação e Execução Local

### Pré-requisitos
* Python 3.9+
* Token da API uTalk (Organization ID e Channel ID)


### 1. Clonar o repositório
```bash
git clone [https://github.com/SEU_USUARIO/streamlit-utalk-create-dashboard-templates.git](https://github.com/SEU_USUARIO/streamlit-utalk-create-dashboard-templates.git)
cd streamlit-utalk-create-dashboard-templates
```

### 2. Instalar dependências
```bash
pip install -r requirements.txt
```

### 3. Configurar Credenciais

Por segurança, as senhas não são enviadas ao GitHub.

Renomeie o arquivo config.example.py para config.py.

Adicione suas chaves da Umbler:

```python

# config.py
TOKEN = "SEU_TOKEN_AQUI"
ORG_ID = "SEU_ORG_ID"
CHANNEL_ID = "SEU_CHANNEL_ID"
```
### 4. Executar o Dashboard

```bash
streamlit run dashboard.py
```
> O painel abrirá automaticamente no seu navegador (geralmente em http://localhost:8501).

## ☁️ Como Rodar na Nuvem (Streamlit Cloud)

1.Este projeto está pronto para deploy gratuito no Streamlit Community Cloud.

2.Faça o fork/upload deste repositório para o seu GitHub.

3.Crie uma conta no Streamlit Share.

4.Conecte seu repositório e clique em Deploy.

5.Nas Advanced Settings do Streamlit, vá em Secrets e adicione suas chaves:

```Ini, TOML
TOKEN = "sua_chave_token"
ORG_ID = "sua_org_id"
CHANNEL_ID = "seu_channel_id"
```
## 📂 Estrutura do Projeto

```text
📦 streamlit-utalk-create-dashboard-templates
 ┣ 📜 api_functions.py     # Lógica de conexão com a API (Backend)
 ┣ 📜 dashboard.py         # Interface visual (Frontend Streamlit)
 ┣ 📜 config.example.py    # Modelo de configuração (Seguro)
 ┣ 📜 requirements.txt     # Dependências do projeto
 ┗ 📜 README.md            # Documentação
```
