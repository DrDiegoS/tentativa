import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials
from datetime import datetime

# === CONFIGURAÇÃO DO APP ===
st.set_page_config(layout="wide")
st.title("📊 Dashboard de Acompanhamento de Programas")

# === CONEXÃO COM GOOGLE SHEETS ===
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
service_account_info = st.secrets["google_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
client = gspread.authorize(creds)

SHEET_ID = "1dQDcSnroIs2iefAsgcDA11jNbVqDUP6w0HFOY-yzBYc"
SHEET_NAME = "bd"
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# === LEITURA DOS DADOS ===
data = sheet.get_all_records()
df = pd.DataFrame(data)

# === ADICIONAR NOVA LINHA DE CUIDADO ===
st.sidebar.markdown("---")
st.sidebar.header("➕ Nova Linha de Cuidado")
nova_linha = st.sidebar.text_input("Nome da nova linha")

if st.sidebar.button("Adicionar Nova Linha"):
    try:
        modelo = df[['Fase', 'Tarefa']].drop_duplicates().reset_index(drop=True)
        nova_estrutura = modelo.copy()
        nova_estrutura['Linha'] = nova_linha
        nova_estrutura['Status'] = "Não iniciado"
        nova_estrutura['Observações'] = ""
        nova_estrutura['Prazo'] = ""
        nova_estrutura = nova_estrutura[df.columns.tolist()]
        df = pd.concat([df, nova_estrutura], ignore_index=True)
        sheet.update([df.columns.tolist()] + df.values.tolist())
        st.success(f"Linha de cuidado '{nova_linha}' adicionada com sucesso!")
    except Exception as e:
        st.error(f"Erro ao adicionar linha: {e}")

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

# === GRÁFICOS ===
st.subheader("📈 Visão Geral em Gráficos")

if not df_filtrado.empty:
    fig_status = px.pie(df_filtrado, names="Status", title="Distribuição de Status")
    st.plotly_chart(fig_status, use_container_width=True)

    fig_linha = px.bar(df_filtrado, x="Linha", color="Status", title="Tarefas por Linha de Cuidado", barmode="group")
    st.plotly_chart(fig_linha, use_container_width=True)

    fig_fase = px.bar(df_filtrado, x="Fase", color="Status", title="Tarefas por Fase", barmode="group")
    st.plotly_chart(fig_fase, use_container_width=True)
else:
    st.info("Nenhuma tarefa encontrada para os filtros selecionados.")

# === INDICADORES ===
col1, col2, col3 = st.columns(3)
col1.metric("Total de Tarefas", len(df_filtrado))
col2.metric("Concluídas", df_filtrado["Status"].value_counts().get("Concluído", 0))
col3.metric("Em Andamento", df_filtrado["Status"].value_counts().get("Em andamento", 0))

# === CONFIGURAÇÃO DAS COLUNAS EDITÁVEIS ===
status_opcoes = ["Não iniciado", "Em andamento", "Concluído", "Ação Contínua"]
config_colunas = {
    "Status": st.column_config.SelectboxColumn(
        "Status",
        help="Selecione o status da tarefa",
        options=status_opcoes,
        required=True
    )
}

# === TABELA DE TAREFAS COM DROPDOWN ===
st.subheader("📋 Tarefas Filtradas")
edited_df = st.data_editor(
    df_filtrado,
    use_container_width=True,
    num_rows="dynamic",
    column_config=config_colunas
)

# === BOTÃO DE SALVAR ===
if st.button("💾 Salvar Alterações"):
    try:
        df.loc[edited_df.index, :] = edited_df
        sheet.update([df.columns.tolist()] + df.values.tolist())
        st.success("Alterações salvas com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

# === ABAS POR LINHA DE CUIDADO ===
st.markdown("---")
st.subheader("🗂️ Visualização por Linha")

linhas_unicas = df["Linha"].unique()
abas = st.tabs(list(linhas_unicas))
for i, linha in enumerate(linhas_unicas):
    with abas[i]:
        st.markdown(f"### Linha: {linha}")
        st.dataframe(df[df["Linha"] == linha])

# === RODAPÉ ===
st.markdown("---")
st.caption(f"Atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
