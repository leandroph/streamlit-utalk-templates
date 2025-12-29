import requests
import streamlit as st
import os

# --- LÓGICA DE IMPORTAÇÃO HÍBRIDA (LOCAL vs NUVEM) ---
# Tenta importar do arquivo local config.py. 
# Se não encontrar (porque está no GitHub/Streamlit Cloud), pega dos Segredos.
try:
    # Tenta importar localmente
    import config

    TOKEN = config.TOKEN
    ORG_ID = config.ORG_ID
    CHANNEL_ID = config.CHANNEL_ID
except ImportError:
    # Estamos na nuvem! (Streamlit Cloud)
    # Certifique-se de configurar isso no painel "Secrets" do Streamlit
    TOKEN = st.secrets["TOKEN"]
    ORG_ID = st.secrets["ORG_ID"]
    CHANNEL_ID = st.secrets["CHANNEL_ID"]

# --- CONFIGURAÇÃO DOS HEADERS ---
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


# --- FUNÇÕES ---

def get_templates():
    """Baixa todos os templates e retorna um DataFrame ou Lista"""
    url = "https://app-utalk.umbler.com/api/v1/templates/"
    params = {
        "organizationId": ORG_ID,
        "channelId": CHANNEL_ID,
        "Take": 100,
        "Behavior": "GetSliceOnly"
    }
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code == 200:
            dados = response.json()
            return dados.get('items', [])
    except Exception as e:
        st.error(f"Erro de conexão ao buscar templates: {e}")
    return []


def get_open_chats():
    """Baixa os chats abertos"""
    url = "https://app-utalk.umbler.com/api/v1/chats/"
    params = {
        "organizationId": ORG_ID,
        "ChatState": "Open",
        "Take": 50,
        "ChatOrderBy": "LastMessage",
        "IncludePinneds": "true",
        "Behavior": "GetSliceOnly"
    }
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code == 200:
            dados = response.json()
            return dados.get('items', [])
    except Exception as e:
        st.error(f"Erro de conexão ao buscar chats: {e}")
    return []


def get_chat_messages(chat_id):
    """Baixa mensagens de um chat específico usando filtro por ID"""
    url = "https://app-utalk.umbler.com/api/v1/messages/"

    # Baixa até 100 mensagens para não ficar lento no front
    params = {
        "organizationId": ORG_ID,
        "ChatId": chat_id,
        "Take": 100,
        "Skip": 0,
        "Behavior": "GetSliceOnly"
    }
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code == 200:
            dados = response.json()
            msgs = dados.get('items', []) if isinstance(dados, dict) else dados
            # Ordena cronologicamente para o chat (Antigas -> Novas)
            msgs.sort(key=lambda x: x.get('createdAtUTC', ''))
            return msgs
    except Exception as e:
        st.error(f"Erro ao baixar mensagens: {e}")
    return []


def create_template(label, category, content, variables):
    """Envia o template para criação"""
    url = "https://app-utalk.umbler.com/api/v1/templates/"
    payload = {
        "organizationId": ORG_ID,
        "channelId": CHANNEL_ID,
        "label": label,
        "category": category,
        "content": content,
        "variables": variables,
        "language": "pt_BR",
        "templateType": "Text"
    }
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        return response
    except Exception as e:
        # Retorna um objeto fake com status de erro para não quebrar o dashboard
        class MockResponse:
            status_code = 500
            text = str(e)

        return MockResponse()