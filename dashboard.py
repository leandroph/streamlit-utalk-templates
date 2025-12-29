import streamlit as st
import pandas as pd
import re
from api_functions import get_templates, create_template, delete_template

# Configuração da Página
st.set_page_config(page_title="Painel Umbler uTalk", page_icon="💬", layout="wide")

# Título e Sidebar
st.title("🤖 Gerenciador WhatsApp - Umbler uTalk")

# MENU: Adicionamos key="navegacao" para controle via código
menu = st.sidebar.radio("Navegação", ["Templates", "Criar Template"], key="navegacao")


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
    # Nota: st.button ainda aceita use_container_width na maioria das versões,
    # mas se der aviso nele também, pode remover o parâmetro.
    if st.button("✏️ Editar / Usar como Modelo", type="primary", use_container_width=True):

        # 1. Prepara as variáveis
        var_str = ""
        variaveis = item.get('variables')
        if isinstance(variaveis, list):
            lista_nomes = [v.get('name') for v in variaveis if v.get('name')]
            var_str = ", ".join(lista_nomes)

        # 2. Preenche memória
        st.session_state['form_nome'] = item['label']
        st.session_state['form_cat'] = item.get('category', 'MARKETING')
        st.session_state['form_corpo'] = item.get('content', '')
        st.session_state['form_vars'] = var_str

        # 3. Muda a aba
        st.session_state.navegacao = "Criar Template"
        st.rerun()

    st.divider()

    st.markdown("### 📝 Mensagem Completa")
    content = item.get('content', '')
    st.code(content, language="markdown")

    # Exibição de Variáveis
    variaveis = item.get('variables')
    if isinstance(variaveis, list) and len(variaveis) > 0:
        st.divider()
        st.markdown("### 🧩 Variáveis Configuradas")
        df_vars = pd.DataFrame(variaveis)
        if 'name' in df_vars.columns:
            cols_show = {'name': 'Variável', 'example': 'Exemplo de Conteúdo'}
            cols_existentes = [c for c in cols_show.keys() if c in df_vars.columns]

            # CORREÇÃO 1: width="stretch"
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

    # --- 1. LÓGICA DE LIMPEZA E EXIBIÇÃO DE MENSAGEM ---
    if st.session_state.get('limpar_apos_sucesso'):
        st.session_state.form_nome = ""
        st.session_state.form_corpo = ""
        st.session_state.form_vars = ""
        st.session_state.limpar_apos_sucesso = False

    if st.session_state.get('exibir_sucesso'):
        nome_sucesso = st.session_state.get('ultimo_nome_criado', 'Template')
        st.success(f"✅ Template '{nome_sucesso}' criado com sucesso!")
        st.balloons()
        st.session_state.exibir_sucesso = False

        # --- 2. INICIALIZAÇÃO SEGURA ---
    if 'form_nome' not in st.session_state: st.session_state.form_nome = ""
    if 'form_corpo' not in st.session_state: st.session_state.form_corpo = ""
    if 'form_vars' not in st.session_state: st.session_state.form_vars = ""

    opcoes_cat = ["UTILITY", "MARKETING", "AUTHENTICATION"]
    if 'form_cat' not in st.session_state or st.session_state.form_cat not in opcoes_cat:
        st.session_state.form_cat = "MARKETING"

    # --- 3. LÓGICA DE PREENCHIMENTO AUTOMÁTICO ---
    if 'edit_data' in st.session_state:
        dados = st.session_state['edit_data']
        st.session_state.form_nome = dados['nome']
        st.session_state.form_cat = dados['categoria']
        st.session_state.form_corpo = dados['corpo']

        if dados['variaveis']:
            lista_nomes = [v.get('name') for v in dados['variaveis']]
            st.session_state.form_vars = ", ".join(lista_nomes)

        st.info(f"✏️ Editando cópia de: **{dados['nome']}**. Altere o nome se quiser criar um novo.")
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
        var_str = st.text_input("Liste as variáveis separadas por vírgula", key="form_vars")

        enviar = st.form_submit_button("🚀 Criar / Atualizar Template")

        if enviar:
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

            if not erro_encontrado:
                variaveis_payload = []
                if var_str:
                    nomes_vars = [v.strip() for v in var_str.split(',')]
                    for n in nomes_vars:
                        variaveis_payload.append({"name": n, "example": f"Ex {n}"})

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
                        lista_erros = erro_data.get('errors', {}).get('Content', [])
                        if "VariableCannotBeAtTheBeginningOrEnd" in lista_erros:
                            st.error("❌ ERRO DE FORMATAÇÃO (WhatsApp):")
                            st.warning("O texto não pode começar ou terminar com variável {{n}}.")
                        else:
                            st.error("❌ Erro de Validação da API:")
                            st.code(res.text, language="json")
                    except:
                        st.error(f"❌ Erro 400: {res.text}")
                else:
                    st.error(f"❌ Erro inesperado ({res.status_code}): {res.text}")