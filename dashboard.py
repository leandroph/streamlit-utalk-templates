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


# ... (início do código, imports, etc...)

# ==============================================================================
# 🆕 FUNÇÃO PARA A JANELA MODAL (Coloque isso logo após os imports ou antes do menu)
# ==============================================================================
@st.dialog("Detalhes do Template")
def show_template_details(item):
    st.subheader(f"{item['label']}")

    # Status com cor
    cor_status = "green" if item['status'] == "APPROVED" else "red" if item['status'] == "REJECTED" else "orange"
    st.markdown(f"**Status:** :{cor_status}[{item['status']}]")
    st.markdown(f"**Categoria:** {item['category']}")
    st.markdown(f"**ID:** `{item['id']}`")

    st.divider()
    st.markdown("### 📝 Mensagem Completa")
    # Usa code block para facilitar a leitura e cópia
    st.code(item['content'], language="markdown")

    # Mostra variáveis se existirem na string (só visualmente)
    if "{{" in item['content']:
        st.info("ℹ️ Este template contém variáveis dinâmicas.")


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