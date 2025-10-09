import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# SAYFA AYARLARI
# -----------------------------
st.set_page_config(page_title="Akıllı Üretim & Vardiya Planlayıcı", layout="wide")
st.title("🏭 Akıllı Üretim & Vardiya Planlayıcı")

st.markdown("""
Bu araç, bölüm bazlı üretim planı, vardiya dağılımı, FTE (Full Time Equivalent) hesaplaması ve mesai ihtiyacını 
otomatik olarak hesaplar.  
Vardiyalar:
- **12 vardiyası:** 08:00 - 16:00  
- **35 vardiyası:** 16:00 - 24:00  
- **51 vardiyası:** 24:00 - 08:00
""")

# -----------------------------
# PARAMETRELER
# -----------------------------
vardiyalar = {
    "12 vardiyası": {"saat_aralığı": "08:00-16:00", "süre": 7.5},
    "35 vardiyası": {"saat_aralığı": "16:00-24:00", "süre": 7.5},
    "51 vardiyası": {"saat_aralığı": "24:00-08:00", "süre": 7.5},
}

gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

st.sidebar.header("⚙️ Planlama Parametreleri")

# Bölüm bilgileri (kullanıcı girebilir)
st.sidebar.markdown("### Bölümler ve kişi sayıları")
bolumler_input = st.sidebar.text_area(
    "Bölüm adlarını ve kişi sayılarını gir (örnek format: Kaymaklı:9, Yoğurt:8, Ayran:7)",
    value="Kaymaklı:9, Yoğurt:8, Ayran:7, Süt Dolum:6, Bakım:5"
)

# Girdi parse et
try:
    bolumler = {b.strip().split(":")[0]: int(b.strip().split(":")[1]) for b in bolumler_input.split(",")}
except:
    st.error("❌ Bölüm bilgisini doğru formatta gir: Örn. Kaymaklı:9, Yoğurt:8")
    st.stop()

# -----------------------------
# PLAN OLUŞTURMA FONKSİYONU
# -----------------------------
def plan_olustur():
    plan = []
    np.random.seed(42)

    for bolum, kisi_sayisi in bolumler.items():
        for gun in gunler:
            vardiya_basina = kisi_sayisi // 3
            kalan = kisi_sayisi % 3
            dagilim = [vardiya_basina] * 3
            for i in range(kalan):
                dagilim[i] += 1

            for i, (vardiya_adi, v_detay) in enumerate(vardiyalar.items()):
                calisma_saat = dagilim[i] * v_detay["süre"]
                fte = round(calisma_saat / 7.5, 2)
                mesai = 0 if dagilim[i] >= 2 else (2 - dagilim[i]) * 1.5  # eksik kişi başına 1.5 saat mesai varsayımı
                plan.append({
                    "Bölüm": bolum,
                    "Gün": gun,
                    "Vardiya": vardiya_adi,
                    "Kişi Sayısı": dagilim[i],
                    "Toplam Çalışma Saati": calisma_saat,
                    "FTE": fte,
                    "Mesai (saat)": mesai
                })
    return pd.DataFrame(plan)

# -----------------------------
# PLAN OLUŞTUR BUTONU
# -----------------------------
if st.button("📅 Planı Oluştur"):
    df = plan_olustur()

    # -----------------------------
    # GÜNLÜK TABLO GÖRÜNÜMÜ
    # -----------------------------
    st.subheader("🔹 Günlük Vardiya Planı")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # -----------------------------
    # HAFTALIK ÖZETLER
    # -----------------------------
    haftalik_ozet = (
        df.groupby("Bölüm")
        .agg({
            "Toplam Çalışma Saati": "sum",
            "Mesai (saat)": "sum",
            "FTE": "sum"
        })
        .reset_index()
    )

    toplam_satir = pd.DataFrame({
        "Bölüm": ["TOPLAM"],
        "Toplam Çalışma Saati": [haftalik_ozet["Toplam Çalışma Saati"].sum()],
        "Mesai (saat)": [haftalik_ozet["Mesai (saat)"].sum()],
        "FTE": [haftalik_ozet["FTE"].sum()]
    })

    haftalik_ozet = pd.concat([haftalik_ozet, toplam_satir], ignore_index=True)

    st.subheader("📊 Haftalık FTE ve Çalışma Saati Özeti")
    st.dataframe(haftalik_ozet, use_container_width=True, hide_index=True)

    # -----------------------------
    # GRAFİK GÖSTERİMİ
    # -----------------------------
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(haftalik_ozet["Bölüm"], haftalik_ozet["FTE"])
    ax.set_ylabel("Toplam FTE")
    ax.set_title("Haftalık FTE Dağılımı (Bölüm Bazlı)")
    st.pyplot(fig)

    # -----------------------------
    # MATRİKS TABLO (Bölüm & Gün Bazlı)
    # -----------------------------
    st.subheader("🧩 Bölüm Bazlı Günlük FTE Matrisi")
    matris = df.pivot_table(
        index="Bölüm",
        columns="Gün",
        values="FTE",
        aggfunc="sum",
        fill_value=0
    )
    st.dataframe(matris, use_container_width=True)

    st.success("✅ Vardiya planı başarıyla oluşturuldu!")

else:
    st.info("👆 Soldan parametreleri belirleyip 'Planı Oluştur' butonuna tıklayarak başlayabilirsin.")
