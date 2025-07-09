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

# === ATRIBUIR QUARTER AUTOMATICAMENTE ===
map_quarter = {
    "Gestação Segura": "Q1",
    "Coluna": "Q1",
    "DRC e Tx Renal": "Q1",
    "Saúde Mental": "Q1",
    "ICC": "Q1",
    "Pós IAM": "Q1",
    "Emagrecimento": "Q1",
    "Fumo Zero": "Q1",
    "Anticoagulantes": "Q1",
    "CA Mama": "Q1",
    "Pós-AVC": "Q2",
    "Endometriose​": "Q2",
    "CA de próstata​": "Q2",
    "CA de pulmão​": "Q2",
    "Arritmia complexa​": "Q2",
    "Valvopatia​": "Q2",
    "Doença autoimune​": "Q2",
    "CA colorretal​": "Q3",
    "DM insulino –dependente (HAS/DIA)​": "Q3",
    "DPOC": "Q3",
    "ASMA": "Q3",
    "Cefaleia​": "Q3",
    "Tx hepático​": "Q3",
    "TMO​": "Q3"
}
df["Quarter"] = df["Linha"].map(map_quarter).fillna("Sem Quarter")

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
        nova_estrutura['Quarter'] = map_quarter.get(nova_linha, "Sem Quarter")
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

# === GRÁFICO DE PROGRESSO POR QUARTER ===
st.subheader("📆 Progresso por Quarter")
if "Quarter" in df.columns:
    df_quarter = df.copy()
    df_quarter["Contagem"] = 1
    progresso_q = df_quarter.groupby(["Quarter", "Status"]).agg({"Contagem": "sum"}).reset_index()
    fig_quarter = px.bar(
        progresso_q,
        x="Quarter",
        y="Contagem",
        color="Status",
        title="Progresso das Linhas por Quarter",
        barmode="stack",
        category_orders={"Quarter": ["Q1", "Q2", "Q3", "Q4", "Sem Quarter"]}
    )
    st.plotly_chart(fig_quarter, use_container_width=True)

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

# === ABA POR LINHA DE CUIDADO ===
st.markdown("---")
st.subheader("📘 Visualização por Linha")

linhas_unicas = df["Linha"].unique()
abas = st.tabs(list(linhas_unicas))
for i, linha in enumerate(linhas_unicas):
    with abas[i]:
        st.markdown(f"### Linha: {linha}")
        st.dataframe(df[df["Linha"] == linha])

# === INSIGHTS COM IA ===
st.markdown("---")
st.subheader("💬 Insights Inteligentes")

try:
    resumo = []
    total_tarefas = len(df)
    concluidas = df[df["Status"] == "Concluído"]
    andamento = df[df["Status"] == "Em andamento"]
    nao_iniciado = df[df["Status"] == "Não iniciado"]
    pendencias = df[df["Status"] != "Concluído"].groupby("Linha").size().sort_values(ascending=False)

    resumo.append(f"- Total de tarefas: **{total_tarefas}**")
    resumo.append(f"- Tarefas concluídas: **{len(concluidas)}** ({len(concluidas)/total_tarefas:.0%})")
    resumo.append(f"- Tarefas em andamento: **{len(andamento)}**")
    resumo.append(f"- Tarefas ainda não iniciadas: **{len(nao_iniciado)}**")

    if not pendencias.empty:
        linha_mais_critica = pendencias.index[0]
        resumo.append(f"- ⚠️ Linha com mais pendências: **{linha_mais_critica}** ({pendencias.iloc[0]} tarefas não concluídas)")

    fase_critica = df[df["Status"] == "Não iniciado"]["Fase"].value_counts().idxmax()
    resumo.append(f"- 🕒 Fase com mais tarefas não iniciadas: **{fase_critica}**")

    if len(nao_iniciado) > len(concluidas):
        resumo.append("👉 **Sugestão:** priorize ações de início das tarefas paradas para impulsionar o avanço geral.")
    elif len(andamento) > len(concluidas):
        resumo.append("👉 **Sugestão:** acompanhe de perto as tarefas em andamento para garantir conclusão.")

    for item in resumo:
        st.markdown(item)

except Exception as e:
    st.warning(f"Não foi possível gerar os insights automáticos: {e}")

# === RODAPÉ ===
st.markdown("---")
st.caption(f"Atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
