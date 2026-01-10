import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# Conectar ao banco usando os Secrets que você configurou
def get_connection():
    url = st.secrets["connections"]["postgresql"]["url"]
    return create_engine(url)

engine = get_connection()

# Exemplo de como salvar dados (no lugar do antigo sqlite3)
def salvar_receita(tipo, data, categoria, valor):
    df = pd.DataFrame([[tipo, data, categoria, valor]], 
                      columns=['tipo', 'data', 'categoria', 'valor'])
    # Salva direto na tabela do Supabase
    df.to_sql('movimentacoes', engine, if_exists='append', index=False)

# Configuração da Página
st.set_page_config(page_title="SGF PRO Web", layout="wide")

# Funções de Banco de Dados
def init_db():
    conn = sqlite3.connect('financeiro.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS movimentacoes 
                      (id INTEGER PRIMARY KEY, tipo TEXT, data TEXT, categoria TEXT, valor REAL)''')
    conn.commit()
    return conn

conn = init_db()

# Título
st.title("🛡️ SGF PRO - Versão Web")

# Menu Lateral (Equivalente às suas abas)
aba = st.sidebar.selectbox("Navegação", ["Dashboard", "Receitas", "Despesas", "Histórico"])

if aba == "Receitas":
    st.header("💰 Lançar Receita")
    with st.form("form_receita"):
        data = st.date_input("Data")
        cat = st.selectbox("Categoria", ["Vendas", "Serviços", "Outros"])
        valor = st.number_input("Valor R$", min_value=0.0, format="%.2f")
        botao = st.form_submit_button("Salvar Receita")
        
        if botao:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO movimentacoes (tipo, data, categoria, valor) VALUES (?,?,?,?)",
                           ("Receita", str(data), cat, valor))
            conn.commit()
            st.success("Receita salva com sucesso!")

elif aba == "Dashboard":
    st.header("📊 Dashboard")
    df = pd.read_sql_query("SELECT * FROM movimentacoes", conn)
    
    if not df.empty:
        receitas = df[df['tipo'] == 'Receita']['valor'].sum()
        despesas = df[df['tipo'] == 'Despesa']['valor'].sum()
        saldo = receitas - despesas
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Receitas", f"R$ {receitas:,.2f}")
        col2.metric("Despesas", f"R$ {despesas:,.2f}")
        col3.metric("Saldo Atual", f"R$ {saldo:,.2f}", delta_color="normal")
        
        st.bar_chart(df.groupby('categoria')['valor'].sum())
    else:

        st.info("Nenhum dado lançado ainda.")
