# app.py
import streamlit as st
import pandas as pd
import math
from datetime import datetime, timedelta, date
from io import BytesIO

st.set_page_config(page_title="Tam Vardiya Planlayıcı", layout="wide")
st.title("🏭 Tam Vardiya & Personel Planlayıcı (12 / 35 / 51 vardiyası)")

# -------------------------
# Sabitler
# -------------------------
VARDIYA_ORDER = ["12 vardiyası", "35 vardiyası", "51 vardiyası"]
VARDIYA_INFO = {
    "12 vardiyası": {"label": "12 vardiyası", "hours": 7.5, "range": "08:00-16:00"},
    "35 vardiyası": {"label": "35 vardiyası", "hours": 7.5, "range": "16:00-24:00"},
    "51 vardiyası": {"label": "51 vardiyası", "hours": 7.5, "range": "24:00-08:00"},
}
DAILY_FTE_HOURS = 7.5   # 1 FTE = 7.5 saat (günlük)
WEEKLY_FTE_HOURS = 42.5 # 1 FTE haftalık = 42.5 saat
SCHED_DAYS_DEFAULT = 7

# -------------------------
# Session state init
# -------------------------
if "machines" not in st.session_state:
    st.session_state["machines"] = pd.DataFrame(columns=[
        "Makine", "Saatlik Kapasite (kg/saat)", "Vardiya Başına Kişi", "Toplam Personel"
    ])

if "personnel" not in st.session_state:
    # dict: machine -> list of person names (may be empty)
    st.session_state["personnel"] = {}

if "rr_index" not in st.session_state:
    st.session_state["rr_index"] = {}  # rotation start index per machine

if "plan" not in st.session_state:
    st.session_state["plan"] = pd.DataFrame(columns=["Ürün", "Miktar (kg)", "Makine", "Teslim Tarihi"])

# -------------------------
# Sol panel: Makine girişi
# -------------------------
st.sidebar.header("1) Makine & Personel Ayarları")

with st.sidebar.expander("Makine ekle"):
    m_name = st.text_input("Makine adı (ör. Ergin)")
    m_capacity = st.number_input("Saatlik kapasite (kg/saat)", min_value=1.0, value=250.0)
    m_req_per_shift = st.number_input("Vardiya başına gerekli kişi", min_value=1, value=3)
    m_total_person = st.number_input("Bölümde toplam personel (placeholder)", min_value=0, value=0)
    add_m = st.button("➕ Makine ekle")
    if add_m:
        if not m_name.strip():
            st.sidebar.error("Makine adı boş olamaz.")
        else:
            new = pd.DataFrame([[m_name.strip(), float(m_capacity),
                                 int(m_req_per_shift), int(m_total_person)]],
                               columns=st.session_state["machines"].columns)
            st.session_state["machines"] = pd.concat([st.session_state["machines"], new], ignore_index=True)
            # ensure personnel dict & rr index exist
            st.session_state["personnel"].setdefault(m_name.strip(), [])
            st.session_state["rr_index"].setdefault(m_name.strip(), 0)
            st.sidebar.success(f"{m_name} eklendi.")

# show machines
st.sidebar.markdown("**Mevcut makineler**")
if not st.session_state["machines"].empty:
    st.sidebar.dataframe(st.session_state["machines"], use_container_width=True)
else:
    st.sidebar.info("Henüz makine yok (soldan ekle).")

# -------------------------
# Sol panel: Personel ekle (makine bazlı)
# -------------------------
with st.sidebar.expander("Makineye personel ekle / placeholder oluştur"):
    sel_machine = st.selectbox("Hangi makineye personel ekleyeceksin?", options=st.session_state["machines"]["Makine"].tolist() if not st.session_state["machines"].empty else [])
    person_name = st.text_input("Personel ismi (boşsa placeholder oluşturulur)")
    add_person = st.button("➕ Personel ekle")
    if add_person:
        if not sel_machine:
            st.sidebar.error("Önce makine ekleyin.")
        else:
            if person_name.strip():
                lst = st.session_state["personnel"].get(sel_machine, [])
                lst.append(person_name.strip())
                st.session_state["personnel"][sel_machine] = lst
                st.session_state["rr_index"].setdefault(sel_machine, 0)
                st.sidebar.success(f"{person_name.strip()} eklendi -> {sel_machine}")
            else:
                # create placeholders up to 'Toplam Personel' if provided
                total = int(st.session_state["machines"][st.session_state["machines"]["Makine"]==sel_machine]["Toplam Personel"].iloc[0])
                existing = len(st.session_state["personnel"].get(sel_machine, []))
                to_create = max(0, total - existing)
                if to_create <= 0:
                    # create one placeholder
                    ph = f"{sel_machine}-Personel{existing+1}"
                    st.session_state["personnel"].setdefault(sel_machine, []).append(ph)
                    st.sidebar.success(f"Placeholder {ph} eklendi.")
                else:
                    for i in range(to_create):
                        ph = f"{sel_machine}-Personel{existing+1+i}"
                        st.session_state["personnel"].setdefault(sel_machine, []).append(ph)
                    st.sidebar.success(f"{to_create} placeholder eklendi -> {sel_machine}")

# show personnel summary
st.sidebar.markdown("**Personel (makine bazlı)**")
for mac, ppl in st.session_state["personnel"].items():
    st.sidebar.write(f"{mac}: {len(ppl)} kişi")

# -------------------------
# Orta bölüm: Üretim Planı girişi
# -------------------------
st.header("2) Üretim Planı (Haftalık)")
with st.form("plan_form", clear_on_submit=True):
    p_col1, p_col2, p_col3, p_col4 = st.columns([3,2,2,2])
    with p_col1:
        p_name = st.text_input("Ürün adı")
    with p_col2:
        p_qty = st.number_input("Miktar (kg)", min_value=1.0, value=1000.0)
    with p_col3:
        p_machine = st.selectbox("Makine seç", options=st.session_state["machines"]["Makine"].tolist() if not st.session_state["machines"].empty else [])
    with p_col4:
        p_due = st.date_input("Teslim tarihi (opsiyonel)", value=date.today())
    p_add = st.form_submit_button("➕ Plan ekle")
    if p_add:
        if not p_name or not p_machine:
            st.warning("Ürün adı ve makine seçimi gerekli.")
        else:
            new = pd.DataFrame([[p_name.strip(), float(p_qty), p_machine, p_due.strftime("%Y-%m-%d")]],
                               columns=st.session_state["plan"].columns)
            st.session_state["plan"] = pd.concat([st.session_state["plan"], new], ignore_index=True)
            st.success(f"{p_name} planına eklendi -> {p_machine}")

st.subheader("Mevcut Üretim Planı")
st.dataframe(st.session_state["plan"], use_container_width=True)

# -------------------------
# Plan oluşturma parametreleri
# -------------------------
st.header("3) Plan Oluşturma Ayarları")
start_date = st.date_input("Plan başlangıç tarihi", value=date.today())
num_days = st.number_input("Kaç günlük plan yapılacak? (gün)", min_value=1, max_value=28, value=SCHED_DAYS_DEFAULT)

# -------------------------
# Yardımcı fonksiyonlar
# -------------------------
def make_placeholder_persons(machine_name, total):
    """Ensure session_state personnel list has 'total' persons (create placeholders if needed)."""
    lst = st.session_state["personnel"].get(machine_name, [])
    while len(lst) < total:
        ph = f"{machine_name}-Personel{len(lst)+1}"
        lst.append(ph)
    st.session_state["personnel"][machine_name] = lst
    return lst

def export_df_to_csv_bytes(df):
    towrite = BytesIO()
    df.to_csv(towrite, index=False)
    return towrite.getvalue()

# -------------------------
# PLAN OLUŞTUR butonu
# -------------------------
if st.button("▶️ Planı Oluştur"):
    try:
        if st.session_state["machines"].empty or st.session_state["plan"].empty:
            st.error("Lütfen önce Makine ve Üretim Planı verilerini girin.")
        else:
            # prepare
            df_machines = st.session_state["machines"].copy()
            df_plan = st.session_state["plan"].copy()
            df_plan["Miktar (kg)"] = df_plan["Miktar (kg)"].astype(float)

            # scheduling containers
            slot_rows = []  # each slot: date, vardiya, makine, ürün, saat, req_personel, assigned_names
            person_assignments = {}  # person -> {date_str: shift_label}
            person_week_hours = {}   # person -> accumulated hours in schedule (week window)
            overall_shortages = 0

            # ensure placeholders if needed
            for _, m in df_machines.iterrows():
                machine_name = m["Makine"]
                total_person = int(m["Toplam Personel"])
                # ensure personnel list has placeholders up to total_person
                existing = st.session_state["personnel"].get(machine_name, [])
                if len(existing) < total_person:
                    make_placeholder_persons(machine_name, total_person)
                # init rr index
                st.session_state["rr_index"].setdefault(machine_name, 0)
                # init person_assignments and person_week_hours
                for p in st.session_state["personnel"].get(machine_name, []):
                    person_assignments.setdefault(p, {})
                    person_week_hours.setdefault(p, 0.0)

            # generate schedule slots for each plan item
            for _, plan_row in df_plan.iterrows():
                machine_row = df_machines[df_machines["Makine"] == plan_row["Makine"]].iloc[0]
                machine_name = machine_row["Makine"]
                capacity = float(machine_row["Saatlik Kapasite (kg/saat)"])
                req_per_shift = int(machine_row["Vardiya Başına Kişi"])
                persons_pool = list(st.session_state["personnel"].get(machine_name, []))

                if capacity <= 0:
                    st.warning(f"{machine_name} için kapasite 0 veya hatalı, bu plan atlanacak.")
                    continue

                total_hours_needed = plan_row["Miktar (kg)"] / capacity
                remaining_hours = total_hours_needed
                cur_date = start_date
                shift_index = 0  # 0->12,1->35,2->51

                while remaining_hours > 0:
                    slot_hours = min(VARDIYA_INFO[VARDIYA_ORDER[shift_index]]["hours"], remaining_hours)
                    date_str = cur_date.strftime("%Y-%m-%d")

                    # assign persons for this slot
                    assigned = []
                    shortage = 0
                    pool = persons_pool[:]  # local copy
                    if pool:
                        rr_start = st.session_state["rr_index"].get(machine_name, 0) % max(1, len(pool))
                        idx = rr_start
                        tried = 0
                        # try to select req_per_shift distinct persons respecting:
                        # - not already assigned on same date
                        # - not exceeding weekly hours (WEEKLY_FTE_HOURS)
                        while len(assigned) < req_per_shift and tried < len(pool) * 2:
                            candidate = pool[idx % len(pool)]
                            assigned_today = person_assignments.get(candidate, {}).get(date_str)
                            candidate_week_hours = person_week_hours.get(candidate, 0.0)
                            # check availability
                            if assigned_today is None and (candidate_week_hours + slot_hours) <= WEEKLY_FTE_HOURS:
                                # assign
                                assigned.append(candidate)
                                person_assignments.setdefault(candidate, {})[date_str] = VARDIYA_ORDER[shift_index]
                                person_week_hours[candidate] = candidate_week_hours + slot_hours
                            idx += 1
                            tried += 1
                        st.session_state["rr_index"][machine_name] = idx % max(1, len(pool))
                        if len(assigned) < req_per_shift:
                            shortage = req_per_shift - len(assigned)
                    else:
                        # no named personnel: create placeholders on the fly (shouldn't happen because we created)
                        shortage = req_per_shift

                    overall_shortages += shortage

                    slot_rows.append({
                        "Tarih": date_str,
                        "Vardiya": VARDIYA_ORDER[shift_index],
                        "Makine": machine_name,
                        "Ürün": plan_row["Ürün"],
                        "Planlanan Saat": round(slot_hours, 2),
                        "Gerekli Kişi": req_per_shift,
                        "Atanan Kişi Sayısı": len(assigned),
                        "Atanan İsimler": ", ".join(assigned) if assigned else ""
                    })

                    remaining_hours -= slot_hours
                    # advance shift/day
                    shift_index = (shift_index + 1) % 3
                    if shift_index == 0:
                        cur_date = cur_date + timedelta(days=1)

            # Build slot df
            df_slots = pd.DataFrame(slot_rows)
            if df_slots.empty:
                st.info("Oluşturulan vardiya slotu yok.")
            else:
                st.subheader("📅 Vardiya Slotları (Detaylı)")
                st.dataframe(df_slots, use_container_width=True)

            # -----------------------------
            # Makine günlük & haftalık özet hesapları
            # -----------------------------
            # determine date range used
            if not df_slots.empty:
                min_date = min(pd.to_datetime(df_slots["Tarih"]))
                max_date = max(pd.to_datetime(df_slots["Tarih"]))
                date_range = pd.date_range(min_date, max_date)
            else:
                date_range = pd.date_range(start_date, start_date + timedelta(days=num_days-1))

            # daily summary per machine
            daily_rows = []
            weekly_rows = []
            for _, m in df_machines.iterrows():
                machine_name = m["Makine"]
                total_personnel = len(st.session_state["personnel"].get(machine_name, []))
                # daily loop
                for d in date_range:
                    dstr = d.strftime("%Y-%m-%d")
                    day_slots = df_slots[(df_slots["Makine"]==machine_name) & (df_slots["Tarih"]==dstr)]
                    scheduled_hours = day_slots["Planlanan Saat"].sum() if not day_slots.empty else 0.0
                    available_person_hours = total_personnel * DAILY_FTE_HOURS
                    mesai_needed = max(0.0, scheduled_hours - available_person_hours)
                    daily_fte = scheduled_hours / DAILY_FTE_HOURS if DAILY_FTE_HOURS>0 else 0.0
                    daily_rows.append({
                        "Makine": machine_name,
                        "Tarih": dstr,
                        "Planlanan Saat (saat)": round(scheduled_hours,2),
                        "Mevcut Personel (adet)": total_personnel,
                        "Mevcut Personel Saat (günlük)": round(available_person_hours,2),
                        "Mesai İhtiyacı (saat)": round(mesai_needed,2),
                        "Günlük FTE": round(daily_fte,2)
                    })
                # weekly summary
                machine_slots = df_slots[df_slots["Makine"]==machine_name]
                weekly_scheduled = machine_slots["Planlanan Saat"].sum() if not machine_slots.empty else 0.0
                weekly_available_hours = total_personnel * WEEKLY_FTE_HOURS
                weekly_mesai = max(0.0, weekly_scheduled - weekly_available_hours)
                weekly_fte = weekly_scheduled / WEEKLY_FTE_HOURS if WEEKLY_FTE_HOURS>0 else 0.0
                weekly_rows.append({
                    "Makine": machine_name,
                    "Haftalık Planlanan Saat": round(weekly_scheduled,2),
                    "Haftalık Mevcut Personel Saat": round(weekly_available_hours,2),
                    "Haftalık Mesai (saat)": round(weekly_mesai,2),
                    "Haftalık FTE": round(weekly_fte,2)
                })

            df_daily = pd.DataFrame(daily_rows)
            df_weekly = pd.DataFrame(weekly_rows)

            # cumulative totals
            total_weekly_scheduled = df_weekly["Haftalık Planlanan Saat"].sum() if not df_weekly.empty else 0.0
            total_weekly_available = df_weekly["Haftalık Mevcut Personel Saat"].sum() if not df_weekly.empty else 0.0
            total_weekly_mesai = max(0.0, total_weekly_scheduled - total_weekly_available)
            total_weekly_fte = df_weekly["Haftalık FTE"].sum() if not df_weekly.empty else 0.0

            # display summaries
            st.subheader("🔎 Makine Günlük Özeti")
            st.dataframe(df_daily, use_container_width=True)

            st.subheader("📈 Makine Haftalık Özeti")
            st.dataframe(df_weekly, use_container_width=True)

            st.markdown("**Kümülatif Toplamlar**")
            st.write({
                "Toplam Haftalık Planlanan Saat": round(total_weekly_scheduled,2),
                "Toplam Haftalık Mevcut Personel Saat": round(total_weekly_available,2),
                "Toplam Haftalık Mesai (saat)": round(total_weekly_mesai,2),
                "Toplam Haftalık FTE": round(total_weekly_fte,2),
                "Toplam Atanmayan Pozisyon (shortages)": int(overall_shortages)
            })

            # -----------------------------
            # Personel x tarih matrisi (makine bazlı)
            # -----------------------------
            st.subheader("🧾 Personel × Tarih Matrisi (Makine Bazlı)")
            if not df_slots.empty:
                all_dates = sorted(df_slots["Tarih"].unique())
            else:
                all_dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(num_days)]

            for _, m in df_machines.iterrows():
                mac = m["Makine"]
                st.markdown(f"### {mac}")
                persons = st.session_state["personnel"].get(mac, [])
                # if no persons, create placeholders
                if not persons:
                    persons = make_placeholder_persons(mac, int(m["Toplam Personel"]))
                mat = pd.DataFrame(index=persons, columns=all_dates).fillna("")
                # fill from person_assignments
                for p in persons:
                    for d in all_dates:
                        val = person_assignments.get(p, {}).get(d)
                        if val:
                            mat.at[p, d] = val
                        else:
                            mat.at[p, d] = ""
                # show matrix with empty names allowed (user can re-run and edit persons)
                st.dataframe(mat, use_container_width=True)

            # -----------------------------
            # Download buttons
            # -----------------------------
            st.subheader("💾 İndir")
            if not df_slots.empty:
                csv_slots = export_df_to_csv_bytes(df_slots)
                st.download_button("CSV: Vardiya Slotları indir", data=csv_slots, file_name="vardiya_slotlari.csv", mime="text/csv")
            if not df_daily.empty:
                csv_daily = export_df_to_csv_bytes(df_daily)
                st.download_button("CSV: Günlük özet indir", data=csv_daily, file_name="gunluk_ozet.csv", mime="text/csv")
            if not df_weekly.empty:
                csv_weekly = export_df_to_csv_bytes(df_weekly)
                st.download_button("CSV: Haftalık özet indir", data=csv_weekly, file_name="haftalik_ozet.csv", mime="text/csv")

            if overall_shortages > 0:
                st.warning(f"Toplam atanmayan pozisyon sayısı: {overall_shortages} (personel yetersizliği)")
            else:
                st.success("Tüm vardiya pozisyonları atanabildi (mevcut personel ile).")

    except Exception as exc:
        st.exception(exc)
        st.error("Plan oluşturma sırasında hata oluştu. Lütfen hatayı bana gönder, birlikte düzelteyim.")
