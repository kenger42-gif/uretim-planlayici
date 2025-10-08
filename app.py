import streamlit as st
import pandas as pd

st.set_page_config(page_title="Üretim Personel Planlayıcı", page_icon="🧮", layout="wide")

st.title("🧮 Üretim Personel Planlayıcı v2")
st.caption("Otomatik vardiya, FTE ve mesai hesaplama sistemi")

# ------------------------------
# Başlangıç state
# ------------------------------
if "makineler" not in st.session_state:
    st.session_state.makineler = []
if "manuel_isler" not in st.session_state:
    st.session_state.manuel_isler = []

# ------------------------------
# Sekmeler
# ------------------------------
tab1, tab2, tab3 = st.tabs(["⚙️ Makine Bilgileri", "🧰 Manuel İşler", "📊 Sonuçlar"])

# ------------------------------
# 1️⃣ MAKİNE BİLGİLERİ
# ------------------------------
with tab1:
    st.subheader("Makine Bilgisi Ekle")
    with st.form("makine_formu"):
        makine_adi = st.text_input("Makine Adı")
        vardiya_personel = st.number_input("Vardiya Başı Gerekli Personel", min_value=0)
        saniyede_uretim = st.number_input("Saniyede Üretilen Ürün (kg/sn)", min_value=0.0)
        ekle = st.form_submit_button("Makineyi Ekle")

        if ekle and makine_adi:
            st.session_state.makineler.append({
                "Makine": makine_adi,
                "Vardiya Personel": vardiya_personel,
                "Saniyede Üretim (kg/sn)": saniyede_uretim
            })
            st.success(f"{makine_adi} başarıyla eklendi!")

    if st.session_state.makineler:
        df_makine = pd.DataFrame(st.session_state.makineler)
        st.dataframe(df_makine, use_container_width=True)
    else:
        st.info("Henüz makine bilgisi girilmedi.")

# ------------------------------
# 2️⃣ MANUEL İŞLER
# ------------------------------
with tab2:
    st.subheader("Manuel İş Bilgisi Ekle")
    with st.form("manuel_formu"):
        is_adi = st.text_input("Manuel İş Adı")
        gunluk_sure = st.number_input("Günlük Toplam Süre (saat)", min_value=0.0)
        kisi_sayisi = st.number_input("Bu iş için gerekli kişi sayısı", min_value=0)
        ekle_is = st.form_submit_button("İşi Ekle")

        if ekle_is and is_adi:
            st.session_state.manuel_isler.append({
                "Manuel İş": is_adi,
                "Günlük Süre (saat)": gunluk_sure,
                "Kişi Sayısı": kisi_sayisi
            })
            st.success(f"{is_adi} başarıyla eklendi!")

    if st.session_state.manuel_isler:
        df_is = pd.DataFrame(st.session_state.manuel_isler)
        st.dataframe(df_is, use_container_width=True)
    else:
        st.info("Henüz manuel iş girilmedi.")

# ------------------------------
# 3️⃣ SONUÇLAR
# ------------------------------
with tab3:
    st.subheader("📈 Hesaplama Sonuçları")

    if st.session_state.makineler:
        df_m = pd.DataFrame(st.session_state.makineler)

        # 3 vardiya toplamı
        df_m["Toplam Üretim Personeli (3 Vardiya)"] = df_m["Vardiya Personel"] * 3

        # Günlük / haftalık FTE hesaplama
        # 1 FTE = 42.5 saat/hafta, 8 saat/vardiya, 5 gün/hafta
        df_m["Günlük FTE"] = (df_m["Vardiya Personel"] * 3 * 8) / 42.5
        df_m["Haftalık FTE"] = df_m["Günlük FTE"] * 5

        st.markdown("### 🏭 Makine Bazlı FTE Hesapları")
        st.dataframe(df_m, use_container_width=True)

        toplam_personel = df_m["Toplam Üretim Personeli (3 Vardiya)"].sum()
        toplam_fte = df_m["Haftalık FTE"].sum()

        st.metric("Toplam Üretim Personeli", f"{toplam_personel}")
        st.metric("Toplam Haftalık FTE", f"{toplam_fte:.2f}")
    else:
        st.warning("Makine bilgisi olmadan hesaplama yapılamaz.")

    if st.session_state.manuel_isler:
        df_is = pd.DataFrame(st.session_state.manuel_isler)
        df_is["Haftalık Süre (saat)"] = df_is["Günlük Süre (saat)"] * 5
        df_is["Haftalık FTE"] = (df_is["Haftalık Süre (saat)"] * df_is["Kişi Sayısı"]) / 42.5

        st.markdown("### 🔧 Manuel İşlerin FTE Katkısı")
        st.dataframe(df_is, use_container_width=True)

        toplam_m_is = df_is["Kişi Sayısı"].sum()
        toplam_m_fte = df_is["Haftalık FTE"].sum()

        st.metric("Manuel İş Personeli", f"{toplam_m_is}")
        st.metric("Manuel İş FTE", f"{toplam_m_fte:.2f}")
    else:
        st.info("Henüz manuel iş girilmedi.")

    # ------------------------------
    # MESAI KONTROLÜ
    # ------------------------------
    st.divider()
    st.markdown("### ⏱️ Mesai Gereksinimi Kontrolü")

    if st.session_state.makineler:
        ortalama_vardiya_personel = df_m["Vardiya Personel"].mean()
        if ortalama_vardiya_personel > 10:
            st.warning("⚠️ Ortalama vardiya personeli 10’un üzerinde. Muhtemelen mesaiye ihtiyaç var (3.5 saat).")
        else:
            st.success("✅ Mevcut personel yeterli, mesaiye gerek yok.")
    else:
        st.info("Makine bilgisi girmeden mesai kontrolü yapılamaz.")
