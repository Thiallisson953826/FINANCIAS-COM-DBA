# ======================================
# TH PROGRAMAÇÃO
# Produzido por Thiallisson
# ======================================

import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import os

st.set_page_config(page_title="Organizador Financeiro - TH PROGRAMAÇÃO")

st.title("💰 Organizador Financeiro - TH PROGRAMAÇÃO")

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

mes_ano = st.selectbox(
    "📅 Selecione o mês",
    pd.date_range(start="2024-01-01", periods=60, freq="MS").strftime("%m-%Y")
)

df = pd.read_sql_query(
    "SELECT data, tipo, referente, valor FROM movimentacoes WHERE mes_ano = ?",
    conn,
    params=(mes_ano,)
)

if not df.empty:
    df["valor"] = pd.to_numeric(df["valor"])
    df["data"] = pd.to_datetime(df["data"])

st.divider()

st.subheader("➕ Nova movimentação")

tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
data_mov = st.date_input("Data", date.today())
referente = st.text_input("Referente")
valor = st.number_input("Valor", min_value=0.0, step=0.01)

if st.button("Salvar"):
    cursor.execute(
        "INSERT INTO movimentacoes (data, mes_ano, tipo, referente, valor) VALUES (?, ?, ?, ?, ?)",
        (data_mov.strftime("%Y-%m-%d"), mes_ano, tipo, referente, valor)
    )
    conn.commit()
    st.success("Movimentação salva")
    st.rerun()

entradas = df[df["tipo"] == "Entrada"]["valor"].sum() if not df.empty else 0
saidas = df[df["tipo"] == "Saída"]["valor"].sum() if not df.empty else 0
saldo = entradas - saidas

st.subheader("📊 Resumo")
st.write(f"Entradas: R$ {entradas:,.2f}")
st.write(f"Saídas: R$ {saidas:,.2f}")
st.write(f"Saldo: R$ {saldo:,.2f}")

if not df.empty:
    st.bar_chart(df.groupby("tipo")["valor"].sum())
    st.dataframe(df)

    excel_name = f"financeiro_{mes_ano}.xlsx"
    df_export = df.copy()
    df_export["data"] = df_export["data"].dt.strftime("%d/%m/%Y")
    df_export.columns = ["Data", "Tipo", "Referente", "Valor"]
    df_export.to_excel(excel_name, index=False)

    with open(excel_name, "rb") as f:
        st.download_button("📥 Baixar Excel", f, excel_name)

