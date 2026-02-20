"""
finflow/calculos.py — Lógica de negócio financeira
"""
from __future__ import annotations
import pandas as pd
from typing import Optional

MESES_PT = ["","Janeiro","Fevereiro","Março","Abril","Maio","Junho",
            "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]

def fmt_brl(valor: float) -> str:
    """Formata valor como R$ 1.234,56"""
    return f"R$ {valor:,.2f}".replace(",","X").replace(".",",").replace("X",".")

def mes_label(mes_str: str) -> str:
    """'2026-02' → 'Fevereiro/2026'"""
    y, m = mes_str.split("-")
    return f"{MESES_PT[int(m)]}/{y}"

def resumo_periodo(df: pd.DataFrame) -> dict:
    """Retorna receitas, despesas, saldo e contagem do período."""
    if df.empty:
        return {"receitas": 0.0, "despesas": 0.0, "saldo": 0.0, "total": 0}
    rec = float(df[df["tipo"] == "receita"]["valor"].sum())
    desp = float(df[df["tipo"] == "despesa"]["valor"].sum())
    return {"receitas": rec, "despesas": desp, "saldo": rec - desp, "total": len(df)}

def resumo_por_categoria(df: pd.DataFrame, tipo: str) -> pd.DataFrame:
    """Agrupa por categoria para o tipo informado."""
    if df.empty:
        return pd.DataFrame()
    filtrado = df[df["tipo"] == tipo].copy()
    if filtrado.empty:
        return pd.DataFrame()
    agg = (filtrado.groupby(["categoria_nome","categoria_icone"])["valor"]
           .sum().reset_index()
           .sort_values("valor", ascending=False))
    total = agg["valor"].sum()
    agg["pct"] = (agg["valor"] / total * 100).round(1) if total else 0
    agg["valor_fmt"] = agg["valor"].apply(fmt_brl)
    return agg

def resumo_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega receitas e despesas por mês."""
    if df.empty:
        return pd.DataFrame()
    d = df.copy()
    d["mes"] = d["data"].astype(str).str[:7]
    agg = d.groupby(["mes","tipo"])["valor"].sum().unstack(fill_value=0).reset_index()
    if "receita" not in agg.columns:
        agg["receita"] = 0.0
    if "despesa" not in agg.columns:
        agg["despesa"] = 0.0
    agg["saldo"] = agg["receita"] - agg["despesa"]
    agg["mes_label"] = agg["mes"].apply(mes_label)
    return agg.sort_values("mes")

def evolucao_saldo(df: pd.DataFrame) -> pd.DataFrame:
    """Saldo acumulado dia a dia."""
    if df.empty:
        return pd.DataFrame()
    d = df.copy()
    d["valor_signed"] = d.apply(
        lambda r: r["valor"] if r["tipo"] == "receita" else -r["valor"], axis=1)
    d = d.sort_values("data")
    agg = d.groupby("data")["valor_signed"].sum().reset_index()
    agg["saldo_acum"] = agg["valor_signed"].cumsum()
    return agg
