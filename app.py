import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- FUNÇÕES DE APOIO ---
def formatar_doc(doc):
    if not doc: return ""
    doc = "".join(filter(str.isdigit, str(doc)))
    if len(doc) == 11:
        return f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
    if len(doc) == 14:
        return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
    return doc

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="SGF PRO - Gestão Profissional", layout="wide", page_icon="🛡️")

@st.cache_resource
def get_engine():
    url = st.secrets["connections"]["postgresql"]["url"]
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

# --- FUNÇÃO DE ENVIO DE EMAIL ---
def enviar_email_boas_vindas(nome, email_destino, senha_provisoria):
    msg_corpo = f"<html><body><h2>Olá, {nome}! 👋</h2><p>Sua conta no <b>SGF PRO</b> foi criada...</p></body></html>"
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["email"]["usuario"]
        msg['To'] = email_destino
        msg['Subject'] = "🚀 Bem-vindo ao SGF PRO"
        msg.attach(MIMEText(msg_corpo, 'html'))
        server = smtplib.SMTP_SSL(st.secrets["email"]["smtp_server"], st.secrets["email"]["smtp_port"])
        server.login(st.secrets["email"]["usuario"], st.secrets["email"]["senha"])
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False

# --- SISTEMA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    # (Mantendo sua lógica de login intacta conforme solicitado)
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
                    st.session_state.logado = True
                    st.session_state.user_id = int(user_df.iloc[0]['id'])
                    st.session_state.user_nome = user_df.iloc[0]['nome']
                    st.session_state.user_nivel = user_df.iloc[0]['nivel']
                    st.rerun()
                else: st.error("Incorreto.")
    st.stop()

# --- INTERFACE PRINCIPAL ---
st.sidebar.title(f"Olá, {st.session_state.user_nome}!")
if st.sidebar.button("Sair"):
    st.session_state.clear()
    st.rerun()

opcoes_menu = ["📊 Dashboard", "👤 Cadastros", "📝 Lançamentos", "📜 Histórico"]
if st.session_state.user_nivel == 'admin': opcoes_menu.append("🛡️ Gestão de Usuários")
menu = st.sidebar.radio("Navegação", opcoes_menu)

# --- ABA CADASTROS ---
if menu == "👤 Cadastros":
    st.header("⚙️ Central de Cadastros")
    
    modo = st.radio("Gerenciar:", ["Categorias", "Fornecedores", "Origens"], horizontal=True)
    st.divider()

    if modo == "Categorias":
        with st.form("f_cat", clear_on_submit=True):
            c1, c2 = st.columns(2)
            t = c1.selectbox("Tipo", ["Receita", "Despesa"])
            d = c2.text_input("Descrição *")
            if st.form_submit_button("Salvar"):
                if d:
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO categorias (tipo, descricao, usuario_id) VALUES (:t, :d, :u)"),
                                     {"t": t, "d": d, "u": st.session_state.user_id})
                    st.rerun()

    elif modo == "Fornecedores":
        with st.form("f_forn", clear_on_submit=True):
            cnpj = st.text_input("CNPJ (Apenas números) *")
            raz = st.text_input("Razão Social *")
            if st.form_submit_button("Cadastrar Fornecedor"):
                doc = "".join(filter(str.isdigit, cnpj))
                if len(doc) == 14 and raz:
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO fornecedores (cnpj, razao_social, usuario_id) VALUES (:c, :r, :u)"),
                                     {"c": doc, "r": raz, "u": st.session_state.user_id})
                    st.rerun()

    elif modo == "Origens":
        with st.form("f_orig", clear_on_submit=True):
            nom = st.text_input("Nome da Origem (Cliente) *")
            if st.form_submit_button("Salvar Origem"):
                if nom:
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO origens (nome, usuario_id) VALUES (:n, :u)"),
                                     {"n": nom, "u": st.session_state.user_id})
                    st.rerun()

# --- ABA LANÇAMENTOS (OTIMIZADA) ---
elif menu == "📝 Lançamentos":
    st.header("📋 Lançamento Financeiro")
    tipo = st.radio("Tipo", ["Receita", "Despesa"], horizontal=True)
    
    # Busca Categorias
    cats = pd.read_sql(text("SELECT descricao FROM categorias WHERE usuario_id=:u AND tipo=:t"), 
                       engine, params={"u":st.session_state.user_id, "t":tipo})
    
    # Busca Contatos (Fornecedores ou Origens)
    if tipo == "Despesa":
        contatos = pd.read_sql(text("SELECT razao_social as nome FROM fornecedores WHERE usuario_id=:u"), 
                               engine, params={"u":st.session_state.user_id})
    else:
        contatos = pd.read_sql(text("SELECT nome FROM origens WHERE usuario_id=:u"), 
                               engine, params={"u":st.session_state.user_id})

    if cats.empty:
        st.warning("Cadastre categorias primeiro.")
    else:
        with st.form("f_mov", clear_on_submit=True):
            col1, col2 = st.columns(2)
            dt = col1.date_input("Data", datetime.now())
            ct = col2.selectbox("Categoria", cats['descricao'].tolist())
            
            col3, col4 = st.columns(2)
            vl = col3.number_input("Valor (R$)", min_value=0.0, step=0.01)
            # Agora é um Selectbox em vez de Text Input!
            lista_contatos = contatos['nome'].tolist() if not contatos.empty else ["Nenhum cadastrado"]
            orig = col4.selectbox("Origem/Destino", lista_contatos)
            
            if st.form_submit_button("Confirmar"):
                if vl > 0 and orig != "Nenhum cadastrado":
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO movimentacoes (tipo, valor, data, origem_destino, usuario_id, categoria_id)
                            VALUES (:t, :v, :d, :o, :u, (SELECT id FROM categorias WHERE descricao=:ct AND usuario_id=:u LIMIT 1))
                        """), {"t":tipo, "v":vl, "d":dt, "o":orig, "u":st.session_state.user_id, "ct":ct})
                    st.success("Lançado!")
                    st.rerun()

# --- ABA HISTÓRICO ---
elif menu == "📜 Histórico":
    st.header("📜 Histórico")
    df = pd.read_sql(text("SELECT data, tipo, origem_destino, valor FROM movimentacoes WHERE usuario_id=:u ORDER BY data DESC"), 
                     engine, params={"u":st.session_state.user_id})
    st.dataframe(df, use_container_width=True)

# --- GESTÃO DE USUÁRIOS ---
elif menu == "🛡️ Gestão de Usuários":
    # (Mantendo sua lógica de gestão de usuários)
    st.header("👥 Gestão de Usuários")
    df_users = pd.read_sql("SELECT * FROM usuarios ORDER BY id ASC", engine)
    st.dataframe(df_users, use_container_width=True)
