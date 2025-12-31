"""
MÓDULO: Dashboard Gerenciador WhatsApp - Umbler uTalk
=====================================================

DESCRIÇÃO:
    Interface gráfica desenvolvida em Streamlit para gerenciamento de operações
    na API do uTalk (WhatsApp Business API). Este painel atua como um Frontend
    para as funções definidas em `api_functions.py`.

FUNCIONALIDADES PRINCIPAIS:
    1. Listagem e Visualização de Templates (HSM).
    2. Criação/Edição de Templates com validação rigorosa de regras do Meta/WhatsApp.
    3. Busca híbrida de contatos e encerramento seguro de atendimentos (Session Close).

DEPENDÊNCIAS:
    - streamlit: Framework de UI.
    - pandas: Manipulação de dados tabulares e datas.
    - regex (re): Validações de padrões de texto.
    - api_functions: Módulo proprietário de comunicação com o Backend.

AUTOR: Leandro
DATA DE ATUALIZAÇÃO: Dezembro/2025
VERSÃO: 2.1.0
"""

import time
import re
import streamlit as st
import pandas as pd

# --- Importação do Módulo de Backend ---
# Este módulo deve conter as chamadas `requests` para a API da Umbler.
# Certifique-se de que o arquivo api_functions.py está no mesmo diretório ou no PYTHONPATH.
from api_functions import (
    get_templates,
    create_template,
    delete_template,
    get_contacts,
    close_chat_safe,
    search_contact_by_text
)

# ==============================================================================
# ⚙️ CONFIGURAÇÃO GLOBAL DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Painel Umbler uTalk",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título Principal da Aplicação
st.title("🤖 Gerenciador WhatsApp - Umbler uTalk")

# ==============================================================================
# 🧭 NAVEGAÇÃO LATERAL (SIDEBAR)
# ==============================================================================
# A chave "navegacao" no session_state permite que o código redirecione o usuário
# automaticamente entre abas (ex: clicar em 'Editar' na aba 1 e ir para a aba 2).
menu = st.sidebar.radio(
    "Navegação",
    ["Templates", "Criar Template", "Fechar Conversas"],
    key="navegacao"
)


# ==============================================================================
# 🛠️ COMPONENTES DE UI E FUNÇÕES AUXILIARES
# ==============================================================================

@st.dialog("Detalhes do Template")
def show_template_details(item: dict):
    """
    Renderiza um modal (pop-up) com os detalhes completos de um template.

    Funcionalidades:
    - Visualização colorida do status (Aprovado/Rejeitado).
    - Botão para carregar os dados do template no formulário de edição.
    - Botão para excluir o template (Zona de Perigo).

    Args:
        item (dict): Dicionário contendo os dados do template vindo da API.
                     Esperado chaves: 'id', 'label', 'status', 'content', 'variables'.
    """
    st.subheader(f"{item.get('label', 'Sem Nome')}")

    # --- Definição Visual de Status ---
    # Mapeia o status da API para cores visuais do Streamlit
    status = item.get('status', 'UNKNOWN')
    mapa_cores = {
        "APPROVED": "green",
        "REJECTED": "red",
        "PENDING": "orange",
        "PAUSED": "grey"
    }
    cor_status = mapa_cores.get(status, "blue")

    st.markdown(f"**Status:** :{cor_status}[{status}]")
    st.markdown(f"**Categoria:** {item.get('category', '-')}")
    st.markdown(f"**ID Técnico:** `{item.get('id', '-')}`")

    st.divider()

    # --- AÇÃO: EDITAR / CLONAR ---
    # Ao clicar, injetamos os dados deste template no Session State da aba "Criar Template"
    if st.button("✏️ Editar / Usar como Modelo", type="primary", use_container_width=True):

        # 1. Extração de Variáveis
        # Transforma o formato da API [{'name': 'x', 'example': 'y'}] para o formato da tabela visual
        lista_vars = []
        variaveis = item.get('variables')
        if isinstance(variaveis, list):
            for v in variaveis:
                lista_vars.append({
                    "Nome": v.get("name", ""),
                    "Exemplo": v.get("example", "")
                })

        # 2. Injeção no Estado (Preenchimento do Formulário)
        st.session_state['form_nome'] = item['label']
        st.session_state['form_cat'] = item.get('category', 'MARKETING')
        st.session_state['form_corpo'] = item.get('content', '')
        st.session_state['vars_iniciais'] = lista_vars

        # ⚠️ CRÍTICO: Deletar a chave do editor força o st.data_editor a recarregar
        # os dados de 'vars_iniciais' na próxima renderização.
        if "editor_variaveis" in st.session_state:
            del st.session_state["editor_variaveis"]

        # 3. Redirecionamento
        st.session_state.navegacao = "Criar Template"
        st.rerun()

    st.divider()

    # --- Visualização do Conteúdo ---
    st.markdown("### 📝 Mensagem Completa")
    content = item.get('content', '')
    st.code(content, language="markdown")

    # Tabela de Variáveis (apenas leitura neste modal)
    variaveis = item.get('variables')
    if isinstance(variaveis, list) and len(variaveis) > 0:
        st.divider()
        st.markdown("### 🧩 Variáveis Configuradas")
        df_vars = pd.DataFrame(variaveis)

        # Filtra apenas colunas relevantes se existirem
        cols_existentes = [c for c in ['name', 'example'] if c in df_vars.columns]
        if cols_existentes:
            st.dataframe(
                df_vars[cols_existentes].rename(columns={'name': 'Variável', 'example': 'Exemplo'}),
                hide_index=True,
                width="stretch"
            )

    # --- ZONA DE PERIGO (EXCLUSÃO) ---
    st.divider()
    with st.expander("🗑️ Zona de Perigo (Excluir)"):
        st.warning("Atenção: Essa ação é irreversível e remove o template da Meta.")

        # Key única necessária para evitar conflito se abrir múltiplos modais em sequência
        key_btn = f"btn_del_{item['id']}"

        if st.button("Confirmar Exclusão", type="primary", key=key_btn):
            with st.spinner("Processando exclusão na API..."):
                res = delete_template(item['id'])

                if res.status_code in [200, 204]:
                    st.success("Template excluído com sucesso!")
                    # Invalida o cache local para forçar nova busca na API
                    if 'lista_templates' in st.session_state:
                        del st.session_state['lista_templates']
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Falha ao excluir. Código: {res.status_code} - {res.text}")


# ==============================================================================
# 📂 ABA 1: LISTAR TEMPLATES
# ==============================================================================
if menu == "Templates":
    st.header("📂 Templates Cadastrados")

    # Botão para limpar cache e buscar dados frescos
    if st.button("🔄 Atualizar Lista"):
        if 'lista_templates' in st.session_state:
            del st.session_state['lista_templates']
        st.rerun()

    # --- LAZY LOADING (Carregamento Sob Demanda) ---
    # Só chama a API se os dados não estiverem na memória para economizar requisições.
    if 'lista_templates' not in st.session_state:
        with st.spinner("Conectando à API Umbler..."):
            try:
                st.session_state['lista_templates'] = get_templates()
            except Exception as e:
                st.error(f"Erro crítico de conexão: {e}")
                st.session_state['lista_templates'] = []

    templates = st.session_state['lista_templates']

    # --- RENDERIZAÇÃO DA LISTA ---
    if templates:
        df = pd.DataFrame(templates)

        # Tratamento de Data: ISO 8601 -> Datetime do Pandas
        if 'createdAtUTC' in df.columns:
            df['createdAtUTC'] = pd.to_datetime(df['createdAtUTC'], format='mixed', errors='coerce')
            df = df.sort_values(by='createdAtUTC', ascending=False)

        # Seleção de colunas para exibição limpa
        cols_preferidas = ['label', 'status', 'category', 'createdAtUTC', 'id', 'content']
        cols_finais = [c for c in cols_preferidas if c in df.columns]
        df_show = df[cols_finais].copy()

        # Formatação final para pt-BR
        if 'createdAtUTC' in df_show.columns:
            df_show['createdAtUTC'] = df_show['createdAtUTC'].dt.strftime('%d/%m/%Y %H:%M').fillna("-")

        st.markdown("👇 **Clique em uma linha para ver detalhes e opções**")

        # Tabela Interativa (Streamlit Dataframe com seleção)
        event = st.dataframe(
            df_show,
            width="stretch",
            selection_mode="single-row",  # Permite selecionar apenas 1 por vez
            on_select="rerun",  # Recarrega o app ao clicar
            hide_index=True
        )

        # Detector de Seleção: Abre o modal se houver linha selecionada
        if len(event.selection.rows) > 0:
            idx = event.selection.rows[0]
            # Mapeia o índice visual para o dado original
            item_completo = df.iloc[idx].to_dict()
            show_template_details(item_completo)

        st.metric("Total de Templates", len(templates))
    else:
        st.warning("Nenhum template encontrado ou falha na conexão.")

# ==============================================================================
# ✨ ABA 2: CRIAR NOVO TEMPLATE
# ==============================================================================
elif menu == "Criar Template":
    st.header("✨ Novo Template")

    # --- 1. GERENCIAMENTO DE ESTADO (CLEANUP) ---
    # Se a flag 'limpar_apos_sucesso' estiver ativa, resetamos o formulário
    if st.session_state.get('limpar_apos_sucesso'):
        st.session_state.form_nome = ""
        st.session_state.form_corpo = ""
        st.session_state.vars_iniciais = []
        if "editor_variaveis" in st.session_state:
            del st.session_state["editor_variaveis"]
        st.session_state.limpar_apos_sucesso = False

    # Feedback visual de sucesso (Balões)
    if st.session_state.get('exibir_sucesso'):
        nome_sucesso = st.session_state.get('ultimo_nome_criado', 'Template')
        st.success(f"✅ Template '{nome_sucesso}' processado com sucesso!")
        st.balloons()
        st.session_state.exibir_sucesso = False

    # --- 2. INICIALIZAÇÃO DE VARIÁVEIS DO FORMULÁRIO ---
    # Garante que as chaves existam para evitar KeyError
    if 'form_nome' not in st.session_state: st.session_state.form_nome = ""
    if 'form_corpo' not in st.session_state: st.session_state.form_corpo = ""
    if 'vars_iniciais' not in st.session_state: st.session_state.vars_iniciais = []

    opcoes_cat = ["UTILITY", "MARKETING", "AUTHENTICATION"]
    if 'form_cat' not in st.session_state or st.session_state.form_cat not in opcoes_cat:
        st.session_state.form_cat = "MARKETING"

    # Remove dados residuais de edição anteriores
    if 'edit_data' in st.session_state:
        del st.session_state['edit_data']

    # --- 3. CONSTRUÇÃO DO FORMULÁRIO ---
    with st.form("form_template"):
        nome = st.text_input(
            "Nome do Template (minúsculo, sem espaços)",
            key="form_nome",
            help="Nome interno usado para disparo via API. Ex: aviso_vencimento_v1",
            placeholder="ex: lembrete_consulta_v1"
        )

        categoria = st.selectbox("Categoria", opcoes_cat, key="form_cat")

        corpo = st.text_area(
            "Mensagem",
            height=150,
            key="form_corpo",
            help="Use {{1}}, {{2}} para variáveis.",
            placeholder="Olá {{1}}, sua consulta é dia {{2}}."
        )

        st.info("💡 Regra Meta: Não comece nem termine a frase com variáveis {{n}}.")

        st.subheader("Variáveis")
        st.markdown("Defina os exemplos para cada variável usada no texto acima:")

        # Tabela Editável para Variáveis
        df_vars_input = pd.DataFrame(st.session_state.vars_iniciais, columns=["Nome", "Exemplo"])

        edited_df = st.data_editor(
            df_vars_input,
            num_rows="dynamic",  # Permite adicionar/remover linhas
            column_config={
                "Nome": st.column_config.TextColumn("Nome da Variável", required=True, width="medium"),
                "Exemplo": st.column_config.TextColumn("Exemplo de Conteúdo", required=True, width="medium")
            },
            width="stretch",
            key="editor_variaveis"
        )

        enviar = st.form_submit_button("🚀 Criar / Atualizar Template")

        # --- 4. LÓGICA DE ENVIO E VALIDAÇÃO ---
        if enviar:
            erro_encontrado = False
            texto_limpo = corpo.strip()

            # Validação A: Campos Obrigatórios
            if not nome or not corpo:
                st.error("❌ Preencha o Nome e a Mensagem.")
                erro_encontrado = True

            # Validação B: Regras de Sintaxe do WhatsApp
            # Regex: Verifica se começa com {{...
            if texto_limpo.startswith("{{"):
                st.error("🚫 Regra Meta: O texto NÃO pode começar com uma variável.")
                erro_encontrado = True

            # Regex: Verifica se termina com ...}}
            if re.search(r"}}\W*$", texto_limpo):
                st.error("🚫 Regra Meta: O texto NÃO pode terminar com uma variável.")
                erro_encontrado = True

            # Validação C: Consistência de Variáveis (Texto vs Tabela)
            # Extrai todas as ocorrências de {{números}}
            vars_no_texto = re.findall(r"\{\{(\d+)\}\}", corpo)
            qtd_vars_texto = len(set(vars_no_texto))  # Set remove duplicatas ({{1}} usado 2x conta como 1)

            # Conta linhas preenchidas na tabela
            linhas_validas = edited_df[edited_df["Nome"].str.strip() != ""]
            qtd_vars_tabela = len(linhas_validas)

            if qtd_vars_texto != qtd_vars_tabela:
                st.error(
                    f"❌ Inconsistência: O texto pede {qtd_vars_texto} variáveis, mas a tabela tem {qtd_vars_tabela}.")
                st.info("💡 Certifique-se de que há uma linha na tabela para cada {{n}} único no texto.")
                erro_encontrado = True

            # --- ENVIO PARA API ---
            if not erro_encontrado:
                variaveis_payload = []

                # Montagem do JSON Payload
                for _, row in linhas_validas.iterrows():
                    n = str(row["Nome"]).strip()
                    e = str(row["Exemplo"]).strip()
                    # Fallback para exemplo vazio
                    ex_final = e if e else f"Exemplo {n}"
                    variaveis_payload.append({"name": n, "example": ex_final})

                with st.spinner("Enviando dados para a Umbler/Meta..."):
                    res = create_template(nome, categoria, corpo, variaveis_payload)

                # Tratamento de Respostas HTTP
                if res.status_code in [200, 201]:
                    # Sucesso: Marca flags para exibir feedback e limpar formulário no próximo rerun
                    st.session_state.exibir_sucesso = True
                    st.session_state.ultimo_nome_criado = nome
                    st.session_state.limpar_apos_sucesso = True
                    st.rerun()

                elif res.status_code == 400:
                    # Erro de Validação da API: Tenta parsear JSON para mensagem amigável
                    try:
                        erro_data = res.json()
                        lista_erros = erro_data.get('errors', {}).get('Content', [])

                        if "VariableCannotBeAtTheBeginningOrEnd" in lista_erros:
                            st.error("❌ A API rejeitou: Variável no início ou fim da frase.")
                        else:
                            st.error("❌ Erro de Validação:")
                            st.json(erro_data)
                    except:
                        st.error(f"❌ Erro 400 (Bad Request): {res.text}")
                else:
                    st.error(f"❌ Erro Inesperado ({res.status_code}): {res.text}")

# ==============================================================================
# 🚫 ABA 3: FECHAR CONVERSAS
# ==============================================================================
elif menu == "Fechar Conversas":
    st.header("🚫 Encerrar Atendimentos")

    # Layout de Busca: Input (80%) + Botão (20%)
    col_busca, col_btn = st.columns([4, 1])

    with col_busca:
        termo_busca = st.text_input(
            "🔍 Buscar Contato",
            placeholder="Digite Nome ou Telefone para pesquisar..."
        )

    with col_btn:
        st.write("")
        st.write("")
        # Botão para disparar o evento de busca/reload
        if st.button("🔍 Buscar"):
            st.rerun()

    contatos = []

    # --- LÓGICA DE BUSCA ---
    # Exige no mínimo 2 caracteres para evitar buscar a base inteira
    if termo_busca and len(termo_busca) >= 2:
        with st.spinner(f"Procurando por '{termo_busca}'..."):
            # A função search_contact_by_text realiza busca dupla:
            # 1. Em chats abertos (Prioridade)
            # 2. Na lista de contatos gerais
            contatos = search_contact_by_text(termo_busca)

        if not contatos:
            st.warning(f"Nenhum resultado para: '{termo_busca}'")

    elif termo_busca:
        st.caption("Digite pelo menos 2 caracteres.")
    else:
        st.info("👆 Use a busca acima para localizar o atendimento.")

    # --- EXIBIÇÃO DA LISTA DE RESULTADOS ---
    if contatos:
        st.success(f"{len(contatos)} contato(s) encontrado(s).")

        # Normalização dos dados para DataFrame
        dados_tabela = []
        for c in contatos:
            contact_id = c.get('id')
            # Telefone pode vir em 'phoneNumber' ou 'identifier' dependendo do endpoint
            telefone = c.get('phoneNumber') or c.get('identifier') or "-"

            # Prioridade de Nome: Name > PushName > Telefone
            raw_name = c.get('name') or c.get('pushName')
            nome_cliente = raw_name if raw_name else (telefone if telefone != "-" else "Desconhecido")

            last_date = c.get('createdAtUTC', '-')

            dados_tabela.append({
                "contact_id": contact_id,  # ID Oculto (Chave Primária)
                "Cliente": nome_cliente,
                "Telefone": telefone,
                "Data Criação": last_date
            })

        df_chats = pd.DataFrame(dados_tabela)

        # Formatação de Data
        if "Data Criação" in df_chats.columns:
            df_chats["Data Criação"] = pd.to_datetime(df_chats["Data Criação"], errors='coerce') \
                .dt.strftime('%d/%m/%Y %H:%M').fillna("-")

        st.markdown("👇 **Selecione o contato na lista abaixo:**")

        # Tabela Selecionável
        event_chat = st.dataframe(
            df_chats,
            width="stretch",
            selection_mode="single-row",
            on_select="rerun",
            hide_index=True,
            column_config={
                "contact_id": None  # Oculta o ID técnico, mas mantém nos dados
            }
        )

        # --- LÓGICA DE ENCERRAMENTO ---
        if len(event_chat.selection.rows) > 0:
            idx = event_chat.selection.rows[0]
            contato_selecionado = df_chats.iloc[idx]

            st.divider()

            # Área de Confirmação com destaque visual
            with st.container(border=True):
                st.subheader(f"Fechar conversa de: {contato_selecionado['Cliente']}")
                st.markdown(f"📱 **Telefone:** {contato_selecionado['Telefone']}")
                st.warning("⚠️ Esta ação encerrará a sessão aberta, mas manterá o contato salvo.")

                # Botão com Chave Única (key) para evitar conflito de IDs no Streamlit
                key_btn_close = f"btn_close_{contato_selecionado['contact_id']}"

                if st.button("✅ Confirmar Encerramento", type="primary", key=key_btn_close):
                    with st.spinner("Processando fechamento seguro (Full Update)..."):

                        # Chama a função segura (PUT) que não deleta o contato
                        res = close_chat_safe(contato_selecionado['contact_id'])

                        if res.status_code in [200, 204]:
                            st.success(f"Sucesso! Conversa encerrada.")
                            time.sleep(1.5)  # Pausa para o usuário ler a mensagem
                            st.rerun()  # Atualiza a tela limpa

                        elif res.status_code == 404:
                            st.warning("⚠️ Nenhuma conversa 'Aberta' encontrada no momento.")
                        else:
                            st.error(f"Erro técnico ao fechar: {res.text}")