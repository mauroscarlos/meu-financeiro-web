import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="SGF PRO - Gestão", layout="wide", page_icon="🛡️")

# --- CONEXÃO COM O BANCO ---
@st.cache_resource
def get_engine():
    url = st.secrets["connections"]["postgresql"]["url"]
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

# --- CONTROLE DE SESSÃO (LOGIN) ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

def tela_login():
    st.markdown("<h2 style='text-align: center;'>🛡️ Acesso ao SGF PRO</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login"):
            email = st.text_input("Email")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar no Sistema"):
                query = f"SELECT * FROM usuarios WHERE email = '{email}' AND senha = '{senha}'"
                user_df = pd.read_sql(query, engine)
                if not user_df.empty:
                    st.session_state.logado = True
                    st.session_state.user_id = int(user_df.iloc[0]['id'])
                    st.session_state.user_nome = user_df.iloc[0]['nome']
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

if not st.session_state.logado:
    tela_login()
    st.stop()

# --- INTERFACE PRINCIPAL ---
st.sidebar.title(f"Olá, {st.session_state.user_nome}!")
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "👤 Clientes e Fornecedores", "💰 Receitas", "💸 Despesas", "📜 Histórico"])

# --- ABA DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("Painel Financeiro")
    df = pd.read_sql(f"SELECT * FROM movimentacoes WHERE usuario_id = {st.session_state.user_id}", engine)
    
    if not df.empty:
        rec = df[df['tipo'] == 'Receita']['valor'].sum()
        des = df[df['tipo'] == 'Despesa']['valor'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Receitas", f"R$ {rec:,.2f}")
        c2.metric("Total Despesas", f"R$ {des:,.2f}")
        c3.metric("Saldo Atual", f"R$ {rec - des:,.2f}")
        
        st.subheader("Resumo por Categoria")
        st.bar_chart(df.groupby('categoria')['valor'].sum())
    else:
        st.info("Nenhum dado lançado ainda. Vá para as abas de Receitas ou Despesas!")

# --- ABA CADASTROS (CLIENTES/FORNECEDORES) ---
elif menu == "👤 Clientes e Fornecedores":
    st.header("Cadastro de Contatos")
    with st.form("cad_contato", clear_on_submit=True):
        tipo = st.selectbox("Tipo", ["Cliente", "Fornecedor", "Categoria"])
        nome = st.text_input("Nome completo / Descrição")
        if st.form_submit_button("Salvar Cadastro"):
            new_cad = pd.DataFrame([{'tipo': tipo, 'nome': nome, 'usuario_id': st.session_state.user_id}])
            new_cad.to_sql('cadastros', engine, if_exists='append', index=False)
            st.success(f"{tipo} cadastrado com sucesso!")

# --- ABA RECEITAS E DESPESAS ---
elif menu in ["💰 Receitas", "💸 Despesas"]:
    tipo_mov = "Receita" if menu == "💰 Receitas" else "Despesa"
    st.header(f"Lançar {tipo_mov}")
    
    # Busca clientes/fornecedores cadastrados por esse usuário
    try:
        opcoes = pd.read_sql(f"SELECT nome FROM cadastros WHERE usuario_id = {st.session_state.user_id}", engine)['nome'].tolist()
    except:
        opcoes = ["Geral"]

    with st.form("lancamento", clear_on_submit=True):
        col1, col2 = st.columns(2)
        data = col1.date_input("Data")
        valor = col2.number_input("Valor R$", min_value=0.0, format="%.2f")
        cat = st.selectbox("Categoria/Contato", opcoes)
        
        if st.form_submit_button(f"Confirmar {tipo_mov}"):
            new_mov = pd.DataFrame([{
                'tipo': tipo_mov, 'data': data, 'categoria': 'Geral', 
                'valor': valor, 'origem_destino': cat, 'usuario_id': st.session_state.user_id
            }])
            new_mov.to_sql('movimentacoes', engine, if_exists='append', index=False)
            st.success(f"{tipo_mov} salva!")

# --- ABA HISTÓRICO ---
elif menu == "📜 Histórico":
    st.header("Todas as Movimentações")
    df_h = pd.read_sql(f"SELECT data, tipo, origem_destino, valor FROM movimentacoes WHERE usuario_id = {st.session_state.user_id} ORDER BY data DESC", engine)
    st.table(df_h)
