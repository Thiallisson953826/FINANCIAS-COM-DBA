# ======================================
# TH PROGRAMAÇÃO
# Organizador Financeiro Profissional
# Produzido por Thiallisson
# ======================================

import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
import os

# ---------- CONFIGURAÇÃO DA PÁGINA ----------
st.set_page_config(
    page_title="Organizador Financeiro - TH",
    layout="wide"
)

st.title("💰 Organizador Financeiro - TH PROGRAMAÇÃO")

# ---------- BANCO DE DADOS ----------
PASTA = "dados"
DB = os.path.join(PASTA, "financeiro.db")
os.makedirs(PASTA, exist_ok=True)

conn = sqlite3.connect(DB, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS movimentacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    mes_ano TEXT NOT NULL,
    tipo TEXT NOT NULL,
    referente TEXT NOT NULL,
    valor REAL NOT NULL
)
""")
conn.commit()

# ---------- FUNÇÃO SALDO MÊS ANTERIOR ----------
def calcular_saldo_mes_anterior(mes_ano_atual):
    mes, ano = mes_ano_atual.split("-")
    mes = int(mes)
    ano = int(ano)

    if mes == 1:
        mes_anterior = 12
        ano_anterior = ano - 1
    else:
        mes_anterior = mes - 1
        ano_anterior = ano

    mes_ano_anterior = f"{mes_anterior:02d}-{ano_anterior}"

    df_ant = pd.read_sql_query(
        "SELECT tipo, valor FROM movimentacoes WHERE mes_ano = ?",
        conn,
        params=(mes_ano_anterior,)
    )

    if df_ant.empty:
        return 0.0

    entradas = df_ant[df_ant["tipo"] == "Entrada"]["valor"].sum()
    saidas = df_ant[df_ant["tipo"] == "Saída"]["valor"].sum()

    return entradas - saidas

# ---------- SELEÇÃO DO MÊS ----------
col_mes, col_vazio = st.columns([2, 8])
with col_mes:
    mes_ano = st.selectbox(
        "📅 Mês de referência",
        pd.date_range(start="2024-01-01", periods=120, freq="MS").strftime("%m-%Y")
    )

# ---------- CARREGAR DADOS DO MÊS ----------
df = pd.read_sql_query(
    "SELECT id, data, tipo, referente, valor FROM movimentacoes WHERE mes_ano = ? ORDER BY data",
    conn,
    params=(mes_ano,)
)

if not df.empty:
    df["data"] = pd.to_datetime(df["data"])
    df["valor"] = pd.to_numeric(df["valor"])

# ---------- FORMULÁRIO ----------
st.divider()
st.subheader("➕ Nova movimentação")

c1, c2, c3, c4 = st.columns(4)

with c1:
    tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
with c2:
    data_mov = st.date_input("Data", date.today())
with c3:
    referente = st.text_input("Referente a quê")
with c4:
    valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01)

if st.button("💾 Salvar movimentação", use_container_width=True):
    cursor.execute(
        """
        INSERT INTO movimentacoes (data, mes_ano, tipo, referente, valor)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            data_mov.strftime("%Y-%m-%d"),
            mes_ano,
            tipo,
            referente,
            valor
        )
    )
    conn.commit()
    st.success("Movimentação salva com sucesso!")
    st.rerun()

# ---------- CÁLCULOS ----------
saldo_anterior = calcular_saldo_mes_anterior(mes_ano)

entradas_mes = df[df["tipo"] == "Entrada"]["valor"].sum() if not df.empty else 0
saidas_mes = df[df["tipo"] == "Saída"]["valor"].sum() if not df.empty else 0
saldo_atual = saldo_anterior + entradas_mes - saidas_mes

# ---------- RESUMO ----------
st.divider()
st.subheader("📊 Resumo financeiro")

r1, r2, r3, r4 = st.columns(4)
r1.metric("💵 Entradas do mês", f"R$ {entradas_mes:,.2f}")
r2.metric("💸 Saídas do mês", f"R$ {saidas_mes:,.2f}")
r3.metric("⏮️ Saldo anterior", f"R$ {saldo_anterior:,.2f}")
r4.metric("📌 Saldo atual", f"R$ {saldo_atual:,.2f}")

# ---------- GRÁFICOS ----------
st.divider()
st.subheader("📈 Evolução financeira")

if not df.empty:
    st.bar_chart(df.groupby("tipo")["valor"].sum())

    df_graf = df.copy()
    df_graf["mov"] = df_graf.apply(
        lambda x: x["valor"] if x["tipo"] == "Entrada" else -x["valor"],
        axis=1
    )

    df_graf["saldo_acumulado"] = saldo_anterior + df_graf["mov"].cumsum()
    st.line_chart(df_graf.set_index("data")["saldo_acumulado"])
else:
    st.info("Nenhuma movimentação registrada neste mês.")

# ---------- TABELA COM CHECKBOX ----------
st.divider()
st.subheader("🧾 Movimentações do mês")

if not df.empty:
    df_view = df.copy()
    df_view["Selecionar"] = False
    df_view["Data"] = df_view["data"].dt.strftime("%d/%m/%Y")
    df_view["Valor (R$)"] = df_view["valor"]

    df_view = df_view[["Selecionar", "id", "Data", "tipo", "referente", "Valor (R$)"]]
    df_view.columns = ["Selecionar", "ID", "Data", "Tipo", "Referente", "Valor (R$)"]

    edited_df = st.data_editor(
        df_view,
        use_container_width=True,
        hide_index=True
    )

    ids_remover = edited_df[edited_df["Selecionar"] == True]["ID"].tolist()

    if ids_remover:
        if st.button("🗑 Remover selecionados", type="primary"):
            cursor.executemany(
                "DELETE FROM movimentacoes WHERE id = ?",
                [(i,) for i in ids_remover]
            )
            conn.commit()
            st.success("Movimentações removidas com sucesso!")
            st.rerun()
else:
    st.info("Sem dados para exibir.")

# ---------- EXPORTAR EXCEL ----------
st.divider()
st.subheader("📥 Exportar para Excel")

if not df.empty:
    df_excel = df.copy()
    df_excel["data"] = df_excel["data"].dt.strftime("%d/%m/%Y")
    df_excel.columns = ["ID", "Data", "Tipo", "Referente", "Valor"]

    nome_excel = f"financeiro_{mes_ano}.xlsx"
    df_excel.to_excel(nome_excel, index=False)

    with open(nome_excel, "rb") as f:
        st.download_button(
            "📊 Baixar Excel do mês",
            data=f,
            file_name=nome_excel,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Nenhum dado para exportar.")
