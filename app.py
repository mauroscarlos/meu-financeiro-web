import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

# --- CONFIGURAÇÃO E CONEXÃO ---
st.set_page_config(page_title="SGF PRO Multi", layout="wide")

@st.cache_resource
def get_engine():
    url = st.secrets["connections"]["postgresql"]["url"]
    return create_engine(url)

engine = get_engine()

# --- SISTEMA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario_id = None

def tela_login():
    st.title("🛡️ SGF PRO - Login")
    with st.form("login"):
        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            # Verificação simples no banco
            user = pd.read_sql(f"SELECT * FROM usuarios WHERE email='{email}' AND senha='{senha}'", engine)
            if not user.empty:
                st.session_state.logado = True
                st.session_state.usuario_id = int(user.iloc[0]['id'])
                st.session_state.usuario_nome = user.iloc[0]['nome']
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")

if not st.session_state.logado:
    tela_login()
    st.stop()

# --- INTERFACE PRINCIPAL (SÓ APARECE SE LOGADO) ---
st.sidebar.title(f"Bem-vindo, {st.session_state.usuario_nome}")
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

aba = st.sidebar.radio("Navegação", ["📊 Dashboard", "📝 Cadastros", "💰 Receitas", "💸 Despesas", "📜 Histórico"])

# --- ABA CADASTROS (Clientes, Fornecedores, Categorias) ---
if aba == "📝 Cadastros":
    st.header("⚙️ Gestão de Cadastros")
    tipo_cad = st.selectbox("O que deseja cadastrar?", ["Cliente", "Fornecedor", "Categoria"])
    
    with st.form("cadastros", clear_on_submit=True):
        nome = st.text_input(f"Nome do {tipo_cad}")
        info_extra = st.text_input("Documento ou Descrição (Opcional)")
        
        if st.form_submit_button(f"Cadastrar {tipo_cad}"):
            # Criamos uma tabela única de 'cadastros' no banco para simplificar
            dados = pd.DataFrame([{
                'nome': nome, 
                'tipo': tipo_cad, 
                'info': info_extra,
                'usuario_id': st.session_state.usuario_id
            }])
            dados.to_sql('cadastros', engine, if_exists='append', index=False)
            st.success(f"{tipo_cad} salvo!")

# --- ABA RECEITAS E DESPESAS ---
elif aba in ["💰 Receitas", "💸 Despesas"]:
    tipo = "Receita" if aba == "💰 Receitas" else "Despesa"
    st.header(f"Lançamento de {tipo}")
    
    # BUSCA DINÂMICA (Só o que este usuário cadastrou)
    try:
        contatos = pd.read_sql(f"SELECT nome FROM cadastros WHERE usuario_id={st.session_state.usuario_id}", engine)['nome'].tolist()
    except:
        contatos = ["Geral"]

    with st.form(f"form_{tipo}", clear_on_submit=True):
        col1, col2 = st.columns(2)
        data = col1.date_input("Data", datetime.now())
        valor = col2.number_input("Valor R$", min_value=0.0, format="%.2f")
        entidade = st.selectbox("Selecionar Cliente/Fornecedor", contatos)
        obs = st.text_area("Observações")
        
        if st.form_submit_button(f"Salvar {tipo}"):
            df = pd.DataFrame([{
                'tipo': tipo, 'data': data, 'valor': valor, 
                'origem_destino': entidade, 'usuario_id': st.session_state.usuario_id
            }])
            df.to_sql('movimentacoes', engine, if_exists='append', index=False)
            st.success(f"{tipo} registrada!")

# --- HISTÓRICO FILTRADO ---
elif aba == "📜 Histórico":
    st.header("Seus Lançamentos")
    df = pd.read_sql(f"SELECT data, tipo, origem_destino, valor FROM movimentacoes WHERE usuario_id={st.session_state.usuario_id}", engine)
    st.dataframe(df, use_container_width=True)
