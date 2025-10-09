import streamlit as st
import pandas as pd
import math
from datetime import datetime, timedelta

st.set_page_config(page_title="Vardiya Planlayıcı", layout="wide")
st.title("🏭 Üretim ve Vardiya Planlama Sistemi")

# --- Session State tanımları ---
if "machines" not in st.session_state:
    st.session_state["machines"] = pd.DataFrame(columns=["Makine", "Kapasite (kg/saat)", "Vardiya Başına Kişi", "Toplam Personel"])

if "plan" not in st.session_state:
    st.session_state["plan"] = pd.DataFrame(columns=["Ürün", "Miktar (kg)", "Makine"])

# --- 1. MAKİNE BİLGİLERİ ---
st.header("1️⃣ Makine Bilgileri Girişi")

uploaded_machines = st.file_uploader("Makine bilgilerini içeren Excel dosyasını yükleyin (isteğe bağlı)", type=["xlsx"])
if uploaded_machines:
    st.session_state["machines"] = pd.read_excel(uploaded_machines)
else:
    with st.form("makine_form"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            makine_adi = st.text_input("Makine Adı")
        with col2:
            kapasite = st.number_input("Kapasite (kg/saat)", min_value=50, max_value=5000, step=50)
        with col3:
            kisi_vardiya = st.number_input("Vardiya Başına Gerekli Kişi", min_value=1, max_value=10)
        with col4:
            toplam_personel = st.number_input("Toplam Personel", min_value=1, max_value=50)
        ekle = st.form_submit_button("Makineyi Ekle")

        if ekle and makine_adi:
            yeni = pd.DataFrame([[makine_adi, kapasite, kisi_vardiya, toplam_personel]],
                                 columns=["Makine", "Kapasite (kg/saat)", "Vardiya Başına Kişi", "Toplam Personel"])
            st.session_state["machines"] = pd.concat([st.session_state["machines"], yeni], ignore_index=True)

st.dataframe(st.session_state["machines"])

# --- 2. ÜRETİM PLANI ---
st.header("2️⃣ Üretim Planı Girişi")

uploaded_plan = st.file_uploader("Üretim planı Excel yükle (isteğe bağlı)", type=["xlsx"])
if uploaded_plan:
    st.session_state["plan"] = pd.read_excel(uploaded_plan)
else:
    with st.form("uretim_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            urun = st.text_input("Ürün Adı")
        with col2:
            miktar = st.number_input("Miktar (kg)", min_value=100, max_value=100000, step=100)
        with col3:
            makine_sec = st.selectbox("Makine Seç", st.session_state["machines"]["Makine"] if not st.session_state["machines"].empty else [])
        ekle_plan = st.form_submit_button("Üretim Planına Ekle")

        if ekle_plan and urun and makine_sec:
            yeni = pd.DataFrame([[urun, miktar, makine_sec]], columns=["Ürün", "Miktar (kg)", "Makine"])
            st.session_state["plan"] = pd.concat([st.session_state["plan"], yeni], ignore_index=True)

st.dataframe(st.session_state["plan"])

# --- 3. PLAN HESAPLAMA ---
st.header("3️⃣ Plan Hesaplama")

if st.button("Planı Oluştur"):
    df_machines = st.session_state["machines"]
    df_plan = st.session_state["plan"]

    if df_machines.empty or df_plan.empty:
        st.error("⚠️ Lütfen hem makine hem üretim planı verilerini giriniz.")
    else:
        results = []
        vardiya_takvimi = []
        start_date = datetime.today()

        for _, row in df_plan.iterrows():
            makine = df_machines[df_machines["Makine"] == row["Makine"]].iloc[0]
            kapasite = makine["Kapasite (kg/saat)"]
            kisi_ihtiyac = makine["Vardiya Başına Kişi"]
            toplam_personel = makine["Toplam Personel"]

            sure_saat = row["Miktar (kg)"] / kapasite
            vardiya_sayisi = math.ceil(sure_saat / 8)
            toplam_kisi_ihtiyaci = kisi_ihtiyac * 3  # 3 vardiya varsayımı

            eksik = "Yok" if toplam_personel >= toplam_kisi_ihtiyaci else f"{toplam_kisi_ihtiyaci - toplam_personel} kişi eksik"
            
            results.append({
                "Ürün": row["Ürün"],
                "Makine": row["Makine"],
                "Toplam Üretim Süresi (saat)": round(sure_saat, 2),
                "Gerekli Vardiya Sayısı": vardiya_sayisi,
                "Personel Durumu": eksik
            })

            # --- VARDİYA TAKVİMİ ---
            kalan_sure = sure_saat
            tarih = start_date
            vardiya_num = 1
            while kalan_sure > 0:
                calisma_saat = min(8, kalan_sure)
                vardiya_takvimi.append({
                    "Tarih": tarih.strftime("%d.%m.%Y"),
                    "Vardiya": vardiya_num,
                    "Makine": row["Makine"],
                    "Ürün": row["Ürün"],
                    "Personel": kisi_ihtiyac,
                    "Planlanan Süre (saat)": round(calisma_saat, 2)
                })
                kalan_sure -= calisma_saat
                vardiya_num = 1 if vardiya_num == 3 else vardiya_num + 1
                if vardiya_num == 1:
                    tarih += timedelta(days=1)

        df_sonuc = pd.DataFrame(results)
        df_vardiya = pd.DataFrame(vardiya_takvimi)

        st.success("📊 Plan oluşturuldu!")
        st.subheader("🔹 Üretim Özeti")
        st.dataframe(df_sonuc)

        st.subheader("📅 Vardiya Takvimi")
        st.dataframe(df_vardiya)

        toplam_mesai = df_sonuc["Toplam Üretim Süresi (saat)"].sum() - (len(df_sonuc) * 24)
        if toplam_mesai > 0:
            st.warning(f"Toplam mesai ihtiyacı yaklaşık {round(toplam_mesai, 1)} saat.")
        else:
            st.info("Mevcut vardiyalar üretim için yeterli görünüyor.")

st.markdown("---")
st.caption("💡 Geliştirilebilir: makine yerleşim planı, vardiya takvimi görselleştirmesi, AI öneri sistemi")
