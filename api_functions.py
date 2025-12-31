"""
MÓDULO: Funções de API (Backend)
================================

DESCRIÇÃO:
    Centraliza todas as comunicações HTTP com a API da Umbler uTalk (WhatsApp Business).
    Este módulo é agnóstico de interface, ou seja, pode ser usado por CLI, Scripts ou Streamlit.

RESPONSABILIDADES:
    1. Autenticação e Gerenciamento de Configurações/Segredos.
    2. CRUD de Templates (HSM) com paginação automática.
    3. Busca e Manipulação de Contatos e Chats.
    4. Lógica de "Fechamento Seguro" (Workaround para APIs REST restritivas).

AUTOR: Leandro
DATA: Dezembro/2025
"""

import requests
import streamlit as st
import os
import json
from typing import List, Dict, Union, Any

# ==============================================================================
# 🔐 CONFIGURAÇÃO DE AMBIENTE E SEGURANÇA
# ==============================================================================
# Lógica Híbrida: Tenta carregar de arquivo local (config.py) para desenvolvimento.
# Se falhar, assume que está na nuvem (Streamlit Cloud) e usa st.secrets.
try:
    import config

    TOKEN = config.TOKEN
    ORG_ID = config.ORG_ID
    CHANNEL_ID = config.CHANNEL_ID
except ImportError:
    # Fallback para Segredos do Streamlit Cloud
    TOKEN = st.secrets["TOKEN"]
    ORG_ID = st.secrets["ORG_ID"]
    CHANNEL_ID = st.secrets["CHANNEL_ID"]

# Headers padrão para todas as requisições (JSON + Bearer Token)
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


# ==============================================================================
# 📂 GERENCIAMENTO DE TEMPLATES
# ==============================================================================

def get_templates() -> List[Dict]:
    """
    Recupera TODOS os templates cadastrados na conta, lidando com a paginação da API.

    A API da Umbler retorna dados em páginas (fatias). Esta função cria um loop
    para baixar página por página até que não haja mais registros.

    Returns:
        List[Dict]: Uma lista contendo todos os objetos de template encontrados.
    """
    url = "https://app-utalk.umbler.com/api/v1/templates/"
    all_templates = []
    skip = 0
    take = 100  # Tamanho do lote (Batch size)

    # Elemento de UI para feedback visual (opcional, mas útil em conexões lentas)
    status_text = st.empty()

    while True:
        params = {
            "organizationId": ORG_ID,
            "channelId": CHANNEL_ID,
            "Take": take,
            "Skip": skip,
            "Behavior": "GetSliceOnly"  # Otimização: Traz apenas a fatia de dados, sem metadados extras
        }

        try:
            status_text.text(f"⏳ Sincronizando templates... {len(all_templates)} baixados.")

            response = requests.get(url, headers=HEADERS, params=params)

            if response.status_code == 200:
                dados = response.json()
                items = dados.get('items', [])

                # Critério de Parada 1: Lista vazia
                if not items:
                    break

                all_templates.extend(items)
                skip += len(items)  # Avança o cursor para a próxima página

                # Critério de Parada 2: Se veio menos itens que o solicitado, é a última página
                if len(items) < take:
                    break
            else:
                st.error(f"Erro na API (Templates): {response.status_code} - {response.text}")
                break

        except Exception as e:
            st.error(f"Falha de conexão ao buscar templates: {e}")
            break

    status_text.empty()  # Limpa a mensagem de carregamento
    return all_templates


def create_template(label: str, category: str, content: str, variables: List[Dict]) -> requests.Response:
    """
    Envia uma solicitação para criar um novo template na Umbler/Meta.

    Args:
        label (str): Nome interno do template (ex: 'aviso_vencimento').
        category (str): Categoria (MARKETING, UTILITY, AUTHENTICATION).
        content (str): Texto da mensagem com variáveis {{n}}.
        variables (List[Dict]): Lista de exemplos [{'name': '1', 'example': 'João'}].

    Returns:
        requests.Response: Objeto de resposta contendo status e dados (ou erros).
    """
    url = "https://app-utalk.umbler.com/api/v1/templates/"

    payload = {
        "organizationId": ORG_ID,
        "channelId": CHANNEL_ID,
        "label": label,
        "category": category,
        "content": content,
        "variables": variables,
        "language": "pt_BR",  # Hardcoded para PT-BR conforme requisito
        "templateType": "Text"
    }

    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        return response
    except Exception as e:
        # Mock de erro para evitar crash no frontend
        class MockResponse:
            status_code = 500
            text = str(e)

            def json(self): return {}

        return MockResponse()


def delete_template(template_id: str) -> requests.Response:
    """
    Remove um template existente.
    NOTA: A API exige organizationId e channelId como Query Params no DELETE.
    """
    url = f"https://app-utalk.umbler.com/api/v1/templates/{template_id}"

    params = {
        "organizationId": ORG_ID,
        "channelId": CHANNEL_ID
    }

    try:
        response = requests.delete(url, headers=HEADERS, params=params)
        return response
    except Exception as e:
        class MockResponse:
            status_code = 500
            text = str(e)

        return MockResponse()


# ==============================================================================
# 💬 GERENCIAMENTO DE CHATS E CONTATOS
# ==============================================================================

def get_contacts() -> List[Dict]:
    """
    Busca os contatos mais recentes da organização (não filtra por status de chat).
    Útil para listagens gerais.
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
        print(f"Erro ao buscar contatos: {e}")
        return []


def close_chat_safe(contact_id: str) -> requests.Response:
    """
    Encerra um atendimento de forma segura (sem apagar o contato).

    ESTRATÉGIA (Full Update / GET+PUT):
    Como a API bloqueia DELETE em chats abertos e não suporta PATCH parcial:
    1. Baixa o objeto completo da conversa ativa.
    2. Modifica localmente o status para 'Closed' e open=False.
    3. Devolve o objeto inteiro atualizado via PUT.

    Args:
        contact_id (str): ID do contato dono da conversa.

    Returns:
        requests.Response: Resultado da operação de fechamento.
    """
    chat_id_para_fechar = None
    chat_data_completo = None  # Armazena o JSON completo do chat

    # --- PASSO 1: Identificar a Conversa Aberta ---
    # Busca no histórico recente do contato
    url_history = f"https://app-utalk.umbler.com/api/v1/contacts/{contact_id}/chats"
    params_history = {
        "organizationId": ORG_ID,
        "ChatState": "All",  # Traz abertos, fechados, waiting, etc.
        "Take": 50,
        "Sort": "LastMessageDate",
        "Direction": "Desc"
    }

    try:
        resp_check = requests.get(url_history, headers=HEADERS, params=params_history)
        if resp_check.status_code == 200:
            itens = resp_check.json().get('items', [])
            for chat in itens:
                # Verifica flag booleana 'open' ou status textual
                is_open = chat.get('open')
                st = str(chat.get('status') or '').upper()

                # Se estiver tecnicamente aberto ou status não for finalizado
                if is_open is True or (st and st not in ["CLOSED", "RESOLVED", "CANCELED"]):
                    chat_id_para_fechar = chat.get('id')
                    chat_data_completo = chat  # CLONE: Guarda o objeto para reenvio
                    break
    except Exception as e:
        print(f"Erro ao buscar histórico de chat: {e}")

    # Validação: Se não achou nada para fechar, retorna 404 simulado
    if not chat_id_para_fechar or not chat_data_completo:
        class MockResponse:
            status_code = 404
            text = "Nenhuma conversa ativa encontrada para este contato."

        return MockResponse()

    # --- PASSO 2: Modificação em Memória ---
    print(f"🔒 Preparando payload de fechamento para chat {chat_id_para_fechar}...")

    # Força os estados de fechamento no objeto clonado
    chat_data_completo['open'] = False
    chat_data_completo['status'] = "Closed"

    # Nota: Se a API começar a recusar campos como 'lastMessage', removê-los aqui:
    # if 'lastMessage' in chat_data_completo: del chat_data_completo['lastMessage']

    # --- PASSO 3: Atualização Completa (PUT) ---
    url_put = f"https://app-utalk.umbler.com/api/v1/chats/{chat_id_para_fechar}"
    params_put = {"organizationId": ORG_ID}

    try:
        # Envia o JSON modificado substituindo o anterior
        response = requests.put(url_put, headers=HEADERS, params=params_put, json=chat_data_completo)
        return response
    except Exception as e:
        class MockResponse:
            status_code = 500
            text = str(e)

        return MockResponse()


def search_contact_by_text(query: str) -> List[Dict]:
    """
    Realiza uma Busca Inteligente Híbrida.

    Fluxo de Busca:
    1. Prioridade: Busca nos CHATS ABERTOS (Geralmente o usuário quer fechar quem está falando).
    2. Fallback: Busca na base geral de CONTATOS (Caso seja um contato antigo/fechado).

    Args:
        query (str): Texto para busca (Nome, Telefone ou ID).

    Returns:
        List[Dict]: Lista de contatos únicos encontrados.
    """
    resultados = []
    ids_encontrados = set()  # Set para garantir unicidade (evita duplicatas na tabela)
    q = str(query).lower().strip()

    # --- ESTRATÉGIA 1: Buscar em Chats Ativos ---
    url_chats = "https://app-utalk.umbler.com/api/v1/chats"
    params_chats = {
        "organizationId": ORG_ID,
        "status": "OPEN",  # Filtro de API: Apenas abertos
        "Take": 100
    }

    try:
        resp_chat = requests.get(url_chats, headers=HEADERS, params=params_chats)
        if resp_chat.status_code == 200:
            itens_chat = resp_chat.json().get('items', [])

            for chat in itens_chat:
                # O objeto chat contem um sub-objeto 'contact'
                contact = chat.get('contact', {})
                if not contact: continue

                # Normalização para comparação (Case insensitive)
                nome = str(contact.get('name') or contact.get('pushName') or "").lower()
                fone = str(contact.get('identifier') or contact.get('phoneNumber') or "").lower()

                if q in nome or q in fone:
                    c_id = contact.get('id')
                    if c_id and c_id not in ids_encontrados:
                        resultados.append(contact)
                        ids_encontrados.add(c_id)
    except Exception as e:
        print(f"Erro na busca de chats: {e}")

    # --- ESTRATÉGIA 2: Buscar na Base Geral ---
    # Só executa se o usuário pesquisar algo, complementando a busca anterior
    url_contacts = "https://app-utalk.umbler.com/api/v1/contacts/"
    params_contacts = {
        "organizationId": ORG_ID,
        "Skip": 0,
        "Take": 100,  # Limite de segurança para performance
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
                    # Só adiciona se não foi achado na etapa anterior
                    if c_id and c_id not in ids_encontrados:
                        resultados.append(c)
                        ids_encontrados.add(c_id)
    except Exception:
        pass  # Falhas silenciosas aqui são aceitáveis (apenas retorna o que achou antes)

    return resultados