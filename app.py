import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Vardiya Planlayıcı", layout="wide")

st.title("🏭 Üretim ve Vardiya Planlama Sistemi")

st.write("""
Bu uygulama, haftalık üretim planını ve makine bazlı personel gereksinimlerini dikkate alarak
en uygun vardiya planını oluşturur.
""")

st.header("1️⃣ Makine Bilgileri Girişi")

uploaded_machines = st.file_uploader("Makine bilgilerini içeren Excel dosyasını yükleyin (isteğe bağlı)", type=["xlsx"])
if uploaded_machines:
    df_machines = pd.read_excel(uploaded_machines)
else:
    st.write("Elle giriş yapabilirsiniz:")
    df_machines = pd.DataFrame(columns=["Makine", "Kapasite (kg/saat)", "Vardiya Başına Kişi", "Toplam Personel"])
    with st.form("makine_form"):
        makine_adi = st.text_input("Makine Adı")
        kapasite = st.number_input("Kapasite (kg/saat)", min_value=50, max_value=5000, step=50)
        kisi_vardiya = st.number_input("Vardiya Başına Gerekli Kişi Sayısı", min_value=1, max_value=10)
        toplam_personel = st.number_input("Bölümde Toplam Personel", min_value=1, max_value=50)
        ekle = st.form_submit_button("Makineyi Ekle")
        if ekle and makine_adi:
            df_machines.loc[len(df_machines)] = [makine_adi, kapasite, kisi_vardiya, toplam_personel]

st.dataframe(df_machines)

st.header("2️⃣ Üretim Planı Girişi")

uploaded_plan = st.file_uploader("Üretim planı Excel yükle (isteğe bağlı)", type=["xlsx"])
if uploaded_plan:
    df_plan = pd.read_excel(uploaded_plan)
else:
    df_plan = pd.DataFrame(columns=["Ürün", "Miktar (kg)", "Makine"])
    with st.form("uretim_form"):
        urun = st.text_input("Ürün Adı")
        miktar = st.number_input("Miktar (kg)", min_value=100, max_value=100000, step=100)
        makine_sec = st.selectbox("Makine Seç", df_machines["Makine"] if not df_machines.empty else [])
        ekle_plan = st.form_submit_button("Üretim Planına Ekle")
        if ekle_plan and urun:
            df_plan.loc[len(df_plan)] = [urun, miktar, makine_sec]

st.dataframe(df_plan)

st.header("3️⃣ Plan Hesaplama")

if st.button("Planı Oluştur"):
    if df_machines.empty or df_plan.empty:
        st.error("Lütfen hem makine hem üretim planı verilerini giriniz.")
    else:
        results = []
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

        df_sonuc = pd.DataFrame(results)
        st.success("📊 Plan oluşturuldu!")
        st.dataframe(df_sonuc)

        toplam_mesai = df_sonuc["Toplam Üretim Süresi (saat)"].sum() - (len(df_sonuc) * 24)
        if toplam_mesai > 0:
            st.warning(f"Toplam mesai ihtiyacı yaklaşık {round(toplam_mesai, 1)} saat.")
        else:
            st.info("Mevcut vardiyalar üretim için yeterli görünüyor.")

st.markdown("---")
st.caption("💡 Geliştirilebilir: görsel makine yerleşim planı, vardiya bazlı takvim, otomatik AI öneri modülü")
