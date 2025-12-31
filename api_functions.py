import requests
import streamlit as st
import os
import json

# --- LÓGICA DE IMPORTAÇÃO HÍBRIDA ---
try:
    import config

    TOKEN = config.TOKEN
    ORG_ID = config.ORG_ID
    CHANNEL_ID = config.CHANNEL_ID
except ImportError:
    TOKEN = st.secrets["TOKEN"]
    ORG_ID = st.secrets["ORG_ID"]
    CHANNEL_ID = st.secrets["CHANNEL_ID"]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


# --- FUNÇÕES ATUALIZADAS ---

def get_templates():
    """
    Baixa TODOS os templates usando paginação automática.
    """
    url = "https://app-utalk.umbler.com/api/v1/templates/"
    all_templates = []
    skip = 0
    take = 100  # Baixa de 100 em 100

    # Espaço reservado para mostrar progresso no Streamlit (opcional, mas legal)
    status_text = st.empty()

    while True:
        params = {
            "organizationId": ORG_ID,
            "channelId": CHANNEL_ID,
            "Take": take,
            "Skip": skip,
            "Behavior": "GetSliceOnly"
        }

        try:
            # Mostra que está carregando (útil se tiver muitos templates)
            status_text.text(f"⏳ Baixando templates... Já foram {len(all_templates)}")

            response = requests.get(url, headers=HEADERS, params=params)

            if response.status_code == 200:
                dados = response.json()
                items = dados.get('items', [])

                # Se não veio nada, acabou a lista
                if not items:
                    break

                # Adiciona os itens novos na lista geral
                all_templates.extend(items)

                # Prepara o pulo para a próxima página
                skip += len(items)

                # Se vieram menos itens do que pedimos (menos de 100), chegamos no fim
                if len(items) < take:
                    break
            else:
                st.error(f"Erro na API: {response.status_code} - {response.text}")
                break

        except Exception as e:
            st.error(f"Erro de conexão: {e}")
            break

    # Limpa a mensagem de carregamento
    status_text.empty()
    return all_templates


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
        class MockResponse:
            status_code = 500
            text = str(e)

        return MockResponse()


def delete_template(template_id):
    """Remove um template pelo ID, enviando as credenciais da organização"""
    url = f"https://app-utalk.umbler.com/api/v1/templates/{template_id}"

    # --- CORREÇÃO: Adicionamos os parâmetros obrigatórios ---
    params = {
        "organizationId": ORG_ID,
        "channelId": CHANNEL_ID
    }

    try:
        # Agora o requests manda o ID da organização junto com o comando DELETE
        response = requests.delete(url, headers=HEADERS, params=params)
        return response
    except Exception as e:
        class MockResponse:
            status_code = 500
            text = str(e)

        return MockResponse()


# --- NOVAS FUNÇÕES DE CHAT ---

def get_contacts():
    """
    Busca a lista de contatos diretamente.
    Rota: GET /v1/contacts/
    """
    url = "https://app-utalk.umbler.com/api/v1/contacts/"

    params = {
        "organizationId": ORG_ID,
        "Skip": 0,
        "Take": 50,
        "Behavior": "GetSliceOnly"
    }

    try:
        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code == 200:
            return response.json().get('items', [])
        return []
    except Exception as e:
        return []


def close_chat_safe(contact_id):
    """
    Versão V9 (Estratégia GET + PUT Completo):
    Já que PATCH (edição parcial) e DELETE (apagar) são bloqueados:
    1. Baixamos os dados completos do chat.
    2. Alteramos 'open' para False na memória.
    3. Enviamos o objeto INTEIRO de volta com PUT.
    """
    chat_id_para_fechar = None
    chat_data_completo = None  # Variável para guardar o objeto inteiro

    # --- TENTATIVA 1: Busca o Chat Aberto ---
    url_history = f"https://app-utalk.umbler.com/api/v1/contacts/{contact_id}/chats"
    params_history = {
        "organizationId": ORG_ID,
        "ChatState": "All",
        "Take": 50,
        "Sort": "LastMessageDate",
        "Direction": "Desc"
    }

    try:
        resp_check = requests.get(url_history, headers=HEADERS, params=params_history)
        if resp_check.status_code == 200:
            itens = resp_check.json().get('items', [])
            for chat in itens:
                is_open = chat.get('open')
                st = str(chat.get('status') or '').upper()

                if is_open is True or (st and st not in ["CLOSED", "RESOLVED", "CANCELED"]):
                    chat_id_para_fechar = chat.get('id')
                    chat_data_completo = chat  # Guardamos TUDO aqui
                    break
    except Exception as e:
        print(f"Erro Busca: {e}")

    if not chat_id_para_fechar or not chat_data_completo:
        class MockResponse:
            status_code = 404
            text = "Nenhuma conversa aberta encontrada."

        return MockResponse()

    # --- PASSO 2: MODIFICAR O OBJETO NA MEMÓRIA ---
    print(f"🔒 Preparando fechamento do chat {chat_id_para_fechar}...")

    # Forçamos os dados de fechamento no objeto que baixamos
    chat_data_completo['open'] = False
    chat_data_completo['status'] = "Closed"

    # Algumas APIs não gostam que enviemos campos de leitura (como lastMessage) de volta no PUT.
    # Se der erro 400, pode ser necessário remover esses campos, mas vamos tentar enviar tudo primeiro
    # para garantir que não faltem dados obrigatórios.

    # --- PASSO 3: SALVAR COM PUT (SUBSTITUIÇÃO) ---
    url_put = f"https://app-utalk.umbler.com/api/v1/chats/{chat_id_para_fechar}"
    params_put = {"organizationId": ORG_ID}

    try:
        # Enviamos o JSON modificado de volta
        response = requests.put(url_put, headers=HEADERS, params=params_put, json=chat_data_completo)
        return response
    except Exception as e:
        class MockResponse:
            status_code = 500
            text = str(e)

        return MockResponse()


def search_contact_by_text(query):
    """
    Busca inteligente:
    1. Procura primeiro nos CHATS ABERTOS (para achar quem está falando agora).
    2. Depois procura na lista geral de CONTATOS (para achar antigos).
    """
    resultados = []
    ids_encontrados = set()  # Para evitar duplicatas
    q = str(query).lower().strip()

    # --- 1. BUSCA EM CHATS ABERTOS (Prioridade) ---
    url_chats = "https://app-utalk.umbler.com/api/v1/chats"
    params_chats = {
        "organizationId": ORG_ID,
        "status": "OPEN",  # Busca só nos abertos
        "Take": 100  # Analisa as últimas 100 conversas
    }

    try:
        resp_chat = requests.get(url_chats, headers=HEADERS, params=params_chats)
        if resp_chat.status_code == 200:
            itens_chat = resp_chat.json().get('items', [])

            for chat in itens_chat:
                # Extrai o contato de dentro do chat
                contact = chat.get('contact', {})
                if not contact: continue

                # Normaliza dados para busca
                nome = str(contact.get('name') or contact.get('pushName') or "").lower()
                fone = str(contact.get('identifier') or contact.get('phoneNumber') or "").lower()

                # Se encontrou o texto no nome ou telefone
                if q in nome or q in fone:
                    c_id = contact.get('id')
                    if c_id and c_id not in ids_encontrados:
                        # Adiciona à lista de resultados
                        resultados.append(contact)
                        ids_encontrados.add(c_id)
    except Exception as e:
        print(f"Erro ao buscar chats: {e}")

    # --- 2. BUSCA EM CONTATOS (Complementar) ---
    # Se já achou o que queria nos chats, nem precisaria ir aqui, mas mantemos para garantir
    url_contacts = "https://app-utalk.umbler.com/api/v1/contacts/"
    params_contacts = {
        "organizationId": ORG_ID,
        "Skip": 0,
        "Take": 100,
        "Behavior": "GetSliceOnly"
    }

    try:
        resp_contacts = requests.get(url_contacts, headers=HEADERS, params=params_contacts)
        if resp_contacts.status_code == 200:
            itens_contact = resp_contacts.json().get('items', [])

            for c in itens_contact:
                nome = str(c.get('name') or c.get('pushName') or "").lower()
                fone = str(c.get('phoneNumber') or c.get('identifier') or "").lower()

                if q in nome or q in fone:
                    c_id = c.get('id')
                    if c_id and c_id not in ids_encontrados:
                        resultados.append(c)
                        ids_encontrados.add(c_id)
    except Exception:
        pass

    return resultados