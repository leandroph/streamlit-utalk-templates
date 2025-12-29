# api_functions.py
import requests
import config

HEADERS = {
    "Authorization": f"Bearer {config.TOKEN}",
    "Content-Type": "application/json"
}


def get_templates():
    """Baixa todos os templates e retorna um DataFrame ou Lista"""
    url = "https://app-utalk.umbler.com/api/v1/templates/"
    params = {
        "organizationId": config.ORG_ID,
        "channelId": config.CHANNEL_ID,
        "Take": 100,
        "Behavior": "GetSliceOnly"
    }
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        dados = response.json()
        return dados.get('items', [])
    return []


def get_open_chats():
    """Baixa os chats abertos"""
    url = "https://app-utalk.umbler.com/api/v1/chats/"
    params = {
        "organizationId": config.ORG_ID,
        "ChatState": "Open",
        "Take": 50,
        "ChatOrderBy": "LastMessage",
        "IncludePinneds": "true",
        "Behavior": "GetSliceOnly"
    }
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        dados = response.json()
        return dados.get('items', [])
    return []


def get_chat_messages(chat_id):
    """Baixa mensagens de um chat específico usando filtro por ID"""
    url = "https://app-utalk.umbler.com/api/v1/messages/"
    all_msgs = []
    skip = 0

    # Baixa até 100 mensagens para não ficar lento no front
    params = {
        "organizationId": config.ORG_ID,
        "ChatId": chat_id,
        "Take": 100,
        "Skip": skip,
        "Behavior": "GetSliceOnly"
    }
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        dados = response.json()
        msgs = dados.get('items', []) if isinstance(dados, dict) else dados
        # Ordena cronologicamente para o chat
        msgs.sort(key=lambda x: x.get('createdAtUTC', ''))
        return msgs
    return []


def create_template(label, category, content, variables):
    """Envia o template para criação"""
    url = "https://app-utalk.umbler.com/api/v1/templates/"
    payload = {
        "organizationId": config.ORG_ID,
        "channelId": config.CHANNEL_ID,
        "label": label,
        "category": category,
        "content": content,
        "variables": variables,
        "language": "pt_BR",
        "templateType": "Text"
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    return response