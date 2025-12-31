import streamlit as st
import pandas as pd
import psycopg2
from datetime import date
import os

# ================= CONFIGURAÇÕES =================
st.set_page_config(page_title="Organizador Financeiro", layout="wide")
st.title("💰 Organizador Financeiro Mensal")

# ================= BANCO DE DADOS =================
# pega a URL do banco nos Secrets do Streamlit Cloud
DATABASE_URL = st.secrets["DATABASE_URL"]

# conecta ao PostgreSQL
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# cria tabela se não existir
cursor.execute("""
CREATE TABLE IF NOT EXISTS lancamentos (
    id SERIAL PRIMARY KEY,
    data TEXT,
    tipo TEXT,
    referente TEXT,
    valor REAL,
    mes TEXT
)
""")
conn.commit()

# ================= FUNÇÕES =================
def inserir(data, tipo, referente, valor, mes):
    cursor.execute(
        "INSERT INTO lancamentos (data, tipo, referente, valor, mes) VALUES (%s, %s, %s, %s, %s)",
        (data, tipo, referente, valor, mes)
    )
    conn.commit()

def carregar_mes(mes):
    df = pd.read_sql("SELECT * FROM lancamentos WHERE mes=%s ORDER BY id DESC", conn, params=(mes,))
    return df

def saldo_mes_anterior(mes_atual):
    ano, mes = map(int, mes_atual.split("-"))
    if mes == 1:
        ano -= 1
        mes = 12
    else:
        mes -= 1
    mes_ant = f"{ano}-{mes:02d}"

    df = pd.read_sql("SELECT tipo, valor FROM lancamentos WHERE mes=%s", conn, params=(mes_ant,))
    entradas = df[df["tipo"] == "Entrada"]["valor"].sum() if not df.empty else 0
    saidas = df[df["tipo"] == "Saída"]["valor"].sum() if not df.empty else 0
    return entradas - saidas

def remover(ids):
    for i in ids:
        cursor.execute("DELETE FROM lancamentos WHERE id=%s", (i,))
    conn.commit()

# ================= INTERFACE =================

# seleção de mês
mes_selecionado = st.selectbox(
    "Selecione o mês",
    [f"{date.today().year}-{m:02d}" for m in range(1, 13)],
    index=date.today().month - 1
)

# saldo anterior aparece primeiro
saldo_ant = saldo_mes_anterior(mes_selecionado)
st.info(f"💼 Saldo do mês anterior: R$ {saldo_ant:,.2f}")

# formulário de cadastro
with st.form("form"):
    col1, col2, col3 = st.columns(3)
    data = col1.date_input("Data", date.today())
    tipo = col2.selectbox("Tipo", ["Entrada", "Saída"])
    referente = col3.text_input("Referente a")
    valor = st.number_input("Valor", min_value=0.0, format="%.2f")

    salvar = st.form_submit_button("Salvar")

    if salvar and referente and valor > 0:
        inserir(str(data), tipo, referente, valor, mes_selecionado)
        st.success("Lançamento adicionado com sucesso!")
        st.experimental_rerun()

# ================= LISTAGEM =================
df = carregar_mes(mes_selecionado)

if not df.empty:
    entradas = df[df["tipo"] == "Entrada"]["valor"].sum()
    saidas = df[df["tipo"] == "Saída"]["valor"].sum()
    saldo = saldo_ant + entradas - saidas

    c1, c2, c3 = st.columns(3)
    c1.metric("Entradas", f"R$ {entradas:,.2f}")
    c2.metric("Saídas", f"R$ {saidas:,.2f}")
    c3.metric("Saldo Final", f"R$ {saldo:,.2f}")

    st.subheader("📋 Lançamentos")
    df["Selecionar"] = False
    editado = st.data_editor(df, hide_index=True)

    if st.button("🗑️ Remover selecionados"):
        ids = editado[editado["Selecionar"] == True]["id"].tolist()
        remover(ids)
        st.experimental_rerun()

else:
    st.warning("Nenhum lançamento neste mês.")
