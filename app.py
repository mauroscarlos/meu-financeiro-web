import streamlit as st
from sqlalchemy import create_engine
import pandas as pd

st.title("🛡️ SGF PRO - Teste de Conexão")

# Função de conexão
@st.cache_resource
def conexao():
    url = st.secrets["connections"]["postgresql"]["url"]
    return create_engine(url)

try:
    engine = conexao()
    # Tenta ler a tabela de usuários que você acabou de criar
    df = pd.read_sql("SELECT nome FROM usuarios", engine)
    st.success(f"Conectado com sucesso! Usuários encontrados: {df['nome'].iloc[0]}")
except Exception as e:
    st.error(f"Erro de conexão: {e}")

