
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# === CONFIGURAÇÃO DO APP ===
st.set_page_config(layout="wide")
st.title("📊 Dashboard de Acompanhamento de Programas")

# === CONEXÃO COM GOOGLE SHEETS via SECRETS ===
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
service_account_info = st.secrets["google_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
client = gspread.authorize(creds)

# ID e Nome da Planilha
SHEET_ID = "1dQDcSnroIs2iefAsgcDA11jNbVqDUP6w0HFOY-yzBYc"
SHEET_NAME = "bd"
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# === LEITURA DOS DADOS ===
data = sheet.get_all_records()
df = pd.DataFrame(data)

# === FILTROS ===
st.sidebar.header("🔍 Filtros")
linhas = ["Todos"] + sorted(df['Linha'].unique())
fases = ["Todos"] + sorted(df['Fase'].unique())
status_list = ["Todos"] + sorted(df['Status'].unique())

linha_sel = st.sidebar.selectbox("Linha de Cuidado", linhas)
fase_sel = st.sidebar.selectbox("Fase", fases)
status_sel = st.sidebar.selectbox("Status", status_list)

df_filtrado = df.copy()
if linha_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Linha"] == linha_sel]
if fase_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Fase"] == fase_sel]
if status_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Status"] == status_sel]

# === INDICADORES ===
col1, col2, col3 = st.columns(3)
col1.metric("Total de Tarefas", len(df_filtrado))
col2.metric("Concluídas", df_filtrado["Status"].value_counts().get("Concluído", 0))
col3.metric("Em Andamento", df_filtrado["Status"].value_counts().get("Em andamento", 0))

# === TABELA DE TAREFAS ===
st.subheader("📋 Tarefas Filtradas")
edited_df = st.data_editor(df_filtrado, use_container_width=True, num_rows="dynamic")

# === BOTÃO DE SALVAR ===
if st.button("💾 Salvar Alterações"):
    try:
        df.update(edited_df)
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
        st.success("Alterações salvas com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

# === RODAPÉ ===
st.markdown("---")
st.caption(f"Atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
