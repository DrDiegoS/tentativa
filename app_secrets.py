# === DASHBOARD DE ACOMPANHAMENTO DE PROGRAMAS COM PRAZOS ===
import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials
from datetime import datetime

# === CONFIGURAÇÃO INICIAL ===
st.set_page_config(page_title="Acompanhamento de Linhas de Cuidado", layout="wide")
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

# === CONVERSÃO DA COLUNA PRAZO ===
df["Prazo"] = pd.to_datetime(df["Prazo"], errors="coerce")
hoje = datetime.today()
df["Dias Restantes"] = (df["Prazo"] - hoje).dt.days

def classificar_prazo(dias):
    if pd.isna(dias):
        return "🔘 Sem prazo"
    elif dias < 0:
        return "❌ Vencido"
    elif dias <= 3:
        return "⚠️ Próximo"
    else:
        return "✅ No prazo"

df["Status do Prazo"] = df["Dias Restantes"].apply(classificar_prazo)

# === FILTROS ===
st.sidebar.header("🔍 Filtros")
quarter_sel = st.sidebar.selectbox("Quarter", ["Todos"] + sorted(df["Quarter"].unique()))
linha_sel = st.sidebar.selectbox("Linha de Cuidado", ["Todos"] + sorted(df["Linha"].unique()))
status_sel = st.sidebar.selectbox("Status", ["Todos"] + sorted(df["Status"].unique()))
prazo_sel = st.sidebar.selectbox("Status do Prazo", ["Todos"] + sorted(df["Status do Prazo"].unique()))

# === APLICAÇÃO DOS FILTROS ===
df_filtrado = df.copy()
if quarter_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Quarter"] == quarter_sel]
if linha_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Linha"] == linha_sel]
if status_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Status"] == status_sel]
if prazo_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Status do Prazo"] == prazo_sel]

# === NAVEGAÇÃO POR ABAS ===
tabas = st.tabs(["📈 Visão Geral", "📋 Monitoramento", "📘 Linhas", "💬 Insights", "⚙️ Admin"])

# === ABA VISÃO GERAL ===
with tabas[0]:
    st.subheader("📈 Visão Geral em Gráficos")

    if not df_filtrado.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("📊 Total de Tarefas", len(df_filtrado))
        col2.metric("✅ Concluídas", len(df_filtrado[df_filtrado["Status"] == "Concluído"]))
        col3.metric("⚠️ Pendentes", len(df_filtrado[df_filtrado["Status"] != "Concluído"]))

        col4, col5 = st.columns(2)
        with col4:
            fig_status = px.pie(df_filtrado, names="Status", title="Distribuição de Status")
            st.plotly_chart(fig_status, use_container_width=True)

        with col5:
            fig_prazo = px.pie(df_filtrado, names="Status do Prazo", title="Distribuição por Prazo")
            st.plotly_chart(fig_prazo, use_container_width=True)

        st.markdown("### 📋 Resumo por Linha de Cuidado")
        resumo = df_filtrado.groupby(["Linha", "Status"]).size().unstack(fill_value=0)
        resumo["Total"] = resumo.sum(axis=1)
        st.dataframe(resumo.reset_index(), use_container_width=True)
    else:
        st.info("Nenhuma tarefa encontrada para os filtros selecionados.")

# === ABA MONITORAMENTO ===
with tabas[1]:
    st.subheader("📋 Tabela de Tarefas")
    palavra_chave = st.text_input("🔎 Buscar por tarefa, fase ou linha")

    df_monitor = df_filtrado.copy()
    if palavra_chave:
        filtro = (
            df_monitor["Tarefa"].str.contains(palavra_chave, case=False, na=False) |
            df_monitor["Fase"].str.contains(palavra_chave, case=False, na=False) |
            df_monitor["Linha"].str.contains(palavra_chave, case=False, na=False)
        )
        df_monitor = df_monitor[filtro]

    status_opcoes = ["Não iniciado", "Em andamento", "Concluído", "Ação Contínua"]
    config_colunas = {
        "Status": st.column_config.SelectboxColumn("Status", options=status_opcoes),
        "Observações": st.column_config.TextColumn("Observações")
    }

    edited_df = st.data_editor(
        df_monitor,
        use_container_width=True,
        column_config=config_colunas,
        num_rows="dynamic"
    )

    if st.button("💾 Salvar Alterações"):
        try:
            df.update(edited_df)
            sheet.update([df.columns.tolist()] + df.values.tolist())
            st.success("Alterações salvas com sucesso!")
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

# === ABA LINHAS ===
with tabas[2]:
    st.subheader("📘 Visualização por Linha de Cuidado")
    busca = st.text_input("🔍 Buscar por nome da linha")
    status_cores = {
        "Concluído": "🟢",
        "Em andamento": "🟡",
        "Não iniciado": "🔴",
        "Ação Contínua": "🔵"
    }
    linhas_exibir = sorted(df[df["Linha"].str.contains(busca, case=False, na=False) if busca else df["Linha"].notna()]["Linha"].unique())

    for linha in linhas_exibir:
        df_linha = df[df["Linha"] == linha]
        total = len(df_linha)
        concluidas = len(df_linha[df_linha["Status"] == "Concluído"])
        status_dominante = df_linha["Status"].mode()[0] if not df_linha.empty else "-"
        cor = status_cores.get(status_dominante, "⚪")

        with st.expander(f"{cor} {linha} ({total} tarefas)"):
            st.dataframe(df_linha[["Tarefa", "Status", "Prazo", "Status do Prazo"]], use_container_width=True)

# === ABA INSIGHTS ===
with tabas[3]:
    st.subheader("💬 Insights Inteligentes")

    st.markdown("### 📊 Gráfico: Status do Prazo")
    fig_prazo_hist = px.histogram(df_filtrado, x="Status do Prazo", title="Tarefas por Status do Prazo")
    st.plotly_chart(fig_prazo_hist, use_container_width=True)

    progresso = (
        df.groupby("Linha")["Status"]
        .apply(lambda x: (x == "Concluído").sum() / len(x) * 100)
        .reset_index(name="Percentual Concluído")
    )

    fig_prog = px.bar(
        progresso,
        x="Percentual Concluído",
        y="Linha",
        orientation="h",
        text="Percentual Concluído",
        title="Progresso por Linha de Cuidado (%)",
    )
    fig_prog.update_layout(xaxis_title="%", yaxis_title="", xaxis_range=[0, 100])
    fig_prog.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    st.plotly_chart(fig_prog, use_container_width=True)

# === ABA ADMIN ===
with tabas[4]:
    st.subheader("⚙️ Adicionar Nova Linha de Cuidado")
    nova_linha = st.text_input("Nome da nova linha")
    if st.button("Adicionar Linha"):
        try:
            modelo = df[["Fase", "Tarefa"]].drop_duplicates()
            nova_estrutura = modelo.copy()
            nova_estrutura["Linha"] = nova_linha
            nova_estrutura["Status"] = "Não iniciado"
            nova_estrutura["Observações"] = ""
            nova_estrutura["Prazo"] = ""
            nova_estrutura = nova_estrutura[df.columns.tolist()]
            df = pd.concat([df, nova_estrutura], ignore_index=True)
            sheet.update([df.columns.tolist()] + df.values.tolist())
            st.success(f"Linha '{nova_linha}' adicionada com sucesso!")
        except Exception as e:
            st.error(f"Erro ao adicionar linha: {e}")

# === RODAPÉ ===
st.markdown("---")
st.caption(f"Atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
