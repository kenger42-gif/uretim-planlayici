import streamlit as st
import pandas as pd
import math
from datetime import datetime, timedelta, date

st.set_page_config(page_title="Gelişmiş Vardiya Planlayıcı", layout="wide")
st.title("🏭 Gelişmiş Vardiya & Personel Planlayıcı")

# ---- session state init ----
if "machines" not in st.session_state:
    st.session_state["machines"] = pd.DataFrame(columns=[
        "Makine", "Kapasite (kg/saat)", "Vardiya Başına Kişi", "Toplam Personel"
    ])
if "plan" not in st.session_state:
    st.session_state["plan"] = pd.DataFrame(columns=["Ürün", "Miktar (kg)", "Makine"])
if "personnel" not in st.session_state:
    # personnel: dict: makine -> [isim, ...]
    st.session_state["personnel"] = {}
if "rr_index" not in st.session_state:
    # for round-robin per machine
    st.session_state["rr_index"] = {}

st.write("Not: önce **Makine** ve **Personel** gir, sonra **Üretim Planı** ekle ve 'Planı Oluştur' butonuna bas.")

# -------------------------
# 1) Makine girişi
# -------------------------
st.header("1️⃣ Makine Bilgileri")
with st.form("makine_form", clear_on_submit=True):
    col1, col2, col3, col4 = st.columns([2,2,2,2])
    with col1:
        m_name = st.text_input("Makine Adı")
    with col2:
        m_capacity = st.number_input("Kapasite (kg/saat)", min_value=1.0, value=250.0)
    with col3:
        m_per_shift = st.number_input("Vardiya Başına Kişi", min_value=1, value=3)
    with col4:
        m_total_person = st.number_input("Bölümde Toplam Personel (adet)", min_value=0, value=0)
    m_add = st.form_submit_button("Makine Ekle")

if m_add and m_name:
    yeni = pd.DataFrame([[m_name, m_capacity, int(m_per_shift), int(m_total_person)]],
                        columns=st.session_state["machines"].columns)
    st.session_state["machines"] = pd.concat([st.session_state["machines"], yeni], ignore_index=True)
    # initialize personnel list & rr index if not exists
    if m_name not in st.session_state["personnel"]:
        st.session_state["personnel"][m_name] = []
    if m_name not in st.session_state["rr_index"]:
        st.session_state["rr_index"][m_name] = 0
    st.success(f"{m_name} eklendi.")

st.dataframe(st.session_state["machines"])

# -------------------------
# 1b) Personel girişi (makine bazlı)
# -------------------------
st.subheader("1️⃣b Makineye Personel Ekle (isim bazlı)")
colA, colB = st.columns([2,3])
with colA:
    sel_machine_for_person = st.selectbox("Personel eklenecek makine", options=st.session_state["machines"]["Makine"].tolist() if not st.session_state["machines"].empty else [])
with colB:
    with st.form("personel_form", clear_on_submit=True):
        if sel_machine_for_person:
            person_name = st.text_input("Personel İsmi")
            add_person = st.form_submit_button("Personel Ekle")
            if add_person and person_name:
                lst = st.session_state["personnel"].get(sel_machine_for_person, [])
                lst.append(person_name)
                st.session_state["personnel"][sel_machine_for_person] = lst
                st.success(f"{person_name} -> {sel_machine_for_person}")
                # keep rr index
                if sel_machine_for_person not in st.session_state["rr_index"]:
                    st.session_state["rr_index"][sel_machine_for_person] = 0

# show personnel lists
if st.session_state["personnel"]:
    for mac, ppl in st.session_state["personnel"].items():
        st.write(f"**{mac}** personel ({len(ppl)}): ", ", ".join(ppl) if ppl else "—")

# -------------------------
# 2) Üretim planı girişi
# -------------------------
st.header("2️⃣ Üretim Planı")
with st.form("plan_form", clear_on_submit=True):
    p_col1, p_col2, p_col3 = st.columns([3,2,3])
    with p_col1:
        p_name = st.text_input("Ürün Adı")
