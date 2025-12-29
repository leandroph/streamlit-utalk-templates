# 📱 Streamlit uTalk Dashboard & Template Creator

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-ff4b4b)
![Status](https://img.shields.io/badge/Status-Active-success)

Painel de controle visual (Front-end) desenvolvido em **Streamlit** para gerenciar a API do **Umbler uTalk**. Este projeto permite criar templates de WhatsApp com validação de regras, visualizar status de aprovação e ler o histórico de conversas dos clientes em uma interface amigável.

---

## ✨ Funcionalidades

### 1. 🛠️ Criador de Templates (Template Builder)
- Interface visual para criação de templates (Marketing, Utilidade, Autenticação).
- **Validação Automática:** Impede o envio de templates que violam as regras do WhatsApp (ex: começar ou terminar frases com variáveis `{{1}}`).
- Gerenciamento fácil de variáveis e exemplos.

### 2. 📂 Gerenciador de Templates
- Listagem completa de todos os templates cadastrados.
- Visualização rápida de Status (`APPROVED`, `PENDING`, `REJECTED`).
- IDs e Categorias visíveis para facilitar a integração.

### 3. 📨 Inbox de Visualização (Chats)
- Leitura de chats em aberto estilo **WhatsApp Web**.
- Diferenciação visual entre mensagens de **Cliente**, **Bot** e **Atendente**.
- Filtro por cliente.

---

## 🚀 Como Rodar Localmente

### Pré-requisitos
- Python 3.9 ou superior.
- Conta na Umbler uTalk com Token de API.

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
