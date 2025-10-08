import streamlit as st
import pandas as pd
import plotly.express as px
import math
import openai

# OpenAI API Key
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(page_title="Üretim Verimlilik Dashboard v5", page_icon="⚙️", layout="wide")

st.title("⚙️ Üretim Verimlilik Dashboard v5")
st.caption("AI Tavsiyeleri entegre edildi")

# ------------------------------
# Başlangıç state
# ------------------------------
if "makineler" not in st.session_state:
    st.session_state.makineler = []
if "manuel_isler" not in st.session_state:
    st.session_state.manuel_isler = []

tab1, tab2, tab3, tab4 = st.tabs([
    "🧮 Makine Girişleri",
    "🔧 Manuel İşler",
    "📊 Analiz ve Grafikler",
    "🤖 AI Tavsiyeleri"
])

vardiya_saat = 8
gun_sayisi = 5
fte_hs = 42.5

# ------------------------------
# MAKİNE GİRİŞLERİ
# ------------------------------
with tab1:
    st.subheader("Makine Bilgisi Ekle")
    with st.form("makine_formu"):
        makine_adi = st.text_input("Makine Adı")
        haftalik_plan = st.number_input("Haftalık Üretim Planı (ton)", min_value=0.0)
        saatlik_kapasite = st.number_input("Saatlik Kapasite (ton/saat)", min_value=0.0)
        vardiya_personel = st.number_input("Vardiya Başı Gerekli Personel", min_value=0)
        mevcut_personel = st.number_input("Bölümde Mevcut Personel (adet)", min_value=0)
        ekle = st.form_submit_button("Makineyi Ekle")

        if ekle and makine_adi:
            st.session_state.makineler.append({
                "Makine": makine_adi,
                "Haftalık Üretim Planı (ton)": haftalik_plan,
                "Saatlik Kapasite (ton/saat)": saatlik_kapasite,
                "Vardiya Personel": vardiya_personel,
                "Mevcut Personel": mevcut_personel
            })
            st.success(f"{makine_adi} başarıyla eklendi ✅")

    if st.session_state.makineler:
        st.dataframe(pd.DataFrame(st.session_state.makineler), use_container_width=True)
    else:
        st.info("Henüz makine bilgisi girilmedi.")

# ------------------------------
# MANUEL İŞLER
# ------------------------------
with tab2:
    st.subheader("Manuel İş Bilgisi Ekle")
    with st.form("manuel_formu"):
        is_adi = st.text_input("Manuel İş Adı")
        gunluk_sure = st.number_input("Günlük Süre (saat)", min_value=0.0)
        kisi_sayisi = st.number_input("Kişi Sayısı", min_value=0)
        ekle_is = st.form_submit_button("İşi Ekle")

        if ekle_is and is_adi:
            st.session_state.manuel_isler.append({
                "Manuel İş": is_adi,
                "Günlük Süre (saat)": gunluk_sure,
                "Kişi Sayısı": kisi_sayisi
            })
            st.success(f"{is_adi} eklendi ✅")

    if st.session_state.manuel_isler:
        st.dataframe(pd.DataFrame(st.session_state.manuel_isler), use_container_width=True)
    else:
        st.info("Henüz manuel iş eklenmedi.")

# ------------------------------
# ANALİZ VE GRAFİKLER
# ------------------------------
with tab3:
    if not st.session_state.makineler:
        st.warning("Makine verisi olmadan analiz yapılamaz.")
    else:
        df = pd.DataFrame(st.session_state.makineler)

        # Hesaplamalar
        df["Toplam Üretim Saati"] = df["Haftalık Üretim Planı (ton)"] / df["Saatlik Kapasite (ton/saat)"]
        df["Mevcut Kapasite Saati"] = df["Mevcut Personel"] * vardiya_saat * 3 * gun_sayisi
        df["Mesai Saat"] = df["Toplam Üretim Saati"] - df["Mevcut Kapasite Saati"]
        df["Mesai Saat"] = df["Mesai Saat"].apply(lambda x: x if x>0 else 0)
        df["Tahmini Gün"] = df["Toplam Üretim Saati"] / (df["Mevcut Personel"] * vardiya_saat * 3)
        df["Tahmini Gün"] = df["Tahmini Gün"].apply(lambda x: math.ceil(x*10)/10)
        df["Kötü Senaryo Gün"] = df["Toplam Üretim Saati"] / (df["Mevcut Personel"]*0.5 * vardiya_saat * 3)
        df["Kötü Senaryo Gün"] = df["Kötü Senaryo Gün"].apply(lambda x: math.ceil(x*10)/10)
        df["Personel Açığı"] = (df["Vardiya Personel"]*3) - df["Mevcut Personel"]
        df["Durum"] = df["Mesai Saat"].apply(lambda x: "⚠️ Mesai Gerekebilir" if x>0 else "✅ Yeterli")
        df["Haftalık FTE"] = ((df["Vardiya Personel"] * 3 * vardiya_saat * gun_sayisi)/fte_hs)

        # Metrikler
        toplam_fte = df["Haftalık FTE"].sum()
        toplam_mesai = df["Mesai Saat"].sum()
        toplam_acik = df["Personel Açığı"].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("Toplam Haftalık FTE", f"{toplam_fte:.1f}")
        col2.metric("Toplam Mesai Saati", f"{toplam_mesai:.1f}")
        col3.metric("Toplam Personel Açığı", f"{toplam_acik}")

        st.divider()
        st.markdown("### 📊 Makine Bazlı Analiz")
        st.dataframe(df[["Makine","Personel Açığı","Mesai Saat","Tahmini Gün","Kötü Senaryo Gün","Durum","Haftalık FTE"]], use_container_width=True)

# ------------------------------
# AI TAVSİYELERİ
# ------------------------------
with tab4:
    st.subheader("🤖 Yapay Zeka Tavsiyeleri")
    if not st.session_state.makineler:
        st.info("Makine verisi olmadan tavsiye oluşturulamaz.")
    else:
        df = pd.DataFrame(st.session_state.makineler)
        # Basit metin oluşturma
        makine_ozet = df.to_dict(orient="records")
        prompt = f"""
        Bu veriye göre üretim planını analiz et ve bana tavsiyeler sun:
        {makine_ozet}
        - Mesai gereken makineleri belirt
        - Personel eksikliği var mı?
        - Tahmini üretim süresi ve kötü senaryolar
        - Yöneticiye öneri şeklinde kısa cümleler
        """

        # GPT çağrısı
        try:
            response = openai.ChatCompletion.create(
                model="gpt-5-mini",
                messages=[{"role":"user","content":prompt}],
                temperature=0.7
            )
            ai_tavsiyeler = response['choices'][0]['message']['content']
            st.markdown(ai_tavsiyeler)
        except Exception as e:
            st.error(f"AI tavsiyeleri alınamadı: {e}")
