import streamlit as st
import pandas as pd
import plotly.express as px
import math

st.set_page_config(page_title="Üretim Verimlilik Dashboard v5", page_icon="⚙️", layout="wide")

st.title("⚙️ Üretim Verimlilik Dashboard v5")
st.caption("AI hazır formatlı, çalışır sürüm")

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

        # Grafikler
        fig1 = px.bar(df, x="Makine", y=["Haftalık Üretim Planı (ton)", "Toplam Üretim Saati"],
                      barmode="group", title="Plan vs Toplam Üretim", color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.bar(df, x="Makine", y="Mesai Saat", color="Durum",
                      title="Mesai İhtiyacı", color_discrete_map={"⚠️ Mesai Gerekebilir": "red", "✅ Yeterli": "green"})
        st.plotly_chart(fig2, use_container_width=True)

# ------------------------------
# AI TAVSİYE (dummy)
# ------------------------------
def ai_tavsiyeler(df):
    """
    AI entegrasyonu için hazır format.
    Şimdilik dummy metin döndürüyor.
    """
    tavsiyeler = []
    for _, row in df.iterrows():
        if row["Mesai Saat"] > 0:
            tavsiyeler.append(f"{row['Makine']}: Mesai gerekebilir ({row['Mesai Saat']:.1f} saat)")
        else:
            tavsiyeler.append(f"{row['Makine']}: Yeterli personel mevcut.")
    return "\n".join(tavsiyeler)

with tab4:
    st.subheader("🤖 AI Tavsiyeleri (Dummy)")
    if not st.session_state.makineler:
        st.info("Makine verisi olmadan tavsiye oluşturulamaz.")
    else:
        df_ai = pd.DataFrame(st.session_state.makineler)
        st.text(ai_tavsiyeler(df_ai))
