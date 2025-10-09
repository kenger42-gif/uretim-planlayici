# app.py - Güçlendirilmiş Vardiya Planlayıcı (hata dayanıklı sürüm)
import streamlit as st
import pandas as pd
import math
from datetime import datetime, timedelta, date

st.set_page_config(page_title="Gelişmiş Vardiya Planlayıcı", layout="wide")
st.title("🏭 Gelişmiş Vardiya & Personel Planlayıcı — Stabil Sürüm")

# -------------------------
# Session State init
# -------------------------
if "machines" not in st.session_state:
    st.session_state["machines"] = pd.DataFrame(columns=[
        "Makine", "Kapasite (kg/saat)", "Vardiya Başına Kişi", "Toplam Personel"
    ])
if "plan" not in st.session_state:
    st.session_state["plan"] = pd.DataFrame(columns=["Ürün", "Miktar (kg)", "Makine"])
if "personnel" not in st.session_state:
    st.session_state["personnel"] = {}
if "rr_index" not in st.session_state:
    st.session_state["rr_index"] = {}

st.write("Not: önce **Makine** ve **Personel** gir, sonra **Üretim Planı** ekle ve 'Planı Oluştur' butonuna bas.")

# -------------------------
# 1) Makine girişi
# -------------------------
st.header("1️⃣ Makine Bilgileri")
with st.form("makine_form", clear_on_submit=True):
    col1, col2, col3, col4 = st.columns([2,2,2,2])
    with col1:
        m_name = st.text_input("Makine Adı", key="m_name")
    with col2:
        m_capacity = st.number_input("Kapasite (kg/saat)", min_value=1.0, value=250.0, key="m_capacity")
    with col3:
        m_per_shift = st.number_input("Vardiya Başına Kişi", min_value=1, value=3, key="m_per_shift")
    with col4:
        m_total_person = st.number_input("Bölümde Toplam Personel (adet)", min_value=0, value=0, key="m_total_person")
    m_add = st.form_submit_button("Makine Ekle")
if m_add:
    if not m_name:
        st.warning("Makine adı boş bırakılamaz.")
    else:
        yeni = pd.DataFrame([[m_name, float(m_capacity), int(m_per_shift), int(m_total_person)]],
                            columns=st.session_state["machines"].columns)
        st.session_state["machines"] = pd.concat([st.session_state["machines"], yeni], ignore_index=True)
        if m_name not in st.session_state["personnel"]:
            st.session_state["personnel"][m_name] = []
        if m_name not in st.session_state["rr_index"]:
            st.session_state["rr_index"][m_name] = 0
        st.success(f"{m_name} başarıyla eklendi.")

st.dataframe(st.session_state["machines"])

# -------------------------
# 1b) Personel girişi (makine bazlı)
# -------------------------
st.subheader("1️⃣b Makineye Personel Ekle (isim bazlı)")
machine_options = st.session_state["machines"]["Makine"].tolist() if not st.session_state["machines"].empty else []
colA, colB = st.columns([2,3])
with colA:
    sel_machine_for_person = st.selectbox("Personel eklenecek makine", options=machine_options, key="sel_machine_for_person")
with colB:
    with st.form("personel_form", clear_on_submit=True):
        person_name = st.text_input("Personel İsmi", key="person_name")
        add_person = st.form_submit_button("Personel Ekle")
        if add_person:
            if not sel_machine_for_person:
                st.warning("Önce bir makine seçin.")
            elif not person_name:
                st.warning("Personel ismi boş olamaz.")
            else:
                lst = st.session_state["personnel"].get(sel_machine_for_person, [])
                lst.append(person_name)
                st.session_state["personnel"][sel_machine_for_person] = lst
                if sel_machine_for_person not in st.session_state["rr_index"]:
                    st.session_state["rr_index"][sel_machine_for_person] = 0
                st.success(f"{person_name} eklendi -> {sel_machine_for_person}")

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
        p_name = st.text_input("Ürün Adı", key="p_name")
    with p_col2:
        p_amount = st.number_input("Miktar (kg)", min_value=1.0, value=1000.0, key="p_amount")
    with p_col3:
        # Güvenli selectbox: makine listesi boşsa bilgilendir
        p_machine = None
        if machine_options:
            p_machine = st.selectbox("Makine Seç", options=machine_options, key="p_machine")
        else:
            st.info("Önce makine ekleyin, ardından üretim planı ekleyebilirsiniz.")
    p_add = st.form_submit_button("Üretim Planına Ekle")

if p_add:
    if not p_name:
        st.warning("Ürün adı boş bırakılamaz.")
    elif not p_machine:
        st.warning("Lütfen önce bir makine ekleyin ve seçim yapın.")
    else:
        yeni = pd.DataFrame([[p_name, float(p_amount), p_machine]], columns=st.session_state["plan"].columns)
        st.session_state["plan"] = pd.concat([st.session_state["plan"], yeni], ignore_index=True)
        st.success(f"{p_name} üretim planına eklendi -> {p_machine}")

st.dataframe(st.session_state["plan"])

# -------------------------
# 3) Plan oluşturma & vardiya takvimi üretimi
# -------------------------
st.header("3️⃣ Plan Hesaplama ve Vardiya Takvimi")
start_date = st.date_input("Plan başlangıç tarihi", value=date.today())
if st.button("Planı Oluştur"):
    try:
        df_machines = st.session_state["machines"]
        df_plan = st.session_state["plan"]

        if df_machines.empty or df_plan.empty:
            st.error("Lütfen önce Makine ve Üretim Planı verilerini eksiksiz giriniz.")
        else:
            vardiya_slots = []
            person_assignments = {}
            for mac in df_machines["Makine"].tolist():
                if mac not in st.session_state["personnel"]:
                    st.session_state["personnel"][mac] = []
                if mac not in st.session_state["rr_index"]:
                    st.session_state["rr_index"][mac] = 0
                for p in st.session_state["personnel"].get(mac, []):
                    person_assignments.setdefault(p, {})

            overall_shortages = 0

            for _, plan_row in df_plan.iterrows():
                mac_row = df_machines[df_machines["Makine"] == plan_row["Makine"]].iloc[0]
                capacity = float(mac_row["Kapasite (kg/saat)"])
                req_per_shift = int(mac_row["Vardiya Başına Kişi"])
                persons_pool = list(st.session_state["personnel"].get(plan_row["Makine"], []))

                if capacity <= 0:
                    st.warning(f"{plan_row['Makine']} için kapasite sıfır veya hatalı: atlama yapılıyor.")
                    continue

                total_hours = float(plan_row["Miktar (kg)"]) / capacity
                remaining = total_hours
                cur_date = datetime.combine(start_date, datetime.min.time()).date()
                shift_num = 1

                while remaining > 0:
                    slot_hours = min(8, remaining)
                    assigned = []
                    shortage = 0
                    if persons_pool:
                        rr_start = st.session_state["rr_index"].get(plan_row["Makine"], 0) % max(1, len(persons_pool))
                        idx = rr_start
                        tried = 0
                        while len(assigned) < req_per_shift and tried < len(persons_pool)*2:
                            candidate = persons_pool[idx % len(persons_pool)]
                            if person_assignments.get(candidate, {}).get(cur_date.strftime("%d.%m.%Y")) is None:
                                assigned.append(candidate)
                                person_assignments.setdefault(candidate, {})[cur_date.strftime("%d.%m.%Y")] = f"V{shift_num}@{plan_row['Makine']}"
                            idx += 1
                            tried += 1
                        st.session_state["rr_index"][plan_row["Makine"]] = idx % max(1, len(persons_pool))
                        if len(assigned) < req_per_shift:
                            shortage = req_per_shift - len(assigned)
                    else:
                        shortage = req_per_shift

                    if shortage > 0:
                        overall_shortages += shortage

                    vardiya_slots.append({
                        "Tarih": cur_date.strftime("%d.%m.%Y"),
                        "Vardiya": shift_num,
                        "Makine": plan_row["Makine"],
                        "Ürün": plan_row["Ürün"],
                        "Planlanan Saat": round(slot_hours,2),
                        "Gerekli Kişi": req_per_shift,
                        "Atanan Kişi Sayısı": len(assigned),
                        "Atanan İsimler": ", ".join(assigned) if assigned else ""
                    })

                    remaining -= slot_hours
                    if shift_num == 3:
                        shift_num = 1
                        cur_date = cur_date + timedelta(days=1)
                    else:
                        shift_num += 1

            df_slots = pd.DataFrame(vardiya_slots)
            st.success("Vardiya takvimi oluşturuldu ✅")
            st.subheader("📅 Vardiya Slotları")
            st.dataframe(df_slots)

            # Personel x tarih matrisi
            st.subheader("🔢 Personel × Tarih Matrisi (makine bazlı)")
            if not df_slots.empty:
                dates = sorted(df_slots["Tarih"].unique(), key=lambda x: datetime.strptime(x, "%d.%m.%Y"))
            else:
                dates = []

            for mac in df_machines["Makine"].tolist():
                st.markdown(f"**Makine: {mac}**")
                ppl = st.session_state["personnel"].get(mac, [])
                if not ppl:
                    st.info("Bu makine için girilmiş personel yok.")
                    continue
                mat = pd.DataFrame(index=ppl, columns=dates).fillna("")
                # fill from df_slots 'Atanan İsimler'
                for _, slot in df_slots[df_slots["Makine"]==mac].iterrows():
                    d = slot["Tarih"]
                    vnum = f"V{int(slot['Vardiya'])}"
                    names = [n.strip() for n in str(slot["Atanan İsimler"]).split(",") if n.strip()]
                    for n in names:
                        if n in mat.index and d in mat.columns:
                            # if already assigned mark as double (shouldn't happen by rotation rule)
                            if mat.at[n,d]:
                                mat.at[n,d] += f";{vnum}"
                            else:
                                mat.at[n,d] = vnum
                st.dataframe(mat)

            # Summary shortages
            if overall_shortages > 0:
                st.warning(f"Toplam atanmayan (personel yetersizliği nedeniyle) pozisyon sayısı: {overall_shortages}")
            else:
                st.info("Tüm vardiya pozisyonları atandı (mevcut personel ile).")

    except Exception as e:
        st.exception(e)
        st.error("Plan oluşturma sırasında bir hata oluştu. Debug bilgilerini aşağıda kontrol et.")
        with st.expander("Debug: session_state ve kısa snapshot"):
            st.write("machines:", st.session_state.get("machines"))
            st.write("plan:", st.session_state.get("plan"))
            st.write("personnel keys:", list(st.session_state.get("personnel", {}).keys()))
            st.write("rr_index:", st.session_state.get("rr_index"))

st.markdown("---")
st.caption("İpucu: Makineye gerçek personel isimlerini eklemek en sağlıklı sonucu verir. Geliştirme: takvim/Gantt görselleştirme, izinler, tercih günleri eklenebilir.")
