import streamlit as st
import pandas as pd

st.set_page_config(page_title="Üretim Personel Planlayıcı", page_icon="🧮", layout="wide")

st.title("🧮 Üretim Personel Planlayıcı v3")
st.caption("Haftalık üretim planına göre FTE ve personel açığı analizi")

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
        haftalik_plan = st.number_input("Haftalık Üretim Planı (ton)", min_value=0.0)
        saatlik_kapasite = st.number_input("Saatlik Kapasite (ton/saat)", min_value=0.0)
        vardiya_personel = st.number_input("Vardiya Başı Gerekli Personel", min_value=0)
        mevcut_personel = st.number_input("Bölümde Mevcut Personel (adet)", min_value=0)
        saniyede_uretim = st.number_input("Saniyede Üretilen Ürün (kg/sn)", min_value=0.0)
        ekle = st.form_submit_button("Makineyi Ekle")

        if ekle and makine_adi:
            st.session_state.makineler.append({
                "Makine": makine_adi,
                "Haftalık Üretim Planı (ton)": haftalik_plan,
                "Saatlik Kapasite (ton/saat)": saatlik_kapasite,
                "Vardiya Personel": vardiya_personel,
                "Mevcut Personel": mevcut_personel,
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

        # İhtiyaç duyulan vardiya sayısı
        df_m["Toplam Gerekli Üretim Saati"] = df_m["Haftalık Üretim Planı (ton)"] / df_m["Saatlik Kapasite (ton/saat)"]
        df_m["Günlük Üretim Saati"] = df_m["Toplam Gerekli Üretim Saati"] / 5
        df_m["Toplam Üretim Personeli (3 Vardiya)"] = df_m["Vardiya Personel"] * 3

        # FTE hesapları
        df_m["Günlük FTE"] = (df_m["Vardiya Personel"] * 3 * 8) / 42.5
        df_m["Haftalık FTE"] = df_m["Günlük FTE"] * 5

        # Açık / fazla personel
        df_m["Personel Açığı (Kişi)"] = df_m["Toplam Üretim Personeli (3 Vardiya)"] - df_m["Mevcut Personel"]

        # Mesai ihtiyacı
        def mesai_durumu(row):
            if row["Personel Açığı (Kişi)"] > 0:
                return "⚠️ Mesai Gerekebilir"
            else:
                return "✅ Yeterli Personel"
        df_m["Mesai Durumu"] = df_m.apply(mesai_durumu, axis=1)

        st.markdown("### 🏭 Makine Bazlı Üretim & FTE Analizi")
        st.dataframe(df_m, use_container_width=True)

        toplam_fte = df_m["Haftalık FTE"].sum()
        toplam_acik = df_m["Personel Açığı (Kişi)"].sum()

        st.metric("Toplam Haftalık FTE", f"{toplam_fte:.2f}")
        st.metric("Toplam Personel Açığı", f"{toplam_acik}")
    else:
        st.warning("Makine bilgisi olmadan hesaplama yapılamaz.")

    # Manuel işler
    if st.session_state.manuel_isler:
        df_is = pd.DataFrame(st.session_state.manuel_isler)
        df_is["Haftalık Süre (saat)"] = df_is["Günlük Süre (saat)"] * 5
        df_is["Haftalık FTE"] = (df_is["Haftalık Süre (saat)"] * df_is["Kişi Sayısı"]) / 42.5

        st.markdown("### 🔧 Manuel İşlerin FTE Katkısı")
        st.dataframe(df_is, use_container_width=True)
