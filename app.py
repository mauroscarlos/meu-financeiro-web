import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

# 1. Configuração da Conexão
@st.cache_resource # Isso evita que o app conecte ao banco toda hora, deixando-o mais rápido
def get_engine():
    try:
        url = st.secrets["connections"]["postgresql"]["url"]
        return create_engine(url)
    except:
        return None

engine = get_engine()

# 2. Interface Lateral
st.set_page_config(page_title="SGF PRO Web", layout="wide", page_icon="🛡️")
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/5501/5501375.png", width=100) # Ícone decorativo
st.sidebar.title("Configurações")
aba = st.sidebar.radio("Selecione a Aba:", ["📊 Dashboard", "💰 Receitas", "💸 Despesas", "📜 Histórico"])

# --- ABA RECEITAS ---
if aba == "💰 Receitas":
    st.header("Lançamento de Receita")
    with st.form("form_rec", clear_on_submit=True):
        col1, col2 = st.columns(2)
        data = col1.date_input("Data", datetime.now())
        valor = col2.number_input("Valor R$", min_value=0.0, format="%.2f")
        cat = st.selectbox("Categoria", ["Salário", "Vendas", "Investimentos", "Bônus", "Outros"])
        origem = st.text_input("Origem (Cliente)")
        
        if st.form_submit_button("SALVAR RECEITA"):
            df = pd.DataFrame([['Receita', data, cat, origem, valor]], 
                              columns=['tipo', 'data', 'categoria', 'origem_destino', 'valor'])
            df.to_sql('movimentacoes', engine, if_exists='append', index=False)
            st.success("Receita gravada com sucesso!")

# --- ABA DESPESAS ---
elif aba == "💸 Despesas":
    st.header("Lançamento de Despesa")
    with st.form("form_desp", clear_on_submit=True):
        col1, col2 = st.columns(2)
        data = col1.date_input("Data", datetime.now())
        valor = col2.number_input("Valor R$", min_value=0.0, format="%.2f")
        cat = st.selectbox("Categoria", ["Aluguel", "Energia", "Internet", "Mercado", "Combustível", "Lazer", "Outros"])
        destino = st.text_input("Destino (Fornecedor)")
        
        if st.form_submit_button("SALVAR DESPESA"):
            df = pd.DataFrame([['Despesa', data, cat, destino, valor]], 
                              columns=['tipo', 'data', 'categoria', 'origem_destino', 'valor'])
            df.to_sql('movimentacoes', engine, if_exists='append', index=False)
            st.error("Despesa registrada com sucesso!") # Usamos o vermelho para despesa

# --- ABA HISTÓRICO ---
elif aba == "📜 Histórico":
    st.header("Histórico de Movimentações")
    try:
        df_hist = pd.read_sql("SELECT * FROM movimentacoes ORDER BY data DESC", engine)
        if not df_hist.empty:
            # Formatação para ficar bonito
            df_hist['valor'] = df_hist['valor'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_hist, use_container_width=True)
            
            # Botão para baixar em Excel (Igual ao seu Desktop!)
            csv = df_hist.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Exportar Histórico (CSV)", csv, "historico.csv", "text/csv")
        else:
            st.info("Nenhum lançamento encontrado.")
    except:
        st.warning("O banco de dados está pronto, aguardando o primeiro lançamento.")

# --- DASHBOARD ---
else:
    st.header("Painel de Controle Financeiro")
    try:
        df = pd.read_sql("SELECT * FROM movimentacoes", engine)
        if not df.empty:
            rec = df[df['tipo'] == 'Receita']['valor'].sum()
            des = df[df['tipo'] == 'Despesa']['valor'].sum()
            saldo = rec - des
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Receitas Total", f"R$ {rec:,.2f}")
            m2.metric("Despesas Total", f"R$ {des:,.2f}")
            m3.metric("Saldo Líquido", f"R$ {saldo:,.2f}", delta=f"{saldo:,.2f}")
            
            st.subheader("Gastos por Categoria")
            df_despesas = df[df['tipo'] == 'Despesa']
            if not df_despesas.empty:
                st.bar_chart(df_despesas.groupby('categoria')['valor'].sum())
        else:
            st.info("Bem-vindo! Comece lançando suas receitas ou despesas nas abas laterais.")
    except:
        st.info("Inicie o sistema fazendo seu primeiro lançamento.")
