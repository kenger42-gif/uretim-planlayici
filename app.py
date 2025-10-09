# app.py — Güçlendirilmiş ve detaylı hesaplama ile tam vardiya planlayıcı
import streamlit as st
import pandas as pd
import math
from datetime import datetime, timedelta, date
from io import BytesIO

st.set_page_config(page_title="Detaylı Vardiya Planlayıcı", layout="wide")
st.title("🏭 Detaylı Üretim & Vardiya Planlayıcı (12/35/51 vardiyası)")

# ---------- Sabitler / Varsayılanlar ----------
VARDIYA_ORDER = ["12 vardiyası", "35 vardiyası", "51 vardiyası"]
VARDIYA_INFO = {
    "12 vardiyası": {"label": "12 vardiyası", "hours": 8.0, "range": "08:00-16:00"},
    "35 vardiyası": {"label": "35 vardiyası", "hours": 8.0, "range": "16:00-24:00"},
    "51 vardiyası": {"label": "51 vardiyası", "hours": 8.0, "range": "24:00-08:00"},
}
# Not: vardiya süresini 8 saat aldım (08-16 gibi). Eğer 7.5 istiyorsan sidebar'dan değiş.
DEFAULT_DAILY_FTE_HOURS = 7.5   # 1 FTE = günlük (kullanıcı ayarlanabilir)
DEFAULT_WEEKLY_FTE_HOURS = 42.5 # 1 FTE = haftalık (kullanıcı ayarlanabilir)
DEFAULT_OVERTIME_PER_PERSON = 3.5  # eğer mesai gerekiyorsa kişiye düşen ekstra saat (haftalık)

SCHED_MAX_DAYS = 28

# ---------- session_state init ----------
if "machines" not in st.session_state:
    st.session_state["machines"] = pd.DataFrame(columns=[
        "Makine", "Saatlik Kapasite (kg/saat)", "Vardiya Başına Kişi", "Toplam Personel"
    ])
if "personnel" not in st.session_state:
    st.session_state["personnel"] = {}  # makine -> [isim,...]
if "rr_index" not in st.session_state:
    st.session_state["rr_index"] = {}   # rotation index per machine
if "plan" not in st.session_state:
    st.session_state["plan"] = pd.DataFrame(columns=["Ürün", "Miktar (kg)", "Makine", "Teslim Tarihi"])

# ---------- Sidebar: Ayarlar & Veri girişi ----------
st.sidebar.header("🔧 Ayarlar")
shift_hours = st.sidebar.number_input("Vardiya başı saat (örn. 8)", min_value=6.0, max_value=12.0, value=8.0, step=0.5)
daily_fte_hours = st.sidebar.number_input("1 FTE = günlük saat", min_value=1.0, max_value=12.0, value=DEFAULT_DAILY_FTE_HOURS, step=0.5)
weekly_fte_hours = st.sidebar.number_input("1 FTE = haftalık saat", min_value=1.0, max_value=100.0, value=DEFAULT_WEEKLY_FTE_HOURS, step=0.5)
overtime_per_person = st.sidebar.number_input("Kişi başı haftalık max mesai (saat)", min_value=0.0, max_value=40.0, value=DEFAULT_OVERTIME_PER_PERSON, step=0.5)
st.sidebar.write("---")

# Makine ekleme paneli
st.sidebar.header("1) Makine & Bölüm Ayarları")
with st.sidebar.expander("Makine ekle", expanded=True):
    m_name = st.text_input("Makine adı", key="m_name")
    m_capacity = st.number_input("Saatlik kapasite (kg/saat)", min_value=0.1, value=250.0, key="m_capacity")
    m_req_per_shift = st.number_input("Vardiya başına gerekli kişi", min_value=1, value=3, key="m_req")
    m_total_person = st.number_input("Bölümde toplam personel (placeholder)", min_value=0, value=0, key="m_total")
    if st.button("➕ Makine ekle", key="add_machine"):
        if not m_name.strip():
            st.sidebar.error("Makine adı gerekli.")
        else:
            row = pd.DataFrame([[m_name.strip(), float(m_capacity), int(m_req_per_shift), int(m_total_person)]],
                               columns=st.session_state["machines"].columns)
            st.session_state["machines"] = pd.concat([st.session_state["machines"], row], ignore_index=True)
            st.session_state["personnel"].setdefault(m_name.strip(), [])
            st.session_state["rr_index"].setdefault(m_name.strip(), 0)
            st.sidebar.success(f"{m_name.strip()} eklendi.")

st.sidebar.markdown("**Mevcut makineler**")
if not st.session_state["machines"].empty:
    st.sidebar.dataframe(st.session_state["machines"], use_container_width=True)
else:
    st.sidebar.info("Henüz makine eklenmedi.")

# Personel ekleme paneli (makine bazlı)
with st.sidebar.expander("Personel ekle / placeholder oluştur", expanded=False):
    sel_machine = st.selectbox("Makine seç", options=st.session_state["machines"]["Makine"].tolist() if not st.session_state["machines"].empty else [], key="sel_machine")
    p_name = st.text_input("Personel ismi (boşsa placeholder oluşturulur)", key="p_name")
    if st.button("➕ Personel ekle", key="add_person"):
        if not sel_machine:
            st.sidebar.error("Önce makine ekleyin.")
        else:
            if p_name.strip():
                st.session_state["personnel"].setdefault(sel_machine, []).append(p_name.strip())
                st.sidebar.success(f"{p_name.strip()} -> {sel_machine}")
            else:
                # placeholder create up to total person if provided
                total = int(st.session_state["machines"].loc[st.session_state["machines"]["Makine"]==sel_machine, "Toplam Personel"].iloc[0])
                existing = len(st.session_state["personnel"].get(sel_machine, []))
                to_create = max(0, total - existing)
                if to_create == 0:
                    ph = f"{sel_machine}-Personel{existing+1}"
                    st.session_state["personnel"].setdefault(sel_machine, []).append(ph)
                    st.sidebar.success(f"Placeholder {ph} eklendi.")
                else:
                    for i in range(to_create):
                        ph = f"{sel_machine}-Personel{existing+1+i}"
                        st.session_state["personnel"].setdefault(sel_machine, []).append(ph)
                    st.sidebar.success(f"{to_create} placeholder eklendi -> {sel_machine}")

st.sidebar.markdown("**Personel (özet)**")
for mac, ppl in st.session_state["personnel"].items():
    st.sidebar.write(f"- {mac}: {len(ppl)} kişi")

st.sidebar.write("---")
st.sidebar.markdown("⚠️ Not: Sol panelde personel listesini boş bırakabilirsin; uygulama placeholder oluşturur. Sonra isimlerle değiştir.")

# ---------- Ana bölüm: Üretim planı girişi ----------
st.header("2) Üretim Planı (Haftalık) - Ürün ekle")
with st.form("plan_form", clear_on_submit=True):
    c1, c2, c3, c4 = st.columns([3,2,2,2])
    with c1:
        prod_name = st.text_input("Ürün adı", key="prod_name")
    with c2:
        prod_qty = st.number_input("Miktar (kg)", min_value=1.0, value=1000.0, key="prod_qty")
    with c3:
        prod_machine = st.selectbox("Makine seç", options=st.session_state["machines"]["Makine"].tolist() if not st.session_state["machines"].empty else [], key="prod_machine")
    with c4:
        prod_due = st.date_input("Teslim tarihi (opsiyonel)", value=date.today(), key="prod_due")
    add_plan = st.form_submit_button("➕ Plan ekle")
    if add_plan:
        if not prod_name or not prod_machine:
            st.warning("Ürün adı ve makine seçimi gerekli.")
        else:
            row = pd.DataFrame([[prod_name.strip(), float(prod_qty), prod_machine, prod_due.strftime("%Y-%m-%d")]], columns=st.session_state["plan"].columns)
            st.session_state["plan"] = pd.concat([st.session_state["plan"], row], ignore_index=True)
            st.success(f"{prod_name} planına eklendi -> {prod_machine}")

st.subheader("Mevcut Üretim Planı")
st.dataframe(st.session_state["plan"], use_container_width=True)

# ---------- Plan oluşturma ayarları ----------
st.header("3) Plan Oluşturma Ayarları")
start_date = st.date_input("Plan başlangıç tarihi", value=date.today())
num_days = st.number_input("Kaç günlük plan oluşturulsun? (gün)", min_value=1, max_value=SCHED_MAX_DAYS, value=7)

def ensure_placeholders(machine_name, total):
    lst = st.session_state["personnel"].get(machine_name, [])
    while len(lst) < total:
        ph = f"{machine_name}-Personel{len(lst)+1}"
        lst.append(ph)
    st.session_state["personnel"][machine_name] = lst
    return lst

def df_to_bytes_csv(df):
    buf = BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()

# ---------- Plan oluştur butonu ----------
if st.button("▶️ Ayrıntılı Planı Oluştur"):
    try:
        if st.session_state["machines"].empty or st.session_state["plan"].empty:
            st.error("Lütfen önce Makine ve Üretim Planı verilerini girin.")
        else:
            machines_df = st.session_state["machines"].copy()
            plan_df = st.session_state["plan"].copy()
            # Ensure placeholders & init tracking
            person_assignments = {}   # person -> {date: shift_label}
            person_week_hours = {}    # person -> toplam haftalık saat ataması (hesaplanacak)
            overall_shortages = 0
            slot_rows = []

            for _, m in machines_df.iterrows():
                mn = m["Makine"]
                totalp = int(m["Toplam Personel"])
                ensure_placeholders(mn, totalp)
                st.session_state["rr_index"].setdefault(mn, 0)
                for p in st.session_state["personnel"].get(mn, []):
                    person_assignments.setdefault(p, {})
                    person_week_hours.setdefault(p, 0.0)

            # Generate slots per plan item
            for _, item in plan_df.iterrows():
                mn = item["Makine"]
                machine_row = machines_df[machines_df["Makine"]==mn].iloc[0]
                capacity = float(machine_row["Saatlik Kapasite (kg/saat)"])
                req_per_shift = int(machine_row["Vardiya Başına Kişi"])
                persons_pool = list(st.session_state["personnel"].get(mn, []))
                if capacity <= 0:
                    st.warning(f"{mn} kapasite hatası; atlandı.")
                    continue

                total_hours_needed = float(item["Miktar (kg)"]) / capacity
                remaining = total_hours_needed
                cur_date = start_date
                shift_idx = 0

                while remaining > 0:
                    slot_len = min(shift_hours, remaining)
                    date_str = cur_date.strftime("%Y-%m-%d")

                    assigned = []
                    shortage = 0
                    pool = persons_pool[:]
                    if pool:
                        rr_start = st.session_state["rr_index"].get(mn, 0) % max(1, len(pool))
                        idx = rr_start
                        tried = 0
                        # pick req_per_shift distinct persons respecting:
                        # - not assigned same date
                        # - weekly hours + slot_len <= weekly_fte_hours + overtime_per_person
                        while len(assigned) < req_per_shift and tried < len(pool)*2:
                            cand = pool[idx % len(pool)]
                            already = person_assignments.get(cand, {}).get(date_str)
                            cand_hours = person_week_hours.get(cand, 0.0)
                            if already is None and (cand_hours + slot_len) <= (weekly_fte_hours + overtime_per_person):
                                # assign
                                assigned.append(cand)
                                person_assignments.setdefault(cand, {})[date_str] = VARDIYA_ORDER[shift_idx]
                                person_week_hours[cand] = cand_hours + slot_len
                            idx += 1
                            tried += 1
                        st.session_state["rr_index"][mn] = idx % max(1, len(pool))
                        if len(assigned) < req_per_shift:
                            shortage = req_per_shift - len(assigned)
                    else:
                        shortage = req_per_shift

                    overall_shortages += shortage

                    slot_rows.append({
                        "Tarih": date_str,
                        "Vardiya": VARDIYA_ORDER[shift_idx],
                        "Makine": mn,
                        "Ürün": item["Ürün"],
                        "Planlanan Saat": round(slot_len,2),
                        "Gerekli Kişi": req_per_shift,
                        "Atanan Kişi Sayısı": len(assigned),
                        "Atanan İsimler": ", ".join(assigned) if assigned else ""
                    })

                    remaining -= slot_len
                    shift_idx = (shift_idx + 1) % 3
                    if shift_idx == 0:
                        cur_date = cur_date + timedelta(days=1)

            df_slots = pd.DataFrame(slot_rows)

            # ---------- Daily & Weekly summaries ----------
            if not df_slots.empty:
                min_date = pd.to_datetime(df_slots["Tarih"]).min()
                max_date = pd.to_datetime(df_slots["Tarih"]).max()
                date_range = pd.date_range(min_date, max_date)
            else:
                date_range = pd.date_range(start_date, start_date + timedelta(days=num_days-1))

            daily_rows = []
            weekly_rows = []
            for _, m in machines_df.iterrows():
                mn = m["Makine"]
                total_persons = len(st.session_state["personnel"].get(mn, []))
                # daily
                for d in date_range:
                    dstr = d.strftime("%Y-%m-%d")
                    day_slots = df_slots[(df_slots["Makine"]==mn) & (df_slots["Tarih"]==dstr)]
                    scheduled_hours = float(day_slots["Planlanan Saat"].sum()) if not day_slots.empty else 0.0
                    available_hours_day = total_persons * daily_fte_hours
                    overtime_capacity_day = total_persons * (overtime_per_person / 5.0)  # approx günlük overtime pay (haftalık böl)
                    # we will compute mesai as needed: prefer weekly overtime but give daily hint
                    mesai_needed_day = max(0.0, scheduled_hours - available_hours_day)
                    # see how much of mesai can be covered by overtime capacity (daily approx)
                    mesai_covered_by_overtime = min(mesai_needed_day, overtime_capacity_day)
                    unassigned_hours_day = max(0.0, mesai_needed_day - overtime_capacity_day)
                    daily_fte = scheduled_hours / daily_fte_hours if daily_fte_hours>0 else 0.0
                    daily_rows.append({
                        "Makine": mn,
                        "Tarih": dstr,
                        "Planlanan Saat (saat)": round(scheduled_hours,2),
                        "Mevcut Personel (adet)": total_persons,
                        "Mevcut Personel Saat (günlük)": round(available_hours_day,2),
                        "Mesai İhtiyacı (saat, total)": round(mesai_needed_day,2),
                        "Mesai Kapasitesi (günlük, approx)": round(overtime_capacity_day,2),
                        "Mesai Karşılandı (günlük, approx)": round(mesai_covered_by_overtime,2),
                        "Unassigned Saat (günlük, approx)": round(unassigned_hours_day,2),
                        "Günlük FTE": round(daily_fte,2)
                    })
                # weekly
                machine_slots = df_slots[df_slots["Makine"]==mn]
                weekly_scheduled = float(machine_slots["Planlanan Saat"].sum()) if not machine_slots.empty else 0.0
                weekly_available = total_persons * weekly_fte_hours
                weekly_overtime_capacity = total_persons * overtime_per_person
                weekly_mesai_needed = max(0.0, weekly_scheduled - weekly_available)
                weekly_overtime_used = min(weekly_mesai_needed, weekly_overtime_capacity)
                weekly_unassigned = max(0.0, weekly_mesai_needed - weekly_overtime_capacity)
                weekly_fte = weekly_scheduled / weekly_fte_hours if weekly_fte_hours>0 else 0.0
                weekly_rows.append({
                    "Makine": mn,
                    "Haftalık Planlanan Saat": round(weekly_scheduled,2),
                    "Haftalık Mevcut Personel Saat": round(weekly_available,2),
                    "Haftalık Mesai (saat)": round(weekly_mesai_needed,2),
                    "Haftalık Mesai Kapasitesi (saat)": round(weekly_overtime_capacity,2),
                    "Haftalık Mesai Kullanıldı (saat, approx)": round(weekly_overtime_used,2),
                    "Haftalık Unassigned Saat (approx)": round(weekly_unassigned,2),
                    "Haftalık FTE": round(weekly_fte,2)
                })

            df_daily = pd.DataFrame(daily_rows)
            df_weekly = pd.DataFrame(weekly_rows)

            # ---------- person x date matrix ----------
            all_dates = sorted({d for d in (df_slots["Tarih"].unique() if not df_slots.empty else [])} | { (start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(num_days) })
            st.subheader("📅 Vardiya Slotları (detay)")
            st.dataframe(df_slots, use_container_width=True)

            st.subheader("🔎 Makine Günlük Özeti")
            st.dataframe(df_daily, use_container_width=True)

            st.subheader("📈 Makine Haftalık Özeti")
            st.dataframe(df_weekly, use_container_width=True)

            st.subheader("🧾 Personel × Tarih Matrisi (Makine Bazlı)")
            for _, m in machines_df.iterrows():
                mac = m["Makine"]
                st.markdown(f"### {mac}")
                persons = st.session_state["personnel"].get(mac, [])
                if not persons:
                    persons = ensure_placeholders(mac, int(m["Toplam Personel"]))
                mat = pd.DataFrame(index=persons, columns=all_dates).fillna("")
                # fill mat from person_assignments
                for p in persons:
                    assigns = person_assignments.get(p, {})
                    for d in all_dates:
                        val = assigns.get(d)
                        mat.at[p, d] = val if val else ""
                st.dataframe(mat, use_container_width=True)

            # ---------- downloads & summary ----------
            st.subheader("💾 İndir")
            if not df_slots.empty:
                st.download_button("Vardiya slotlarını CSV indir", data=df_to_bytes_csv(df_slots), file_name="vardiya_slotlari.csv", mime="text/csv")
            if not df_daily.empty:
                st.download_button("Günlük özet CSV indir", data=df_to_bytes_csv(df_daily), file_name="gunluk_ozet.csv", mime="text/csv")
            if not df_weekly.empty:
                st.download_button("Haftalık özet CSV indir", data=df_to_bytes_csv(df_weekly), file_name="haftalik_ozet.csv", mime="text/csv")

            # overall
            st.markdown("### Özet")
            st.write({
                "Toplam Atanmayan Pozisyon (adet)": int(overall_shortages),
                "Toplam Haftalık Mesai (approx, saat)": round(sum([r["Haftalık Mesai (saat)"] for r in weekly_rows]) if weekly_rows else 0.0,2)
            })

    except Exception as exc:
        st.exception(exc)
        st.error("Plan oluşturma sırasında hata oluştu. Hatasız bir örnek ver ve tekrar dene.")
