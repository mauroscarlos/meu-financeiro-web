import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="SGF PRO - Admin", layout="wide", page_icon="🛡️")

@st.cache_resource
def get_engine():
    url = st.secrets["connections"]["postgresql"]["url"]
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

# --- LÓGICA DE AUTO-CADASTRO (VIA LINK EXTERNO) ---
# O link será: https://seu-app.streamlit.app/?modo=registro
params = st.query_params
if "modo" in params and params["modo"] == "registro":
    st.markdown("<h2 style='text-align: center;'>📝 Criar Nova Conta</h2>", unsafe_allow_html=True)
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            with st.form("auto_registro"):
                n_nome = st.text_input("Nome Completo")
                n_email = st.text_input("Seu melhor E-mail")
                n_senha = st.text_input("Defina uma Senha", type="password")
                if st.form_submit_button("Finalizar Cadastro"):
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO usuarios (nome, email, senha, nivel, status) VALUES (:n, :e, :s, 'user', 'ativo')"),
                                     {"n": n_nome, "e": n_email, "s": n_senha})
                    st.success("Conta criada! Agora você pode voltar ao login.")
            if st.button("⬅️ Voltar para Login"):
                st.query_params.clear()
                st.rerun()
    st.stop()

# --- SISTEMA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

placeholder = st.empty()

if not st.session_state.logado:
    with placeholder.container():
        st.markdown("<h2 style='text-align: center;'>🛡️ Acesso ao SGF PRO</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            with st.form("login"):
                email = st.text_input("Email")
                senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    query = text("SELECT * FROM usuarios WHERE email = :e AND senha = :s")
                    user_df = pd.read_sql(query, engine, params={"e": email, "s": senha})
                    
                    if not user_df.empty:
                        if user_df.iloc[0]['status'] == 'bloqueado':
                            st.error("❌ Sua conta está bloqueada. Entre em contato com o administrador.")
                        else:
                            st.session_state.logado = True
                            st.session_state.user_id = int(user_df.iloc[0]['id'])
                            st.session_state.user_nome = user_df.iloc[0]['nome']
                            st.session_state.user_nivel = user_df.iloc[0]['nivel']
                            placeholder.empty()
                            st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
    st.stop()

# --- INTERFACE PRINCIPAL ---
st.sidebar.title(f"Olá, {st.session_state.user_nome}!")
if st.sidebar.button("Sair"):
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

# Definindo as abas baseadas no nível de acesso
opcoes_menu = ["📊 Dashboard", "👤 Cadastros", "💰 Receitas", "💸 Despesas", "📜 Histórico"]
if st.session_state.user_nivel == 'admin':
    opcoes_menu.append("🛡️ Gestão de Usuários")

menu = st.sidebar.radio("Navegação", opcoes_menu)

# --- ABA GESTÃO DE USUÁRIOS (EXCLUSIVA ADMIN) ---
if menu == "🛡️ Gestão de Usuários":
    st.header("Gerenciamento de Membros")
    df_users = pd.read_sql("SELECT id, nome, email, nivel, status FROM usuarios ORDER BY id ASC", engine)
    
    for i, row in df_users.iterrows():
        with st.container():
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
            c1.write(f"**{row['nome']}**\n{row['email']}")
            c2.write(f"Nível: `{row['nivel']}` | Status: `{row['status']}`")
            
            # Botão Bloquear/Desbloquear
            txt_btn = "🔓 Desbloquear" if row['status'] == 'bloqueado' else "🔒 Bloquear"
            novo_status = 'ativo' if row['status'] == 'bloqueado' else 'bloqueado'
            if c3.button(txt_btn, key=f"block_{row['id']}"):
                with engine.begin() as conn:
                    conn.execute(text("UPDATE usuarios SET status = :s WHERE id = :id"), {"s": novo_status, "id": row['id']})
                st.rerun()
            
            # Botão Excluir
            if c4.button("🗑️ Excluir", key=f"del_{row['id']}"):
                with engine.begin() as conn:
                    conn.execute(text("DELETE FROM usuarios WHERE id = :id"), {"id": row['id']})
                st.rerun()
        st.divider()

# --- ABA HISTÓRICO (COM BOTÃO DE EXCEL) ---
elif menu == "📜 Histórico":
    st.header("Histórico de Movimentações")
    df_h = pd.read_sql(text("SELECT data, tipo, origem_destino, valor FROM movimentacoes WHERE usuario_id = :id ORDER BY data DESC"), 
                       engine, params={"id": st.session_state.user_id})
    if not df_h.empty:
        st.dataframe(df_h, use_container_width=True)
        csv = df_h.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Planilha (Excel/CSV)", csv, "meu_financeiro.csv", "text/csv")
    else:
        st.info("Nada por aqui ainda.")

# ... (Mantenha as abas de Dashboard, Cadastros, Receitas e Despesas do código anterior) ...
