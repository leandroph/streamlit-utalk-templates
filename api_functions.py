import requests
import streamlit as st
import os

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