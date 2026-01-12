import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="SGF PRO - Gestão Profissional", layout="wide", page_icon="🛡️")

@st.cache_resource
def get_engine():
    url = st.secrets["connections"]["postgresql"]["url"]
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

# --- LÓGICA DE AUTO-CADASTRO (VIA LINK: ?modo=registro) ---
params = st.query_params
if "modo" in params and params["modo"] == "registro":
    st.markdown("<h2 style='text-align: center;'>📝 Criar Nova Conta</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("auto_registro"):
            n_nome = st.text_input("Nome Completo")
            n_email = st.text_input("E-mail")
            n_senha = st.text_input("Defina uma Senha", type="password")
            if st.form_submit_button("Finalizar Cadastro"):
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO usuarios (nome, email, senha, nivel, status) VALUES (:n, :e, :s, 'user', 'ativo')"),
                                 {"n": n_nome, "e": n_email, "s": n_senha})
                st.success("Conta criada com sucesso!")
        if st.button("⬅️ Voltar para Login"):
            st.query_params.clear()
            st.rerun()
    st.stop()

# --- SISTEMA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

# O placeholder deve ser criado ANTES do bloco if not logado
placeholder = st.empty()

if not st.session_state.logado:
    with placeholder.container(): # Tudo o que está aqui será apagado depois
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
                            st.error("❌ Sua conta está bloqueada.")
                        else:
                            # 1. Salva os dados na sessão
                            st.session_state.logado = True
                            st.session_state.user_id = int(user_df.iloc[0]['id'])
                            st.session_state.user_nome = user_df.iloc[0]['nome']
                            st.session_state.user_nivel = user_df.iloc[0]['nivel']
                            
                            # 2. LIMPA O CONTEÚDO DO PLACEHOLDER (Apaga o formulário da tela)
                            placeholder.empty()
                            
                            # 3. Reinicia o app já com a sessão logada
                            st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
    st.stop()

# --- INTERFACE PRINCIPAL ---
st.sidebar.title(f"Olá, {st.session_state.user_nome}!")
if st.sidebar.button("Sair"):
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

opcoes_menu = ["📊 Dashboard", "👤 Cadastros", "💰 Receitas", "💸 Despesas", "📜 Histórico"]
if st.session_state.user_nivel == 'admin':
    opcoes_menu.append("🛡️ Gestão de Usuários")

menu = st.sidebar.radio("Navegação", opcoes_menu)

# --- ABA GESTÃO DE USUÁRIOS (EXCLUSIVA ADMIN) ---
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- FUNÇÃO DE ENVIO DE EMAIL ---
def enviar_email_boas_vindas(nome, email_destino, senha_provisoria):
    msg_corpo = f"""
    <html>
        <body>
            <h2>Olá, {nome}! 👋</h2>
            <p>Sua conta no <b>SGF PRO</b> foi criada com sucesso pelo administrador.</p>
            <p><b>Seus dados de acesso:</b></p>
            <ul>
                <li><b>Link:</b> <a href="https://seu-app.streamlit.app">Acessar Sistema</a></li>
                <li><b>Usuário:</b> {email_destino}</li>
                <li><b>Senha:</b> {senha_provisoria}</li>
            </ul>
            <p><i>Recomendamos alterar sua senha após o primeiro login.</i></p>
        </body>
    </html>
    """
    
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["email"]["usuario"]
        msg['To'] = email_destino
        msg['Subject'] = "🚀 Bem-vindo ao SGF PRO - Seus dados de acesso"
        msg.attach(MIMEText(msg_corpo, 'html'))

        server = smtplib.SMTP_SSL(st.secrets["email"]["smtp_server"], st.secrets["email"]["smtp_port"])
        server.login(st.secrets["email"]["usuario"], st.secrets["email"]["senha"])
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False
        
# --- FUNÇÃO DE ENVIO DE EMAIL ---
def enviar_email_boas_vindas(nome, email_destino, senha_provisoria):
    msg_corpo = f"""
    <html>
        <body>
            <h2>Olá, {nome}! 👋</h2>
            <p>Sua conta no <b>SGF PRO</b> foi criada com sucesso pelo administrador.</p>
            <p><b>Seus dados de acesso:</b></p>
            <ul>
                <li><b>Link:</b> <a href="https://seu-app.streamlit.app">Acessar Sistema</a></li>
                <li><b>Usuário:</b> {email_destino}</li>
                <li><b>Senha:</b> {senha_provisoria}</li>
            </ul>
            <p><i>Recomendamos alterar sua senha após o primeiro login.</i></p>
        </body>
    </html>
    """
    
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["email"]["usuario"]
        msg['To'] = email_destino
        msg['Subject'] = "🚀 Bem-vindo ao SGF PRO - Seus dados de acesso"
        msg.attach(MIMEText(msg_corpo, 'html'))

        server = smtplib.SMTP_SSL(st.secrets["email"]["smtp_server"], st.secrets["email"]["smtp_port"])
        server.login(st.secrets["email"]["usuario"], st.secrets["email"]["senha"])
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False
        
    # 2. Listagem e Edição
    df_users = pd.read_sql("SELECT * FROM usuarios ORDER BY id ASC", engine)
    for i, row in df_users.iterrows():
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([3, 2, 1, 1, 1])
            c1.write(f"**{row['nome']}**\n{row['email']}")
            c2.write(f"Nível: `{row['nivel']}` | Status: `{row['status']}`")
            
            if c3.button("📝", key=f"ed_{row['id']}", help="Editar"):
                st.session_state[f"editando_{row['id']}"] = True
            
            txt_status = "🔓" if row['status'] == 'bloqueado' else "🔒"
            if c4.button(txt_status, key=f"st_{row['id']}", help="Bloquear"):
                novo = 'ativo' if row['status'] == 'bloqueado' else 'bloqueado'
                with engine.begin() as conn:
                    conn.execute(text("UPDATE usuarios SET status = :s WHERE id = :id"), {"s": novo, "id": row['id']})
                st.rerun()

            if c5.button("🗑️", key=f"del_{row['id']}", help="Excluir"):
                if row['id'] != st.session_state.user_id:
                    with engine.begin() as conn:
                        conn.execute(text("DELETE FROM usuarios WHERE id = :id"), {"id": row['id']})
                    st.rerun()
                else:
                    st.error("Você não pode se excluir!")

        # FORMULÁRIO DE EDIÇÃO (Alinhado fora das colunas, mas dentro do 'for')
        if st.session_state.get(f"editando_{row['id']}", False):
            with st.form(f"f_edit_{row['id']}"):
                e_nome = st.text_input("Nome", value=row['nome'])
                e_email = st.text_input("Email", value=row['email'])
                e_senha = st.text_input("Senha", value=row['senha'])
                e_nivel = st.selectbox("Nível", ["user", "admin"], index=0 if row['nivel']=='user' else 1)
                
                col_s1, col_s2 = st.columns(2)
                if col_s1.form_submit_button("Salvar Alterações"):
                    with engine.begin() as conn:
                        conn.execute(text("UPDATE usuarios SET nome=:n, email=:e, senha=:s, nivel=:nv WHERE id=:id"),
                                     {"n": e_nome, "e": e_email, "s": e_senha, "nv": e_nivel, "id": row['id']})
                    st.session_state[f"editando_{row['id']}"] = False
                    st.rerun()
                if col_s2.form_submit_button("Cancelar"):
                    st.session_state[f"editando_{row['id']}"] = False
                    st.rerun()
        st.divider()

# --- ABA HISTÓRICO ---
elif menu == "📜 Histórico":
    st.header("Histórico Financeiro")
    query_h = text("SELECT data, tipo, origem_destino, valor FROM movimentacoes WHERE usuario_id = :id ORDER BY data DESC")
    df_h = pd.read_sql(query_h, engine, params={"id": st.session_state.user_id})
    if not df_h.empty:
        st.dataframe(df_h, use_container_width=True)
        csv = df_h.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Exportar CSV/Excel", csv, "relatorio.csv", "text/csv")

# --- (Outras abas como Dashboard, Receitas, Despesas seguem a mesma lógica de filtro por user_id) ---








