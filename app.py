import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

# 1. Configuração da Conexão Permanente (Supabase)
def get_engine():
    try:
        # Busca a URL que você colou nos Secrets do Streamlit
        url = st.secrets["connections"]["postgresql"]["url"]
        return create_engine(url)
    except Exception as e:
        st.error("Erro ao conectar ao banco de dados. Verifique os Secrets.")
        return None

engine = get_engine()

# 2. Interface da Aplicação
st.set_page_config(page_title="SGF PRO Web", layout="wide")
st.title("🛡️ SGF PRO - Gestão Financeira Permanente")

aba = st.sidebar.selectbox("Navegação", ["Dashboard", "Receitas", "Despesas", "Histórico"])

if aba == "Receitas":
    st.header("💰 Lançar Receita")
    with st.form("form_receita", clear_on_submit=True):
        data = st.date_input("Data", datetime.now())
        cat = st.selectbox("Categoria", ["Salário", "Vendas", "Investimentos", "Outros"])
        origem = st.text_input("Origem (Cliente)")
        valor = st.number_input("Valor R$", min_value=0.0, format="%.2f")
        botao = st.form_submit_button("Salvar Receita")
        
        if botao and engine:
            # Criamos um DataFrame com o novo lançamento
            novo_dado = pd.DataFrame([{
                'tipo': 'Receita',
                'data': data,
                'categoria': cat,
                'origem_destino': origem,
                'valor': valor
            }])
            # Envia para a tabela 'movimentacoes' no Supabase
            novo_dado.to_sql('movimentacoes', engine, if_exists='append', index=False)
            st.success("Receita salva permanentemente no Supabase!")

elif aba == "Dashboard":
    st.header("📊 Painel de Controle")
    if engine:
        try:
            df = pd.read_sql("SELECT * FROM movimentacoes", engine)
            if not df.empty:
                receitas = df[df['tipo'] == 'Receita']['valor'].sum()
                despesas = df[df['tipo'] == 'Despesa']['valor'].sum()
                st.metric("Saldo Geral", f"R$ {receitas - despesas:,.2f}")
                st.bar_chart(df.groupby('categoria')['valor'].sum())
            else:
                st.info("Nenhum dado encontrado no banco.")
        except:
            st.warning("Tabela 'movimentacoes' ainda não existe ou está vazia.")

# ... (Você pode adicionar as abas de Despesas e Histórico seguindo a mesma lógica)
