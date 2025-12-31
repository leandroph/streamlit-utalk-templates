from datetime import time

import streamlit as st
import pandas as pd
import re
from api_functions import get_templates, create_template, delete_template, get_contacts, close_chat

# Configuração da Página
st.set_page_config(page_title="Painel Umbler uTalk", page_icon="💬", layout="wide")

# Título e Sidebar
st.title("🤖 Gerenciador WhatsApp - Umbler uTalk")

# MENU: Adicionamos key="navegacao" para controle via código
menu = st.sidebar.radio("Navegação", ["Templates", "Criar Template", "Fechar Conversas"], key="navegacao")


@st.dialog("Detalhes do Template")
def show_template_details(item):
    st.subheader(f"{item['label']}")

    # Status com cor
    status = item.get('status', 'UNKNOWN')
    cor_status = "green" if status == "APPROVED" else "red" if status == "REJECTED" else "orange"
    st.markdown(f"**Status:** :{cor_status}[{status}]")
    st.markdown(f"**Categoria:** {item.get('category', '-')}")
    st.markdown(f"**ID:** `{item.get('id', '-')}`")

    st.divider()

    # Botão de Ação: EDITAR / CLONAR
    if st.button("✏️ Editar / Usar como Modelo", type="primary", use_container_width=True):

        # 1. Prepara a lista de variáveis para a tabela
        lista_vars = []
        variaveis = item.get('variables')
        if isinstance(variaveis, list):
            for v in variaveis:
                lista_vars.append({
                    "Nome": v.get("name", ""),
                    "Exemplo": v.get("example", "")
                })

        # 2. Preenche memória
        st.session_state['form_nome'] = item['label']
        st.session_state['form_cat'] = item.get('category', 'MARKETING')
        st.session_state['form_corpo'] = item.get('content', '')

        # Salva a lista de variáveis para iniciar a tabela
        st.session_state['vars_iniciais'] = lista_vars

        # ⚠️ IMPORTANTE: Deleta o estado do editor para forçar ele a carregar os novos dados
        if "editor_variaveis" in st.session_state:
            del st.session_state["editor_variaveis"]

        # 3. Muda a aba
        st.session_state.navegacao = "Criar Template"
        st.rerun()

    st.divider()

    st.markdown("### 📝 Mensagem Completa")
    content = item.get('content', '')
    st.code(content, language="markdown")

    # Exibição de Variáveis (Visualização apenas)
    variaveis = item.get('variables')
    if isinstance(variaveis, list) and len(variaveis) > 0:
        st.divider()
        st.markdown("### 🧩 Variáveis Configuradas")
        df_vars = pd.DataFrame(variaveis)
        if 'name' in df_vars.columns:
            cols_show = {'name': 'Variável', 'example': 'Exemplo de Conteúdo'}
            cols_existentes = [c for c in cols_show.keys() if c in df_vars.columns]

            st.dataframe(
                df_vars[cols_existentes].rename(columns=cols_show),
                hide_index=True,
                width="stretch"
            )

    # --- 🗑️ ZONA DE EXCLUSÃO ---
    st.divider()
    with st.expander("🗑️ Zona de Perigo (Excluir)"):
        st.warning("Atenção: Essa ação não pode ser desfeita.")

        if st.button("Confirmar Exclusão", type="primary", key=f"btn_del_{item['id']}"):
            with st.spinner("Excluindo..."):
                res = delete_template(item['id'])

                if res.status_code == 200 or res.status_code == 204:
                    st.success("Template excluído!")
                    if 'lista_templates' in st.session_state:
                        del st.session_state['lista_templates']
                    st.rerun()
                else:
                    st.error(f"Erro ao excluir: {res.text}")

# ==============================================================================
# 📄 ABA 1: LISTAR TEMPLATES
# ==============================================================================
if menu == "Templates":
    st.header("📂 Templates Cadastrados")

    # Botão de Forçar Atualização
    if st.button("🔄 Atualizar Lista"):
        if 'lista_templates' in st.session_state:
            del st.session_state['lista_templates']
        st.rerun()

    # --- LÓGICA DE DOWNLOAD ---
    if 'lista_templates' not in st.session_state:
        with st.spinner("Baixando templates da API... (Aguarde)"):
            st.session_state['lista_templates'] = get_templates()

    # Recupera dados
    templates = st.session_state['lista_templates']

    if templates:
        df = pd.DataFrame(templates)

        # 1. TRATAMENTO
        if 'createdAtUTC' in df.columns:
            df['createdAtUTC'] = pd.to_datetime(df['createdAtUTC'], format='mixed')
            df = df.sort_values(by='createdAtUTC', ascending=False)

        df = df.reset_index(drop=True)

        # 2. PREPARAÇÃO VISUAL
        cols_preferidas = ['label', 'status', 'category', 'createdAtUTC', 'id', 'content']
        cols_finais = [c for c in cols_preferidas if c in df.columns]

        df_show = df[cols_finais].copy()

        if 'createdAtUTC' in df_show.columns:
            df_show['createdAtUTC'] = df_show['createdAtUTC'].dt.strftime('%d/%m/%Y %H:%M')

        # 3. TABELA INTERATIVA
        st.markdown("👇 **Clique em uma linha para ver os detalhes**")

        # CORREÇÃO 2: width="stretch" na tabela principal
        event = st.dataframe(
            df_show,
            width="stretch",
            selection_mode="single-row",
            on_select="rerun",
            hide_index=True
        )

        # 4. ABRIR POP-UP
        if len(event.selection.rows) > 0:
            idx_selecionado = event.selection.rows[0]
            item_completo = df.iloc[idx_selecionado]
            show_template_details(item_completo)

        st.metric("Total de Templates", len(templates))
    else:
        st.warning("Nenhum template encontrado.")

# ==============================================================================
# ✨ ABA 2: CRIAR NOVO TEMPLATE
# ==============================================================================
elif menu == "Criar Template":
    st.header("✨ Novo Template")

    # --- 1. LÓGICA DE LIMPEZA E SUCESSO ---
    if st.session_state.get('limpar_apos_sucesso'):
        st.session_state.form_nome = ""
        st.session_state.form_corpo = ""
        # Limpa também a tabela de variáveis
        st.session_state.vars_iniciais = []
        if "editor_variaveis" in st.session_state:
            del st.session_state["editor_variaveis"]
        st.session_state.limpar_apos_sucesso = False

    if st.session_state.get('exibir_sucesso'):
        nome_sucesso = st.session_state.get('ultimo_nome_criado', 'Template')
        st.success(f"✅ Template '{nome_sucesso}' criado com sucesso!")
        st.balloons()
        st.session_state.exibir_sucesso = False

        # --- 2. INICIALIZAÇÃO SEGURA ---
    if 'form_nome' not in st.session_state: st.session_state.form_nome = ""
    if 'form_corpo' not in st.session_state: st.session_state.form_corpo = ""
    # Inicializa dados da tabela se não existirem
    if 'vars_iniciais' not in st.session_state: st.session_state.vars_iniciais = []

    opcoes_cat = ["UTILITY", "MARKETING", "AUTHENTICATION"]
    if 'form_cat' not in st.session_state or st.session_state.form_cat not in opcoes_cat:
        st.session_state.form_cat = "MARKETING"

    # --- 3. PREENCHIMENTO AUTOMÁTICO (EDITAR) ---
    # Essa parte foi migrada para dentro da show_template_details, mas mantemos o cleanup se houver resquício
    if 'edit_data' in st.session_state:
        del st.session_state['edit_data']

    # --- 4. FORMULÁRIO ---
    with st.form("form_template"):
        nome = st.text_input("Nome do Template (minúsculo, sem espaços)",
                             key="form_nome",
                             placeholder="ex: lembrete_consulta_v1")

        categoria = st.selectbox("Categoria", opcoes_cat, key="form_cat")

        corpo = st.text_area("Mensagem", height=150, key="form_corpo",
                             placeholder="Olá {{1}}...")

        st.info("💡 Dica: Não comece nem termine a frase com variáveis {{n}}.")

        st.subheader("Variáveis")
        st.markdown("Adicione as variáveis e seus exemplos abaixo:")

        # Prepara o DataFrame inicial
        df_vars_input = pd.DataFrame(st.session_state.vars_iniciais, columns=["Nome", "Exemplo"])

        # --- TABELA EDITÁVEL (CORRIGIDA) ---
        edited_df = st.data_editor(
            df_vars_input,
            num_rows="dynamic",
            column_config={
                # CORREÇÃO: Removemos 'placeholder' e usamos 'help' e 'width'
                "Nome": st.column_config.TextColumn(
                    "Nome da Variável",
                    required=True,
                    width="medium",
                    help="Ex: nome_cliente"
                ),
                "Exemplo": st.column_config.TextColumn(
                    "Exemplo de Conteúdo",
                    required=True,
                    width="medium",
                    help="Ex: João Silva"
                )
            },
            use_container_width=True,
            key="editor_variaveis"
        )

        enviar = st.form_submit_button("🚀 Criar / Atualizar Template")

        if enviar:
            # --- VALIDAÇÃO E ENVIO ---
            erro_encontrado = False

            if not nome or not corpo:
                st.error("❌ Preencha o Nome e a Mensagem.")
                erro_encontrado = True

            if corpo.strip().startswith("{{"):
                st.error("🚫 O texto NÃO pode começar com uma variável.")
                erro_encontrado = True

            if re.search(r"}}\W*$", corpo.strip()):
                st.error("🚫 O texto NÃO pode terminar com uma variável.")
                erro_encontrado = True

            # --- 🆕 VALIDAÇÃO DE CONTAGEM DE VARIÁVEIS ---
            # 1. Conta quantas {{n}} existem no texto (ex: {{1}}, {{2}} = 2 variáveis)
            vars_no_texto = re.findall(r"\{\{(\d+)\}\}", corpo)
            qtd_vars_texto = len(
                set(vars_no_texto))  # Usa set para contar únicos (se usar {{1}} duas vezes conta como 1)

            # 2. Conta quantas linhas válidas tem na tabela
            # Filtra linhas vazias para não contar errado
            linhas_validas = edited_df[edited_df["Nome"].str.strip() != ""]
            qtd_vars_tabela = len(linhas_validas)

            if qtd_vars_texto != qtd_vars_tabela:
                st.error(
                    f"❌ Contagem Incorreta: O texto pede {qtd_vars_texto} variáveis, mas você definiu {qtd_vars_tabela} na tabela.")
                st.info(
                    f"💡 Dica: Se você usou até {{{{ {qtd_vars_texto} }}}} no texto, a tabela precisa ter exatamente {qtd_vars_texto} linhas preenchidas.")
                erro_encontrado = True
            # ---------------------------------------------

            if not erro_encontrado:
                variaveis_payload = []

                # Itera sobre as linhas VALIDAS da tabela
                for index, row in linhas_validas.iterrows():
                    n = row["Nome"]
                    e = row["Exemplo"]

                    # Garante que tem exemplo
                    ex_final = e if (e and pd.notna(e) and str(e).strip() != "") else f"Ex {n}"
                    variaveis_payload.append({"name": str(n).strip(), "example": str(ex_final).strip()})

                with st.spinner("Enviando para aprovação..."):
                    res = create_template(nome, categoria, corpo, variaveis_payload)

                if res.status_code in [200, 201]:
                    st.session_state.exibir_sucesso = True
                    st.session_state.ultimo_nome_criado = nome
                    st.session_state.limpar_apos_sucesso = True
                    st.rerun()

                elif res.status_code == 400:
                    try:
                        erro_data = res.json()
                        lista_erros = erro_data.get('errors', {}).get('Content', [])  # Tenta pegar erros de conteúdo
                        erros_gerais = erro_data.get('errors', {})

                        if "VariableCannotBeAtTheBeginningOrEnd" in lista_erros:
                            st.error("❌ ERRO DE FORMATAÇÃO (WhatsApp):")
                            st.warning("O texto não pode começar ou terminar com variável {{n}}.")

                        # Tratamento específico para o erro que você teve agora
                        elif "Variables" in erros_gerais and "NumberOfVariablesIsNotTheSame" in erros_gerais[
                            "Variables"]:
                            st.error("❌ Erro de Quantidade: O número de variáveis no texto não bate com a tabela.")

                        else:
                            st.error("❌ Erro de Validação da API:")
                            st.json(erro_data)  # Mostra o JSON completo para facilitar debug
                    except:
                        st.error(f"❌ Erro 400: {res.text}")
                else:
                    st.error(f"❌ Erro inesperado ({res.status_code}): {res.text}")

# ==============================================================================
# 🚫 ABA 3: FECHAR CONVERSAS (Via Contatos)
# ==============================================================================
elif menu == "Fechar Conversas":
    st.header("🚫 Encerrar Atendimentos")
    st.info("Lista de contatos recentes. Selecione para fechar o chat.")

    if st.button("🔄 Atualizar Lista"):
        if 'lista_contatos' in st.session_state:
            del st.session_state['lista_contatos']
        st.rerun()

    # --- Carrega Contatos ---
    if 'lista_contatos' not in st.session_state:
        with st.spinner("Buscando contatos..."):
            st.session_state['lista_contatos'] = get_contacts()

    contatos = st.session_state['lista_contatos']

    if contatos:
        # Prepara os dados para exibir
        dados_tabela = []
        for c in contatos:
            # 1. PEGAR O ID (Fundamental para fechar)
            contact_id = c.get('id')

            # 2. PEGAR O TELEFONE (Correção: O campo no seu JSON é 'phoneNumber')
            telefone = c.get('phoneNumber') or c.get('identifier') or "-"

            # 3. PEGAR O NOME
            # Lógica: Se o nome for null, usamos o telefone como nome para identificar a pessoa
            raw_name = c.get('name') or c.get('pushName')
            if raw_name:
                nome_cliente = raw_name
            elif telefone != "-":
                nome_cliente = telefone # Usa o número se não tiver nome (Evita linha em branco)
            else:
                nome_cliente = "Desconhecido"

            # 4. DATA (Usamos a data de criação, pois lastMessageDate não vem nesse endpoint)
            last_date = c.get('createdAtUTC', '-')

            dados_tabela.append({
                "contact_id": contact_id,
                "Cliente": nome_cliente,
                "Telefone": telefone,
                "Última Mensagem": "-", # Esse endpoint não traz o conteúdo da mensagem
                "Data": last_date
            })

        df_chats = pd.DataFrame(dados_tabela)

        # Tratamento de Data Visual
        if "Data" in df_chats.columns:
            # Converte data UTC para formato brasileiro
            df_chats["Data"] = pd.to_datetime(df_chats["Data"], errors='coerce').dt.strftime('%d/%m/%Y %H:%M').fillna("-")

        # Mostra a Tabela
        st.markdown("👇 **Selecione um contato para finalizar o atendimento**")

        event_chat = st.dataframe(
            df_chats,
            width="stretch",
            selection_mode="single-row",
            on_select="rerun",
            hide_index=True,
            column_config={
                "contact_id": None  # Esconde o ID técnico
            }
        )

        # --- AÇÃO: ENCERRAR CHAT ---
        if len(event_chat.selection.rows) > 0:
            idx = event_chat.selection.rows[0]
            contato_selecionado = df_chats.iloc[idx]

            st.divider()
            st.markdown(f"### 👤 Cliente: {contato_selecionado['Cliente']}")
            st.markdown(f"📱 **Telefone:** {contato_selecionado['Telefone']}")

            # Botão de Confirmação
            col1, col2 = st.columns([1, 4])
            with col1:
                # Botão com chave única baseada no ID do contato
                if st.button("✅ Encerrar Chat", type="primary", key=f"btn_close_{contato_selecionado['contact_id']}"):
                    with st.spinner("Encerrando atendimento..."):

                        # Chama a função de fechar passando o ID do Contato
                        res = close_chat(contato_selecionado['contact_id'])

                        if res.status_code == 200 or res.status_code == 204:
                            st.success(f"Conversas de {contato_selecionado['Cliente']} encerradas!")
                            # Limpa cache para atualizar
                            del st.session_state['lista_contatos']
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Erro ao fechar: {res.text}")

    else:
        st.warning("Nenhum contato encontrado.")