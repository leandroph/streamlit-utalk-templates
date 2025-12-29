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

# ==============================================================================
# 📄 ABA 1: LISTAR TEMPLATES
# ==============================================================================
if menu == "Templates":
    st.header("📂 Templates Cadastrados")

    if st.button("🔄 Atualizar Lista"):
        with st.spinner("Baixando templates..."):
            templates = get_templates()

            if templates:
                # Criando um DataFrame bonito para exibir
                df = pd.DataFrame(templates)
                # Selecionando colunas úteis
                # Proteção caso alguma coluna não venha na API
                cols = ['label', 'status', 'category', 'id', 'content']
                available_cols = [c for c in cols if c in df.columns]

                df_show = df[available_cols]
                st.dataframe(df_show, use_container_width=True)

                # Métrica rápida
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