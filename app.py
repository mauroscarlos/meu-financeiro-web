import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="SGF PRO - Gestão Profissional", layout="wide", page_icon="🛡️")

@st.cache_resource
def get_engine():
    url = st.secrets["connections"]["postgresql"]["url"]
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

# --- FUNÇÃO DE ENVIO DE EMAIL ---
def enviar_email_boas_vindas(nome, email_destino, senha_provisoria):
    msg_corpo = f"""
    <html>
        <body>
            <h2>Olá, {nome}! 👋</h2>
            <p>Sua conta no <b>SGF PRO</b> foi criada com sucesso pelo administrador.</p>
            <p><b>Seus dados de acesso:</b></p>
            <ul>
                <li><b>Link:</b> <a href="https://meu-financeiro-web-htaqqyp7igebzsdy6vymja.streamlit.app/">Acessar Sistema</a></li>
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

# --- LÓGICA DE AUTO-CADASTRO ---
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
                            st.error("❌ Sua conta está bloqueada.")
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

opcoes_menu = ["📊 Dashboard", "👤 Cadastros", "💰 Receitas", "💸 Despesas", "📜 Histórico"]
if st.session_state.user_nivel == 'admin':
    opcoes_menu.append("🛡️ Gestão de Usuários")

menu = st.sidebar.radio("Navegação", opcoes_menu)

# --- ABA GESTÃO DE USUÁRIOS (EXCLUSIVA ADMIN) ---
if menu == "🛡️ Gestão de Usuários":
    st.header("👥 Gerenciamento de Membros")
    with st.expander("➕ Adicionar Novo Usuário"):
        with st.form("add_manual", clear_on_submit=True):
            m_nome = st.text_input("Nome")
            m_email = st.text_input("Email")
            m_senha = st.text_input("Senha")
            m_nivel = st.selectbox("Nível", ["user", "admin"])
            if st.form_submit_button("Cadastrar e Notificar"):
                if m_nome and m_email and m_senha:
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO usuarios (nome, email, senha, nivel, status) VALUES (:n, :e, :s, :nv, 'ativo')"),
                                     {"n": m_nome, "e": m_email, "s": m_senha, "nv": m_nivel})
                    enviou = enviar_email_boas_vindas(m_nome, m_email, m_senha)
                    if enviou:
                        st.success(f"Usuário {m_nome} criado e e-mail enviado!")
                    else:
                        st.warning("Usuário criado, mas houve erro no envio do e-mail.")
                    st.rerun()
                else:
                    st.error("Preencha todos os campos.")

    st.divider()
    df_users = pd.read_sql("SELECT * FROM usuarios ORDER BY id ASC", engine)
    for i, row in df_users.iterrows():
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([3, 2, 1, 1, 1])
            c1.write(f"**{row['nome']}**\n{row['email']}")
            c2.write(f"Nível: `{row['nivel']}` | Status: `{row['status']}`")
            if c3.button("📝", key=f"ed_{row['id']}"):
                st.session_state[f"editando_{row['id']}"] = True
            
            txt_status = "🔓" if row['status'] == 'bloqueado' else "🔒"
            if c4.button(txt_status, key=f"st_{row['id']}"):
                novo = 'ativo' if row['status'] == 'bloqueado' else 'bloqueado'
                with engine.begin() as conn:
                    conn.execute(text("UPDATE usuarios SET status = :s WHERE id = :id"), {"s": novo, "id": row['id']})
                st.rerun()

            if c5.button("🗑️", key=f"del_{row['id']}"):
                if row['id'] != st.session_state.user_id:
                    with engine.begin() as conn:
                        conn.execute(text("DELETE FROM usuarios WHERE id = :id"), {"id": row['id']})
                    st.rerun()

            if st.session_state.get(f"editando_{row['id']}", False):
                with st.form(f"f_edit_{row['id']}"):
                    e_nome = st.text_input("Nome", value=row['nome'])
                    e_email = st.text_input("Email", value=row['email'])
                    e_senha = st.text_input("Senha", value=row['senha'])
                    e_nivel = st.selectbox("Nível", ["user", "admin"], index=0 if row['nivel']=='user' else 1)
                    col_s1, col_s2 = st.columns(2)
                    if col_s1.form_submit_button("Salvar"):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE usuarios SET nome=:n, email=:e, senha=:s, nivel=:nv WHERE id=:id"),
                                         {"n": e_nome, "e": e_email, "s": e_senha, "nv": e_nivel, "id": row['id']})
                        st.session_state[f"editando_{row['id']}"] = False
                        st.rerun()
                    if col_s2.form_submit_button("Cancelar"):
                        st.session_state[f"editando_{row['id']}"] = False
                        st.rerun()
        st.divider()

# --- ABA CADASTROS (CATEGORIAS) ---
elif menu == "👤 Cadastros":
    st.header("⚙️ Gestão de Categorias")
    
    # CSS AGRESSIVO para remover espaços e estilizar botões pequenos
    st.markdown("""
        <style>
            /* Remove espaço entre blocos verticais */
            [data-testid="stVerticalBlock"] > div {
                padding-top: 0rem !important;
                padding-bottom: 0rem !important;
                margin-top: -0.2rem !important;
            }
            /* Estiliza os botões para serem pequenos e com texto visível */
            .stButton button {
                height: 1.5rem !important;
                line-height: 1 !important;
                padding: 0px 5px !important;
                font-size: 0.8rem !important;
            }
            /* Remove a linha divisória padrão do Streamlit para economizar espaço */
            hr {
                margin-top: 0.2rem !important;
                margin-bottom: 0.2rem !important;
            }
        </style>
    """, unsafe_allow_html=True)

    with st.expander("➕ Adicionar Nova Categoria"):
        with st.form("form_categorias", clear_on_submit=True):
            col1, col2 = st.columns(2)
            tipo_cat = col1.selectbox("Tipo", ["Receita", "Despesa"])
            desc_cat = col2.text_input("Descrição (Ex: Telefone, Aluguel)")
            if st.form_submit_button("Salvar Categoria"):
                if desc_cat:
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO categorias (tipo, descricao, usuario_id) VALUES (:t, :d, :u)"),
                                     {"t": tipo_cat, "d": desc_cat, "u": st.session_state.user_id})
                    st.success("Categoria incluída!")
                    st.rerun()

    st.subheader("📋 Lista de Categorias")
    
    try:
        query_cat = text("SELECT * FROM categorias WHERE usuario_id = :u ORDER BY tipo DESC, descricao ASC")
        df_cat = pd.read_sql(query_cat, engine, params={"u": st.session_state.user_id})
    except:
        df_cat = pd.DataFrame()

    if not df_cat.empty:
        # Cabeçalho da "tabela" manual
        h1, h2, h3, h4 = st.columns([1, 3, 1, 1])
        h1.caption("TIPO")
        h2.caption("DESCRIÇÃO")
        h3.caption("AÇÃO")
        h4.caption("AÇÃO")
        st.divider()

        for i, row in df_cat.iterrows():
            # Proporções ajustadas para caber o texto nos botões
            c1, c2, c3, c4 = st.columns([1, 3, 1, 1]) 
            
            cor = "🟢" if row['tipo'] == 'Receita' else "🔴"
            c1.write(f"{cor} {row['tipo']}")
            c2.write(f"{row['descricao']}")
            
            # Botões com TEXTO agora
            if c3.button("Editar", key=f"ed_cat_{row['id']}"):
                st.session_state[f"edit_cat_{row['id']}"] = True
            
            if c4.button("Excluir", key=f"del_cat_{row['id']}"):
                with engine.begin() as conn:
                    conn.execute(text("DELETE FROM categorias WHERE id = :id"), {"id": row['id']})
                st.rerun()

            # Área de edição simplificada
            if st.session_state.get(f"edit_cat_{row['id']}", False):
                with st.form(f"f_edit_cat_{row['id']}"):
                    n_desc = st.text_input("Nova Descrição", value=row['descricao'])
                    b1, b2 = st.columns(2)
                    if b1.form_submit_button("Salvar"):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE categorias SET descricao=:d WHERE id=:id"),
                                         {"d": n_desc, "id": row['id']})
                        st.session_state[f"edit_cat_{row['id']}"] = False
                        st.rerun()
                    if b2.form_submit_button("X"):
                        st.session_state[f"edit_cat_{row['id']}"] = False
                        st.rerun()
            st.divider()
    else:
        st.info("Nenhuma categoria cadastrada.")
        
# --- ABA HISTÓRICO ---
elif menu == "📜 Histórico":
    st.header("Histórico Financeiro")
    try:
        query_h = text("SELECT data, tipo, origem_destino, valor FROM movimentacoes WHERE usuario_id = :id ORDER BY data DESC")
        df_h = pd.read_sql(query_h, engine, params={"id": st.session_state.user_id})
        if not df_h.empty:
            st.dataframe(df_h, use_container_width=True)
            csv = df_h.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Exportar CSV", csv, "relatorio.csv", "text/csv")
        else:
            st.info("Nenhum dado encontrado.")
    except:
        st.warning("Tabela de movimentações não encontrada.")





