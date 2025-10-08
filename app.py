import streamlit as st
import pandas as pd

st.title("🧮 Üretim Personel Planlayıcı")

# Session state başlat
if "data" not in st.session_state:
    st.session_state.data = []

# Veri girişi formu
st.subheader("Veri Girişi")
with st.form("veri_formu"):
    urun = st.text_input("Ürün Adı")
    haftalik_tonaj = st.number_input("Haftalık Üretim (ton)", min_value=0.0)
    gunluk_tonaj = st.number_input("Günlük Üretim (ton)", min_value=0.0)
    saatlik_kapasite = st.number_input("Saatlik Kapasite (ton/saat)", min_value=0.0)
    personel_ihtiyaci = st.number_input("Makinede Gerekli Personel", min_value=0)
    submit = st.form_submit_button("Ekle")

    if submit and urun:
        yeni_veri = {
            "Ürün": urun,
            "Haftalık Üretim (ton)": haftalik_tonaj,
            "Günlük Üretim (ton)": gunluk_tonaj,
            "Saatlik Kapasite (ton/saat)": saatlik_kapasite,
            "Makinede Gerekli Personel": personel_ihtiyaci
        }
        st.session_state.data.append(yeni_veri)
        st.success(f"{urun} başarıyla eklendi!")

# Girilen veriler varsa tabloyu göster
if st.session_state.data:
    df = pd.DataFrame(st.session_state.data)
    st.subheader("Girilmiş Veriler")
    st.dataframe(df)

    # Haftalık personel ihtiyacı hesaplama
    df["Tahmini Haftalık Personel (adet)"] = (
        df["Haftalık Üretim (ton)"] / (df["Saatlik Kapasite (ton/saat)"] * 8 * 5)
    ) * df["Makinede Gerekli Personel"]

    st.subheader("🔍 Hesaplanan Personel İhtiyacı")
    st.dataframe(df[["Ürün", "Tahmini Haftalık Personel (adet)"]])
else:
    st.info("Henüz veri girilmedi.")
