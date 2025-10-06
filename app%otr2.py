
# SAIPMP: Sistem Analisis Indeks Pemberat Mata Pelajaran
# Template Streamlit (Python)
# Cara jalankan di terminal:  streamlit run app.py

import io
import time
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="SiPP - IPMP Analyzer", page_icon="📊", layout="wide")

# -----------------------------
# Utilities
# -----------------------------
EXPECTED_COLUMNS = {
    "Mata Pelajaran": ["Mata Pelajaran", "Subjek", "Subject"],
    "Bil. Daftar": ["Bil. Daftar", "Daftar", "Bil Daftar", "Registered"],
    "Bil. Ambil": ["Bil. Ambil", "Ambil", "Bil Ambil", "Taken"],
    "% L PPC": ["% L PPC", "PPC"],
    "% L OTR2": ["% L OTR2", "OTR2"],
}

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Try to match incoming columns to expected names."""
    mapping = {}
    for target, options in EXPECTED_COLUMNS.items():
        for opt in options:
            for col in df.columns:
                if col.strip().lower() == opt.strip().lower():
                    mapping[col] = target
                    break
    df = df.rename(columns=mapping)
    return df

def compute_ipmp(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Ensure needed columns exist
    needed = ["Mata Pelajaran", "Bil. Ambil", "% L PPC", "% L OTR2"]
    for c in needed:
        if c not in df.columns:
            raise ValueError(f"Kolum '{c}' tiada dalam data.")
    # Coerce numerics
    for c in ["Bil. Daftar", "Bil. Ambil", "% L PPC", "% L OTR2"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # Calculations
    df["Beza Peratus (PPC - OTR2)"] = df["% L PPC"] - df["% L OTR2"]
    total_ambil = df["Bil. Ambil"].sum()
    df["Pemberat"] = np.where(total_ambil > 0, df["Bil. Ambil"] / total_ambil, 0.0)
    df["IPMP"] = df["Beza Peratus (PPC - OTR2)"] * df["Pemberat"]

    # Ranking (tinggi ke rendah)
    df["Ranking"] = df["IPMP"].rank(method="min", ascending=False).astype(int)

    # Susun kolum
    cols = [
        "Mata Pelajaran", "Bil. Daftar", "Bil. Ambil",
        "% L PPC", "% L OTR2",
        "Beza Peratus (PPC - OTR2)", "Pemberat", "IPMP", "Ranking"
    ]
    df = df[[c for c in cols if c in df.columns]].sort_values("Ranking")
    return df

def style_ipmp(val):
    # Simple color scale for IPMP: positive -> greenish, negative -> reddish
    try:
        v = float(val)
    except:
        return ""
    if v > 0:
        return "background-color: #E8F5E9"  # light green
    elif v < 0:
        return "background-color: #FFEBEE"  # light red
    return ""

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("📁 Data & Tetapan")
uploaded = st.sidebar.file_uploader("Muat naik fail (Excel/CSV)", type=["xlsx", "xls", "csv"])
example_btn = st.sidebar.button("Gunakan data contoh")
st.sidebar.markdown("---")
st.sidebar.caption("Kolum diperlukan: Mata Pelajaran, Bil. Ambil, % L PPC, % L OTR2. (Bil. Daftar opsyenal).")

# -----------------------------
# Load dataset
# -----------------------------
df_raw = None
if uploaded:
    if uploaded.name.lower().endswith(".csv"):
        df_raw = pd.read_csv(uploaded)
    else:
        df_raw = pd.read_excel(uploaded)
elif example_btn:
    df_raw = pd.read_csv("sample_data.csv")

# -----------------------------
# Main UI
# -----------------------------
st.title("📊 SiPP — Sistem Indeks Pemberat Mata Pelajaran")
st.markdown("Muat naik data dan jana **IPMP** secara automatik.")

if df_raw is None:
    st.info("Sila muat naik fail Excel/CSV atau klik **Gunakan data contoh** di sebelah kiri.")
    st.stop()

# Standardize & compute
df_raw = standardize_columns(df_raw)
try:
    df_result = compute_ipmp(df_raw)
except Exception as e:
    st.error(f"Ralat pengiraan: {e}")
    st.stop()

# -----------------------------
# KPI Cards
# -----------------------------
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Jumlah Subjek", len(df_result))
with col2:
    st.metric("Jumlah Murid (Ambil)", int(df_result["Bil. Ambil"].sum()))
with col3:
    st.metric("Purata IPMP", round(df_result["IPMP"].mean(), 4))
with col4:
    best_row = df_result.sort_values("IPMP", ascending=False).iloc[0]
    st.metric("Subjek Terbaik", f"{best_row['Mata Pelajaran']}", delta=round(best_row['IPMP'], 4))
with col5:
    worst_row = df_result.sort_values("IPMP", ascending=True).iloc[0]
    st.metric("Subjek Terlemah", f"{worst_row['Mata Pelajaran']}", delta=round(worst_row['IPMP'], 4))

st.markdown("---")

# -----------------------------
# Table
# -----------------------------
st.subheader("Hasil Pengiraan")
st.dataframe(df_result, use_container_width=True, hide_index=True)

# -----------------------------
# Charts
# -----------------------------
st.subheader("Ranking IPMP Mengikut Subjek")
chart_df = df_result.sort_values("IPMP", ascending=False)
fig = px.bar(chart_df, x="Mata Pelajaran", y="IPMP", text="Ranking",
             title="IPMP per Subjek (Bar Tinggi = Sumbangan Lebih Baik)")
fig.update_traces(textposition="outside")
fig.update_layout(xaxis_title="", yaxis_title="IPMP", margin=dict(t=60, b=20))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Perbandingan GPMP (OTR2 vs PPC)")
long_df = df_result.melt(id_vars=["Mata Pelajaran"], value_vars=["% L OTR2", "% L PPC"],
                         var_name="Jenis", value_name="GPMP")
fig2 = px.line(long_df, x="Mata Pelajaran", y="GPMP", color="Jenis",
               markers=True, title="GPMP % L OTR2 vs % L PPC Mengikut Subjek")
fig2.update_layout(xaxis_title="", yaxis_title="GPMP", margin=dict(t=60, b=20))
st.plotly_chart(fig2, use_container_width=True)

# -----------------------------
# Downloads
# -----------------------------
st.markdown("---")
st.subheader("Muat Turun Laporan")
export_cols = df_result.columns
csv_bytes = df_result.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Muat turun CSV", data=csv_bytes, file_name="IPMP_report.csv", mime="text/csv")

# Export to Excel in-memory
import io
output = io.BytesIO()
with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
    df_result.to_excel(writer, sheet_name="IPMP", index=False)
st.download_button("⬇️ Muat turun Excel", data=output.getvalue(),
                   file_name="IPMP_report.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.caption("© SiPP — Sistem Indeks Pemberat Mata Pelajaran")
