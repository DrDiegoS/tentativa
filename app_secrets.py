# === DASHBOARD DE ACOMPANHAMENTO DE PROGRAMAS ===
import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials
from datetime import datetime

# === CONFIGURAÇÃO DO APP ===
st.set_page_config(page_title="Acompanhamento de Linhas de Cuidado", layout="wide")

# === CABEÇALHO COM TÍTULO À ESQUERDA E LOGO À DIREITA ===
col1, col2 = st.columns([6, 1])  # Proporção ajustável

with col1:
    st.markdown("<h1 style='margin-bottom:0;'>Programas e Linhas de Cuidado</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='margin-top:0;'>Diretoria de Gestão Clínica</h3>", unsafe_allow_html=True)

with col2:
    st.image("logo_cuidadosmil.png", width=220)  # Ajuste o tamanho conforme necessário

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
        # === Contadores Visuais ===
        col1, col2, col3 = st.columns(3)
        col1.metric("📊 Total de Tarefas", len(df_filtrado))
        col2.metric("✅ Concluídas", len(df_filtrado[df_filtrado["Status"] == "Concluído"]))
        col3.metric("⚠️ Pendentes", len(df_filtrado[df_filtrado["Status"] != "Concluído"]))

        # === Gráficos ===
        col4, col5 = st.columns(2)
        with col4:
            fig_status = px.pie(df_filtrado, names="Status", title="Distribuição de Status")
            st.plotly_chart(fig_status, use_container_width=True)

        with col5:
            fig_quarter = px.bar(df_filtrado, x="Quarter", color="Status", barmode="group", title="Status por Quarter")
            st.plotly_chart(fig_quarter, use_container_width=True)

        # === Tabela Resumo ===
        st.markdown("### 📋 Resumo por Linha de Cuidado")
        resumo = df_filtrado.groupby(["Linha", "Status"]).size().unstack(fill_value=0)
        resumo["Total"] = resumo.sum(axis=1)
        st.dataframe(resumo.reset_index(), use_container_width=True)

    else:
        st.info("Nenhuma tarefa encontrada para os filtros selecionados.")

# === ABA 2: MONITORAMENTO ===
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
            
# === ABA 3: POR LINHA ===
with tabas[2]:
    st.subheader("📘 Visualização por Linha de Cuidado")

    busca_linha = st.text_input("🔍 Buscar por nome da linha")

    status_cores = {
        "Concluído": "🟢",
        "Em andamento": "🟡",
        "Não iniciado": "🔴",
        "Ação Contínua": "🔵"
    }

    # Filtro inteligente por nome
    linhas_filtradas = df[df["Linha"].str.contains(busca_linha, case=False, na=False)] if busca_linha else df

    quarters_ordenados = ["Q1", "Q2", "Q3", "Q4", "Sem Quarter"]
    for quarter in quarters_ordenados:
        linhas_quarter = sorted(linhas_filtradas[linhas_filtradas["Quarter"] == quarter]["Linha"].unique())
        if not linhas_quarter:
            continue

        st.markdown(f"### 🗓️ Quarter {quarter[-1] if quarter != 'Sem Quarter' else 'Desconhecido'}")

        num_por_linha = 3
        for i in range(0, len(linhas_quarter), num_por_linha):
            cols = st.columns(num_por_linha)
            for j, linha in enumerate(linhas_quarter[i:i+num_por_linha]):
                df_linha = df[df["Linha"] == linha]
                total = len(df_linha)
                concluidas = len(df_linha[df_linha["Status"] == "Concluído"])
                status_dominante = df_linha["Status"].mode()[0]
                cor = status_cores.get(status_dominante, "⚪")

                with cols[j]:
                    st.markdown(f"""
                        <div style='
                            background-color: #fff;
                            border: 1px solid #ddd;
                            border-radius: 12px;
                            padding: 16px;
                            height: auto;
                            box-shadow: 1px 2px 5px rgba(0,0,0,0.05);
                            display: flex;
                            flex-direction: column;
                            justify-content: space-between;
                        '>
                            <div>
                                <h4 style='margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>
                                    {cor} <span style="font-size: 18px;">{linha}</span>
                                </h4>
                                <ul style='padding-left: 20px; margin: 0; font-size: 15px;'>
                                    <li><strong>Total:</strong> {total} tarefas</li>
                                    <li><strong>Concluídas:</strong> {concluidas}</li>
                                    <li><strong>Status dominante:</strong> <span style="font-family: monospace;">{status_dominante}</span></li>
                                </ul>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    with st.expander(f"📂 Ver tarefas de {linha}"):
                        colunas_exibir = ["Tarefa", "Status"]
                        st.dataframe(df_linha[colunas_exibir], use_container_width=True)

                        fig = px.pie(
                            df_linha,
                            names="Status",
                            title=None,
                            width=300,
                            height=250
                        )
                        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
                        st.plotly_chart(fig, use_container_width=False, key=f"grafico_{linha.replace(' ', '_')}")
                    
# === ABA 4: INSIGHTS ===
with tabas[3]:
    st.subheader("💬 Insights Inteligentes")

    if not df.empty:
        total = len(df)
        concluidas = len(df[df["Status"] == "Concluído"])
        pendentes = df[df["Status"] != "Concluído"]

        # === Métricas de topo ===
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 Total de Tarefas", total)
        col2.metric("✅ Concluídas", concluidas, f"{(concluidas/total):.0%}")
        col3.metric("⚠️ Em Aberto", len(pendentes))
        linha_critica = pendentes["Linha"].value_counts().idxmax()
        col4.metric("📍 Mais Pendências", linha_critica)

        # === Gráfico de calor por linha e status ===
        st.markdown("### 🔥 Mapa de Calor de Pendências")
        heat_data = pd.crosstab(pendentes["Linha"], pendentes["Status"])
        st.dataframe(heat_data, use_container_width=True)

        # === Gráfico de barras com maiores linhas pendentes ===
        st.markdown("### 📌 Linhas com Mais Pendências")
        pendencias_por_linha = pendentes["Linha"].value_counts().reset_index()
        pendencias_por_linha.columns = ["Linha", "Pendências"]
        fig = px.bar(pendencias_por_linha, x="Linha", y="Pendências", title="Top Linhas com Pendências", text="Pendências")
        fig.update_layout(xaxis_title="", yaxis_title="Qtd", xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        # === NOVO INSIGHT: Progresso por Linha ===
        st.markdown("### ✅ Progresso por Linha (%)")

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

    else:
        st.info("Nenhum dado disponível para gerar insights.")

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
