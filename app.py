import streamlit as st
import pandas as pd
import math
from datetime import datetime, timedelta

st.set_page_config(page_title="Üretim ve Vardiya Planlayıcı", layout="wide")

st.title("🏭 Üretim ve Vardiya Planlayıcı")

st.sidebar.header("🔧 Makine Bilgileri")
makine_sayisi = st.sidebar.number_input("Makine Sayısı", 1, 20, 3)

makineler = []
for i in range(makine_sayisi):
    with st.sidebar.expander(f"Makine {i+1}"):
        ad = st.text_input(f"Makine Adı {i+1}", f"Makine-{i+1}")
        personel = st.number_input(f"Vardiya Başına Gerekli Personel ({ad})", 1, 10, 3)
        kapasite = st.number_input(f"Saatlik Üretim Kapasitesi (kg/saat) - {ad}", 100, 5000, 1000)
        mevcut = st.number_input(f"Bölümdeki Toplam Personel ({ad})", 1, 50, 12)
        makineler.append({
            "Makine": ad,
            "Vardiya Personel": personel,
            "Kapasite": kapasite,
            "Toplam Personel": mevcut
        })

st.divider()
st.header("📦 Haftalık Üretim Planı")

uploaded_file = st.file_uploader("Excel veya CSV yükleyebilirsin (Makine - Ürün - Miktar - Teslim Tarihi)", type=["xlsx", "csv"])

if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        plan_df = pd.read_csv(uploaded_file)
    else:
        plan_df = pd.read_excel(uploaded_file)
else:
    st.info("Dosya yüklemeden örnek veriyle devam edebilirsin.")
    plan_df = pd.DataFrame({
        "Makine": [makineler[0]["Makine"], makineler[1]["Makine"], makineler[2]["Makine"]],
        "Ürün": ["Yoğurt", "Süt", "Ayran"],
        "Miktar (kg)": [12000, 8000, 15000],
        "Teslim Tarihi": [
            (datetime.today() + timedelta(days=2)).strftime("%Y-%m-%d"),
            (datetime.today() + timedelta(days=3)).strftime("%Y-%m-%d"),
            (datetime.today() + timedelta(days=4)).strftime("%Y-%m-%d")
        ]
    })

st.dataframe(plan_df, use_container_width=True)

if st.button("📅 Planı Oluştur"):
    try:
        vardiya_saat = 8
        vardiya_sayisi = 3
        plan_sonuc = []
        tarih_baslangic = datetime.today()

        for _, row in plan_df.iterrows():
            makine = next(m for m in makineler if m["Makine"] == row["Makine"])
            uretim_saati = row["Miktar (kg)"] / makine["Kapasite"]
            gerekli_vardiya_sayisi = math.ceil(uretim_saati / vardiya_saat)
            toplam_personel_ihtiyaci = gerekli_vardiya_sayisi * makine["Vardiya Personel"]

            haftalik_calisma_saati = makine["Toplam Personel"] * 42.5
            toplam_ihtiyac_saat = gerekli_vardiya_sayisi * vardiya_saat * makine["Vardiya Personel"]

            mesai_ihtiyaci = max(0, toplam_ihtiyac_saat - haftalik_calisma_saati)
            gun_sayisi = math.ceil(gerekli_vardiya_sayisi / vardiya_sayisi)

            plan_sonuc.append({
                "Makine": makine["Makine"],
                "Ürün": row["Ürün"],
                "Toplam Üretim (kg)": row["Miktar (kg)"],
                "Gerekli Vardiya": gerekli_vardiya_sayisi,
                "Toplam Personel İhtiyacı": toplam_personel_ihtiyaci,
                "Tahmini Süre (gün)": gun_sayisi,
                "Mesai (saat)": mesai_ihtiyaci
            })

        sonuc_df = pd.DataFrame(plan_sonuc)
        st.success("✅ Üretim planı başarıyla oluşturuldu!")
        st.dataframe(sonuc_df, use_container_width=True)

        # ---- MATRİKS TABLO OLUŞTURMA ----
        st.divider()
        st.subheader("📆 Vardiya Takvimi")

        tarihler = pd.date_range(datetime.today(), periods=7).strftime("%Y-%m-%d")
        personel_listesi = []
        for m in makineler:
            for i in range(m["Toplam Personel"]):
                personel_listesi.append(f"{m['Makine']}-P{i+1}")

        vardiyalar = ["V1", "V2", "V3"]
        mat = pd.DataFrame(index=personel_listesi, columns=tarihler)

        # Dağıtım
        for makine in makineler:
            personele_ait = [p for p in personel_listesi if p.startswith(makine["Makine"])]
            for t in tarihler:
                for v in vardiyalar:
                    for i in range(makine["Vardiya Personel"]):
                        if len(personele_ait) > 0:
                            kisi = personele_ait.pop(0)
                            mat.at[kisi, t] = v

        st.dataframe(mat.fillna("-"), use_container_width=True)

    except Exception as e:
        st.error(f"Hata oluştu: {e}")
