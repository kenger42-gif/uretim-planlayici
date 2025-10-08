import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Üretim Verimlilik Dashboard", page_icon="⚙️", layout="wide")

st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    .stDataFrame {
        background-color: white;
        border-radius: 10px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚙️ Üretim Verimlilik Dashboard")
st.caption("Haftalık plan, kapasite, FTE ve personel açığı analizi")

# ------------------------------
# Başlangıç state
# ------------------------------
if "makineler" not in st.session_state:
    st.session_state.makineler = []
if "manuel_isler" not in st.session_state:
    st.session_state.manuel_isler = []

tab1, tab2, tab3 = st.tabs(["🧮 Makine Girişleri", "🔧 Manuel İşler", "📊 Analiz ve Grafikler"])

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
        df = pd.DataFrame(st.session_state.makineler)
        st.dataframe(df, use_container_width=True)
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
# GRAFİKSEL ANALİZ
# ------------------------------
with tab3:
    if not st.session_state.makineler:
        st.warning("Makine verisi olmadan analiz yapılamaz.")
    else:
        df = pd.DataFrame(st.session_state.makineler)
        df["Gerekli Üretim Saati"] = df["Haftalık Üretim Planı (ton)"] / df["Saatlik Kapasite (ton/saat)"]
        df["Personel Açığı"] = (df["Vardiya Personel"] * 3) - df["Mevcut Personel"]
        df["Durum"] = df["Personel Açığı"].apply(lambda x: "⚠️ Açık Var" if x > 0 else "✅ Yeterli")

        toplam_fte = ((df["Vardiya Personel"] * 3 * 8) / 42.5).sum()
        toplam_acik = df["Personel Açığı"].sum()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Toplam Haftalık FTE", f"{toplam_fte:.1f}")
        with col2:
            st.metric("Toplam Personel Açığı", f"{toplam_acik}")

        st.divider()
        st.markdown("### 📊 Makine Bazlı Görselleştirme")

        fig1 = px.bar(df, x="Makine", y=["Haftalık Üretim Planı (ton)", "Saatlik Kapasite (ton/saat)"],
                      barmode="group", title="Üretim Planı vs Kapasite", color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.pie(df, values="Mevcut Personel", names="Makine", title="Personel Dağılımı")
        st.plotly_chart(fig2, use_container_width=True)

        fig3 = px.bar(df, x="Makine", y="Personel Açığı", color="Durum",
                      title="Personel Açığı Durumu", color_discrete_map={"⚠️ Açık Var": "red", "✅ Yeterli": "green"})
        st.plotly_chart(fig3, use_container_width=True)
