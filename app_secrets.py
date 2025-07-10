# === DASHBOARD DE ACOMPANHAMENTO DE PROGRAMAS ===
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

# === MAPA DE QUARTERS ===
quarters = {
    "Gestacao Segura": "Q1", "Coluna": "Q1", "DRC e Tx Renal": "Q1", "Saude Mental": "Q1", "ICC": "Q1",
    "Pos IAM": "Q1", "Emagrecimento": "Q1", "Fumo Zero": "Q1", "Anticoagulantes": "Q1", "CA Mama": "Q1",
    "Endometriose": "Q2", "CA de prostata": "Q2", "CA de pulmao": "Q2", "Arritmia complexa": "Q2",
    "Valvopatia": "Q2", "Doenca autoimune": "Q2",
    "CA colorretal": "Q3", "DM insulino dependente (HAS/DIA)": "Q3", "DPOC": "Q3", "ASMA": "Q3",
    "Cefaleia": "Q3", "Tx hepatico": "Q3", "TMO": "Q3"
}
df["Quarter"] = df["Linha"].apply(lambda x: quarters.get(x.strip(), "Sem Quarter"))

# === FILTROS ===
st.sidebar.header("🔍 Filtros")
quarter_sel = st.sidebar.selectbox("Quarter", ["Todos"] + sorted(df["Quarter"].unique()))
linha_sel = st.sidebar.selectbox("Linha de Cuidado", ["Todos"] + sorted(df["Linha"].unique()))
status_sel = st.sidebar.selectbox("Status", ["Todos"] + sorted(df["Status"].unique()))

# === APLICAÇÃO DOS FILTROS ===
df_filtrado = df.copy()
if quarter_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Quarter"] == quarter_sel]
if linha_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Linha"] == linha_sel]
if status_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Status"] == status_sel]

# === NAVEGAÇÃO POR ABAS ===
tabas = st.tabs(["📈 Visão Geral", "📋 Monitoramento", "📘 Linhas", "💬 Insights", "⚙️ Admin"])

# === ABA 1: VISÃO GERAL ===
with tabas[0]:
    st.subheader("📈 Visão Geral em Gráficos")
    if not df_filtrado.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig_status = px.pie(df_filtrado, names="Status", title="Distribuição de Status")
            st.plotly_chart(fig_status, use_container_width=True)
        with col2:
            fig_quarter = px.bar(df_filtrado, x="Quarter", color="Status", barmode="group", title="Status por Quarter")
            st.plotly_chart(fig_quarter, use_container_width=True)
    else:
        st.info("Nenhuma tarefa encontrada para os filtros selecionados.")

# === ABA 2: MONITORAMENTO ===
with tabas[1]:
    st.subheader("📋 Tabela de Tarefas")
    status_opcoes = ["Não iniciado", "Em andamento", "Concluído", "Ação Contínua"]
    config_colunas = {
        "Status": st.column_config.SelectboxColumn("Status", options=status_opcoes)
    }
    edited_df = st.data_editor(df_filtrado, use_container_width=True, column_config=config_colunas, num_rows="dynamic")
    if st.button("💾 Salvar Alteracoes"):
        try:
            df.loc[edited_df.index, :] = edited_df
            sheet.update([df.columns.tolist()] + df.values.tolist())
            st.success("Alteracoes salvas com sucesso!")
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

# === ABA 3: POR LINHA ===
with tabas[2]:
    st.subheader("📘 Visualização por Linha de Cuidado")

    status_cores = {
        "Concluído": "🟢",
        "Em andamento": "🟡",
        "Não iniciado": "🔴",
        "Ação Contínua": "🔵"
    }

    quarters_ordenados = ["Q1", "Q2", "Q3", "Q4", "Sem Quarter"]
    for quarter in quarters_ordenados:
        linhas_quarter = sorted(df[df["Quarter"] == quarter]["Linha"].unique())
        if not linhas_quarter:
            continue

        st.markdown(f"### 🗓️ Quarter {quarter[-1] if quarter != 'Sem Quarter' else 'Desconhecido'}")

        num_por_linha = 4
        for i in range(0, len(linhas_quarter), num_por_linha):
            cols = st.columns(num_por_linha)
            for j, linha in enumerate(linhas_quarter[i:i+num_por_linha]):
                df_linha = df[df["Linha"] == linha]
                total = len(df_linha)
                concluidas = len(df_linha[df_linha["Status"] == "Concluído"])
                status_dominante = df_linha["Status"].mode()[0]
                cor = status_cores.get(status_dominante, "⚪")

                fig = px.pie(df_linha, names="Status", hole=0.4)
                fig.update_layout(
                    margin=dict(l=0, r=0, t=0, b=0),
                    height=160,
                    showlegend=False
                )

                with cols[j]:
                    st.markdown(f"""
                        <div style='
                            background-color: #fff;
                            border: 1px solid #ddd;
                            border-radius: 12px;
                            padding: 12px;
                            box-shadow: 1px 2px 5px rgba(0,0,0,0.05);
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                            height: 300px;
                            overflow: hidden;
                        '>
                            <h5 style='margin-bottom: 4px; text-align: center;'>{cor} {linha}</h5>
                            <p style='font-size: 13px; text-align: center; margin: 4px 0;'>Total: {total} | ✅ {concluidas}</p>
                    """, unsafe_allow_html=True)

                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"pie_{linha.replace(' ', '_')}_{quarter}")

                    st.markdown("</div>", unsafe_allow_html=True)
                    
# === ABA 4: INSIGHTS ===
with tabas[3]:
    st.subheader("💬 Insights Inteligentes")
    try:
        total = len(df)
        concluidas = len(df[df["Status"] == "Concluído"])
        pendentes = df[df["Status"] != "Concluído"]
        st.markdown(f"- Total de tarefas: **{total}**")
        st.markdown(f"- Concluídas: **{concluidas}** ({concluidas/total:.0%})")
        st.markdown(f"- Tarefas em aberto: **{len(pendentes)}**")
        if not pendentes.empty:
            linha_critica = pendentes["Linha"].value_counts().idxmax()
            st.markdown(f"- Linha com mais pendências: **{linha_critica}**")
    except:
        st.warning("Erro ao gerar insights.")

# === ABA 5: ADMINISTRAÇÃO ===
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
