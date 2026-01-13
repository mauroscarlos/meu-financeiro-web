import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

opcoes_menu = ["📊 Dashboard", "👤 Cadastros", "📝 Lançamentos", "📜 Histórico"]
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

# --- ABA CADASTROS (CORREÇÃO DEFINITIVA DE INDENTAÇÃO) ---
elif menu == "👤 Cadastros":
    st.header("⚙️ Central de Cadastros")
    
    modo_cadastro = st.radio(
        "O que deseja gerenciar?", 
        ["Categorias", "Fornecedores", "Origens de Receita"],
        horizontal=True
    )
    
    st.divider() # Esta é a linha 216 que estava dando erro

    if modo_cadastro == "Categorias":
        with st.expander("➕ Nova Categoria", expanded=True):
            with st.form("form_cat", clear_on_submit=True):
                c1, c2 = st.columns(2)
                t_cat = c1.selectbox("Tipo", ["Receita", "Despesa"])
                d_cat = c2.text_input("Descrição *")
                if st.form_submit_button("Salvar"):
                    if d_cat:
                        with engine.begin() as conn:
                            conn.execute(text("INSERT INTO categorias (tipo, descricao, usuario_id) VALUES (:t, :d, :u)"),
                                         {"t": t_cat, "d": d_cat, "u": st.session_state.user_id})
                        st.rerun()
                    else:
                        st.error("Campo obrigatório!")
        try:
            df_cat = pd.read_sql(text("SELECT * FROM categorias WHERE usuario_id = :u"), engine, params={"u": st.session_state.user_id})
            st.dataframe(df_cat, use_container_width=True)
        except:
            st.info("Tabela de categorias não encontrada.")

    elif modo_cadastro == "Fornecedores":
        with st.expander("➕ Novo Fornecedor", expanded=True):
            with st.form("form_forn", clear_on_submit=True):
                cnpj = st.text_input("CNPJ *", placeholder="Apenas números")
                razao = st.text_input("Razão Social *")
                f1, f2 = st.columns(2)
                email_f = f1.text_input("E-mail *")
                tel_f = f2.text_input("Telefone *")
                if st.form_submit_button("Cadastrar"):
                    doc_limpo = "".join(filter(str.isdigit, cnpj))
                    if all([doc_limpo, razao, email_f, tel_f]) and len(doc_limpo) == 14:
                        with engine.begin() as conn:
                            conn.execute(text("INSERT INTO fornecedores (cnpj, razao_social, email, telefone, usuario_id) VALUES (:c, :r, :e, :t, :u)"),
                                         {"c": doc_limpo, "r": razao, "e": email_f, "t": tel_f, "u": st.session_state.user_id})
                        st.rerun()
                    else:
                        st.error("Preencha todos os campos (CNPJ deve ter 14 números).")
        try:
            df_forn = pd.read_sql(text("SELECT * FROM fornecedores WHERE usuario_id = :u"), engine, params={"u": st.session_state.user_id})
            if not df_forn.empty:
                df_forn['cnpj'] = df_forn['cnpj'].apply(formatar_doc)
                st.dataframe(df_forn, use_container_width=True)
        except:
            st.info("Tabela fornecedores não encontrada.")

    elif modo_cadastro == "Origens de Receita":
        with st.expander("➕ Nova Origem", expanded=True):
            with st.form("form_orig", clear_on_submit=True):
                nome_o = st.text_input("Nome da Origem *")
                o1, o2 = st.columns(2)
                t_doc = o1.selectbox("Documento", ["CPF", "CNPJ"])
                n_doc = o2.text_input(f"Número do {t_doc} *")
                o3, o4 = st.columns(2)
                email_o = o3.text_input("E-mail *")
                tel_o = o4.text_input("Telefone *")
                if st.form_submit_button("Salvar"):
                    doc_limpo = "".join(filter(str.isdigit, n_doc))
                    if all([nome_o, doc_limpo, email_o, tel_o]):
                        with engine.begin() as conn:
                            conn.execute(text("INSERT INTO origens (nome, tipo_documento, documento, email, telefone, usuario_id) VALUES (:n, :td, :d, :e, :t, :u)"),
                                         {"n": nome_o, "td": t_doc, "d": doc_limpo, "e": email_o, "t": tel_o, "u": st.session_state.user_id})
                        st.rerun()
                    else:
                        st.error("Preencha todos os campos!")
        try:
            df_orig = pd.read_sql(text("SELECT * FROM origens WHERE usuario_id = :u"), engine, params={"u": st.session_state.user_id})
            if not df_orig.empty:
                df_orig['documento'] = df_orig['documento'].apply(formatar_doc)
                st.dataframe(df_orig, use_container_width=True)
        except:
            st.info("Tabela origens não encontrada.")

# --- ABA LANÇAMENTOS (UNIFICADA) ---
elif menu == "📝 Lançamentos":
    st.header("📋 Lançamento Financeiro")
    
    # Seletor de Tipo
    tipo_mov = st.radio("Tipo de Movimentação", ["Receita", "Despesa"], horizontal=True)
    
    # Busca categorias do tipo selecionado
    try:
        query_cat = text("SELECT id, descricao FROM categorias WHERE usuario_id = :u AND tipo = :t ORDER BY descricao ASC")
        df_cat = pd.read_sql(query_cat, engine, params={"u": st.session_state.user_id, "t": tipo_mov})
    except:
        df_cat = pd.DataFrame()

    if df_cat.empty:
        st.warning(f"⚠️ Nenhuma categoria de {tipo_mov} encontrada. Cadastre-as em '👤 Cadastros'.")
    else:
        with st.form("form_lancamento", clear_on_submit=True):
            col1, col2 = st.columns(2)
            data_mov = col1.date_input("Data", datetime.now())
            cat_mov = col2.selectbox("Categoria", df_cat['descricao'].tolist())
            
            col3, col4 = st.columns(2)
            valor_mov = col3.number_input("Valor (R$)", min_value=0.0, step=0.01)
            origem_mov = col4.text_input("Origem/Destino (Ex: Cliente, Fornecedor)")
            
            if st.form_submit_button("Lançar"):
                if valor_mov > 0:
                    with engine.begin() as conn:
                        # Buscamos o ID da categoria baseado na descrição escolhida
                        cat_id_query = text("SELECT id FROM categorias WHERE descricao = :d AND usuario_id = :u LIMIT 1")
                        res = conn.execute(cat_id_query, {"d": cat_mov, "u": st.session_state.user_id}).fetchone()
                        
                        if res:
                            conn.execute(text("""
                                INSERT INTO movimentacoes (tipo, categoria_id, valor, data, origem_destino, usuario_id) 
                                VALUES (:t, :cid, :v, :d, :o, :u)
                            """), {
                                "t": tipo_mov, "cid": res[0], "v": valor_mov, 
                                "d": data_mov, "o": origem_mov, "u": st.session_state.user_id
                            })
                            st.success("Lançamento realizado!")
                            st.rerun()
                else:
                    st.error("O valor deve ser maior que zero.")

    st.divider()
    st.subheader("⏱️ Últimos Lançamentos")
    
    # BLOCO COM PROTEÇÃO CONTRA O ERRO DE SQL
    try:
        query_resumo = text("""
            SELECT m.data, m.tipo, c.descricao as categoria, m.origem_destino, m.valor 
            FROM movimentacoes m
            LEFT JOIN categorias c ON m.categoria_id = c.id
            WHERE m.usuario_id = :u
            ORDER BY m.data DESC LIMIT 5
        """)
        df_resumo = pd.read_sql(query_resumo, engine, params={"u": st.session_state.user_id})
        
        if not df_resumo.empty:
            st.dataframe(df_resumo, use_container_width=True)
        else:
            st.info("Nenhuma movimentação encontrada.")
    except Exception as e:
        st.info("As movimentações aparecerão aqui assim que a tabela for configurada no Supabase.")
        
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




















