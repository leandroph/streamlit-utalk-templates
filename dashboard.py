import streamlit as st
import pandas as pd
import re
from api_functions import get_templates, create_template

# Configuração da Página
st.set_page_config(page_title="Painel Umbler uTalk", page_icon="💬", layout="wide")

# Título e Sidebar
st.title("🤖 Gerenciador WhatsApp - Umbler uTalk")
# MENU EDITADO: Removemos a opção de Chats
menu = st.sidebar.radio("Navegação", ["Templates", "Criar Template"])


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
    st.markdown("### 📝 Mensagem Completa")
    content = item.get('content', '')
    st.code(content, language="markdown")

    # --- 🆕 EXIBIÇÃO DE VARIÁVEIS ---
    # Tenta pegar a lista de variáveis do item
    # (Usa .get para não quebrar se a coluna não existir)
    variaveis = item.get('variables')

    # Verifica se é uma lista válida e se tem conteúdo
    if isinstance(variaveis, list) and len(variaveis) > 0:
        st.divider()
        st.markdown("### 🧩 Variáveis Configuradas")

        # Cria um DataFramezinho para mostrar bonito na tela
        df_vars = pd.DataFrame(variaveis)

        # Filtra colunas para mostrar só o que interessa
        if 'name' in df_vars.columns:
            # Renomeia para ficar em português
            cols_show = {'name': 'Variável', 'example': 'Exemplo de Conteúdo'}
            # Garante que só pega colunas que existem
            cols_existentes = [c for c in cols_show.keys() if c in df_vars.columns]

            st.dataframe(
                df_vars[cols_existentes].rename(columns=cols_show),
                hide_index=True,
                use_container_width=True
            )
        else:
            # Se a estrutura for diferente do esperado, mostra o JSON cru
            st.json(variaveis)

    elif "{{" in str(content):
        # Fallback: Se tem {{ }} no texto mas a API não mandou a lista
        st.divider()
        st.warning("⚠️ Variáveis detectadas no texto, mas os detalhes técnicos não foram retornados.")

# ... (Configuração da página, Título e Menu) ...

# ==============================================================================
# 📄 ABA 1: LISTAR TEMPLATES (COM CACHE DE SESSÃO)
# ==============================================================================
if menu == "Templates":
    st.header("📂 Templates Cadastrados")

    # Botão de Forçar Atualização
    # Se clicar aqui, limpamos a memória para ele baixar de novo
    if st.button("🔄 Atualizar Lista"):
        if 'lista_templates' in st.session_state:
            del st.session_state['lista_templates']
        st.rerun()

    # --- LÓGICA INTELIGENTE (SÓ BAIXA SE NÃO TIVER NA MEMÓRIA) ---
    if 'lista_templates' not in st.session_state:
        with st.spinner("Baixando templates da API... (Aguarde)"):
            # Baixa e salva na sessão
            st.session_state['lista_templates'] = get_templates()

    # Recupera os dados da memória (Instantâneo, sem loading!)
    templates = st.session_state['lista_templates']

    if templates:
        df = pd.DataFrame(templates)

        # 1. TRATAMENTO E ORDENAÇÃO
        if 'createdAtUTC' in df.columns:
            df['createdAtUTC'] = pd.to_datetime(df['createdAtUTC'], format='mixed')
            df = df.sort_values(by='createdAtUTC', ascending=False)

        # Resetar o índice para garantir a seleção correta
        df = df.reset_index(drop=True)

        # 2. PREPARAÇÃO VISUAL
        cols_preferidas = ['label', 'status', 'category', 'createdAtUTC', 'id', 'content']
        cols_finais = [c for c in cols_preferidas if c in df.columns]
        df_show = df[cols_finais]

        if 'createdAtUTC' in df_show.columns:
            df_show['createdAtUTC'] = df_show['createdAtUTC'].dt.strftime('%d/%m/%Y %H:%M')

        # 3. TABELA INTERATIVA
        st.markdown("👇 **Clique em uma linha para ver os detalhes**")

        event = st.dataframe(
            df_show,
            use_container_width=True,
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

    with st.form("form_template"):
        nome = st.text_input("Nome do Template (minúsculo, sem espaços)", placeholder="ex: lembrete_consulta_v1")
        categoria = st.selectbox("Categoria", ["UTILITY", "MARKETING", "AUTHENTICATION"])

        corpo = st.text_area("Mensagem", height=150,
                             placeholder="Olá {{1}}, seu agendamento para {{2}} está confirmado.")

        st.info("💡 Dica: Não comece nem termine a frase com variáveis {{n}}.")

        # Gerenciador de Variáveis Simples
        st.subheader("Variáveis")
        var_str = st.text_input("Liste as variáveis separadas por vírgula (ex: Nome, Data)",
                                help="Isso vai gerar os exemplos automaticamente")

        enviar = st.form_submit_button("🚀 Criar Template")

        if enviar:
            # --- 1. VALIDAÇÃO LOCAL (PREVENTIVA) ---
            erro_encontrado = False

            # Verifica campos vazios
            if not nome or not corpo:
                st.error("❌ Preencha o Nome e a Mensagem.")
                erro_encontrado = True

            # REGRA 1: Não começar com {{
            if corpo.strip().startswith("{{"):
                st.error("🚫 O texto NÃO pode começar com uma variável.")
                st.info("💡 Correção: Adicione uma saudação antes. Ex: 'Olá {{1}}...'")
                erro_encontrado = True

            # REGRA 2: Não terminar com }} (usa Regex para ignorar pontuação final simples)
            if re.search(r"}}\W*$", corpo.strip()):
                st.error("🚫 O texto NÃO pode terminar com uma variável.")
                st.info("💡 Correção: Adicione uma instrução depois. Ex: '...código {{1}}. Não compartilhe.'")
                erro_encontrado = True

            # Se passou na validação local, envia para a API
            if not erro_encontrado:

                # Prepara as variáveis
                variaveis_payload = []
                if var_str:
                    nomes_vars = [v.strip() for v in var_str.split(',')]
                    for n in nomes_vars:
                        variaveis_payload.append({"name": n, "example": f"Ex {n}"})

                with st.spinner("Enviando para aprovação..."):
                    res = create_template(nome, categoria, corpo, variaveis_payload)

                # --- 2. TRATAMENTO DA RESPOSTA (REATIVO) ---
                if res.status_code in [200, 201]:
                    st.success(f"✅ Template '{nome}' criado com sucesso!")
                    st.balloons()
                    st.json(res.json())

                elif res.status_code == 400:
                    try:
                        erro_data = res.json()
                        lista_erros = erro_data.get('errors', {}).get('Content', [])

                        if "VariableCannotBeAtTheBeginningOrEnd" in lista_erros:
                            st.error("❌ ERRO DE FORMATAÇÃO (WhatsApp):")
                            st.warning("O WhatsApp rejeitou porque o texto começa ou termina com uma variável {{n}}.")
                            st.markdown(
                                "**Regra de Ouro:** Sempre coloque texto fixo antes da primeira variável e depois da última.")
                        else:
                            st.error("❌ Erro de Validação da API:")
                            st.code(res.text, language="json")
                    except:
                        st.error(f"❌ Erro 400: {res.text}")

                else:
                    st.error(f"❌ Erro inesperado ({res.status_code}): {res.text}")