import streamlit as st
import pandas as pd
import re
from api_functions import get_templates, get_open_chats, get_chat_messages, create_template

# Configuração da Página
st.set_page_config(page_title="Painel Umbler uTalk", page_icon="💬", layout="wide")

# Título e Sidebar
st.title("🤖 Gerenciador WhatsApp - Umbler uTalk")
menu = st.sidebar.radio("Navegação", ["Templates", "Chats (Inbox)", "Criar Template"])

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
                df_show = df[['label', 'status', 'category', 'id', 'content']]
                st.dataframe(df_show, use_container_width=True)

                # Métrica rápida
                st.metric("Total de Templates", len(templates))
            else:
                st.warning("Nenhum template encontrado.")

# ==============================================================================
# 💬 ABA 2: LEITURA DE CHATS (Estilo WhatsApp Web)
# ==============================================================================
elif menu == "Chats (Inbox)":
    st.header("📨 Caixa de Entrada (Chats Abertos)")

    # 1. Carrega a lista de chats na lateral
    col_lista, col_conversa = st.columns([1, 2])

    chats = get_open_chats()

    if not chats:
        st.info("Nenhum chat aberto no momento.")
    else:
        # Cria um dicionário para o Selectbox: "Nome Cliente (Tel)" -> ID
        opcoes_chat = {
            f"{c.get('contact', {}).get('name', 'Desc')} ({c.get('contact', {}).get('phoneNumber', '')})": c.get('id')
            for c in chats
        }

        with col_lista:
            st.subheader("Selecione um Cliente:")
            chat_selecionado_nome = st.radio("Lista:", list(opcoes_chat.keys()))
            chat_id = opcoes_chat[chat_selecionado_nome]

        # 2. Carrega as mensagens do chat selecionado
        with col_conversa:
            st.subheader(f"Conversa com {chat_selecionado_nome}")
            st.divider()

            # Container com scroll para mensagens
            chat_container = st.container(height=500)

            # Busca mensagens (Função que criamos antes)
            mensagens = get_chat_messages(chat_id)

            with chat_container:
                if not mensagens:
                    st.write("📭 Nenhuma mensagem carregada.")

                for msg in mensagens:
                    origem = msg.get('source')
                    texto = msg.get('content', '')
                    hora = msg.get('createdAtUTC', '')[11:16]

                    # Se for cliente, balão na esquerda (user). Se for Bot/Atendente, direita (assistant)
                    if origem == 'Contact':
                        with st.chat_message("user"):
                            st.write(f"**{hora}**: {texto}")
                    else:
                        avatar = "🤖" if origem == 'Bot' else "👨‍💻"
                        with st.chat_message("assistant", avatar=avatar):
                            st.write(f"**{hora}**: {texto}")

# ==============================================================================
# ✨ ABA 3: CRIAR NOVO TEMPLATE
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
            # Impede o envio se tiver erros óbvios
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
            # Verifica se termina com chaves, mesmo que tenha um ponto ou espaço depois.
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
                    st.balloons()  # Efeito visual de festa
                    st.json(res.json())  # Mostra os dados técnicos se quiser

                elif res.status_code == 400:
                    # Tenta ler o erro JSON
                    try:
                        erro_data = res.json()
                        lista_erros = erro_data.get('errors', {}).get('Content', [])

                        # Verifica se é o erro específico que você mandou
                        if "VariableCannotBeAtTheBeginningOrEnd" in lista_erros:
                            st.error("❌ ERRO DE FORMATAÇÃO (WhatsApp):")
                            st.warning("O WhatsApp rejeitou porque o texto começa ou termina com uma variável {{n}}.")
                            st.markdown(
                                "**Regra de Ouro:** Sempre coloque texto fixo antes da primeira variável e depois da última.")
                        else:
                            # Outro erro 400 qualquer
                            st.error("❌ Erro de Validação da API:")
                            st.code(res.text, language="json")

                    except:
                        st.error(f"❌ Erro 400: {res.text}")

                else:
                    st.error(f"❌ Erro inesperado ({res.status_code}): {res.text}")