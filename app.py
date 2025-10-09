import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Akıllı Vardiya Planlayıcı", layout="wide")

st.title("🧭 Akıllı Vardiya Planlayıcı")

# -----------------------------
# PARAMETRELER
# -----------------------------
vardiyalar = {
    "12 vardiyası": {"saat_aralığı": "08:00-16:00", "süre": 7.5},
    "35 vardiyası": {"saat_aralığı": "16:00-24:00", "süre": 7.5},
    "51 vardiyası": {"saat_aralığı": "24:00-08:00", "süre": 7.5},
}

# Günler
gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

# Bölümler ve kişi sayıları
bolumler = {
    "Kaymaklı": 9,
    "Yoğurt": 8,
    "Ayran": 7,
    "Süt Dolum": 6,
    "Bakım": 5,
}

# -----------------------------
# AKILLI PLANLAMA
# -----------------------------
def plan_olustur():
    plan = []
    np.random.seed(42)  # sabit sonuçlar için

    for bolum, kisi_sayisi in bolumler.items():
        for gun in gunler:
            # 3 vardiyaya dengeli dağıtım
            vardiya_basina = kisi_sayisi // 3
            kalan = kisi_sayisi % 3
            dagilim = [vardiya_basina] * 3
            for i in range(kalan):
                dagilim[i] += 1

            # Her vardiyanın toplam çalışma saati
            for i, (vardiya_adi, v_detay) in enumerate(vardiyalar.items()):
                calisma_saat = dagilim[i] * v_detay["süre"]
                fte = calisma_saat / 7.5
                plan.append({
                    "Bölüm": bolum,
                    "Gün": gun,
                    "Vardiya": vardiya_adi,
                    "Kişi Sayısı": dagilim[i],
                    "Toplam Çalışma Saati": calisma_saat,
                    "FTE": round(fte, 2)
                })
    return pd.DataFrame(plan)

df = plan_olustur()

# -----------------------------
# MESAI İHTİYACI HESAPLAMA
# -----------------------------
# Burada mesai ihtiyacını örnek olarak rastgele belirliyoruz,
# istenirse üretim planına göre dinamik hale getirilebilir.
df["Mesai (saat)"] = np.where(df["Kişi Sayısı"] < 2, 1.5, 0)

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

# Kümülatif toplam
toplam_satir = pd.DataFrame({
    "Bölüm": ["TOPLAM"],
    "Toplam Çalışma Saati": [haftalik_ozet["Toplam Çalışma Saati"].sum()],
    "Mesai (saat)": [haftalik_ozet["Mesai (saat)"].sum()],
    "FTE": [haftalik_ozet["FTE"].sum()]
})

haftalik_ozet = pd.concat([haftalik_ozet, toplam_satir], ignore_index=True)

# -----------------------------
# GÖRSEL ARAYÜZ
# -----------------------------
st.subheader("📅 Günlük Vardiya Planı")
st.dataframe(df, use_container_width=True)

st.subheader("📊 Haftalık FTE ve Çalışma Saati Özeti")
st.dataframe(haftalik_ozet, use_container_width=True)

# Grafik
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.bar(haftalik_ozet["Bölüm"], haftalik_ozet["FTE"])
ax.set_ylabel("Toplam FTE")
ax.set_title("Haftalık FTE Dağılımı (Bölüm Bazlı)")
st.pyplot(fig)

st.success("Planlama tamamlandı! Tüm vardiyalar dengeli, FTE değerleri hesaplandı.")
