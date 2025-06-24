# rename_app.py
import streamlit as st
import pandas as pd
import zipfile
import os
import tempfile
import shutil
import re
from io import BytesIO

st.set_page_config(page_title="Image Renaming Tool", layout="centered")
st.title("📸 Image Renaming Assistant")

st.markdown("""
Upload dine billeder og få genereret en skabelon med filnavne, så du let kan angive metadata og få dem omdøbt automatisk – i overensstemmelse med navngivningsguiden:

- **Engelsk** sprog
- **KUN små bogstaver** og **bindestreger** (-)
- **Ingen specialtegn** (fx æ, ø, å, %, @, &, osv.)
- **Max 110 tegn** i filnavn
- **Kort og beskrivende** (maks. 5–7 ord)
- **Inkluder brandnavn som sidste del**
""")

uploaded_images = st.file_uploader("1️⃣ Upload billeder der skal omdøbes", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_images:
    # Generér skabelon med filnavne
    filenames = [img.name for img in uploaded_images]
    df_template = pd.DataFrame({
        'Original Filnavn': filenames,
        'Page Title': '',
        'Subject': '',
        'Version/Date': '',
    })
    df_template['Brand'] = 'muuto'  # tilføj kolonnen med standardværdi

    excel_bytes = BytesIO()
    df_template.to_excel(excel_bytes, index=False, engine='openpyxl')
    st.download_button("📥 Download metadata-skabelon", data=excel_bytes.getvalue(), file_name="metadata_template.xlsx")

    st.markdown("---")
    uploaded_metadata = st.file_uploader("2️⃣ Upload udfyldt metadata-fil (Excel/CSV)", type=["csv", "xlsx"])

    if uploaded_metadata:
        try:
            if uploaded_metadata.name.endswith(".csv"):
                df = pd.read_csv(uploaded_metadata)
            else:
                df = pd.read_excel(uploaded_metadata)
        except Exception as e:
            st.error(f"Fejl ved indlæsning af fil: {e}")
            st.stop()

        # Tjek kolonner
        required_cols = ["Original Filnavn", "Page Title", "Subject", "Version/Date", "Brand"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"Excel skal indeholde følgende kolonner: {', '.join(required_cols)}")
            st.stop()

        renamed_files = []
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "renamed")
            os.makedirs(output_dir, exist_ok=True)

            for img in uploaded_images:
                match = df[df['Original Filnavn'] == img.name]
                if match.empty:
                    continue

                row = match.iloc[0]
                parts = [row['Page Title'], row['Subject'], row['Version/Date'], row['Brand']]
                clean_parts = []
                for part in parts:
                    p = str(part).strip().lower()
                    p = re.sub(r'[^a-z0-9\- ]', '', p)
                    p = p.replace(' ', '-')
                    clean_parts.append(p)

                new_name = '-'.join([p for p in clean_parts if p])
                new_name = re.sub(r'-+', '-', new_name)[:105]  # reservér 5 tegn til extension
                extension = os.path.splitext(img.name)[1].lower()
                final_name = f"{new_name}{extension}"

                output_path = os.path.join(output_dir, final_name)
                with open(output_path, "wb") as f:
                    f.write(img.read())

                renamed_files.append((img.name, final_name))

            # ZIP
            zip_path = os.path.join(tmpdir, "renamed_images.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for file in os.listdir(output_dir):
                    zipf.write(os.path.join(output_dir, file), arcname=file)

            st.success("Filerne er omdøbt og klar til download")
            with open(zip_path, "rb") as f:
                st.download_button("📦 Download ZIP med omdøbte filer", f, file_name="renamed_images.zip")

            st.markdown("## 📋 Ændringer")
            st.dataframe(pd.DataFrame(renamed_files, columns=["Original Filnavn", "Nyt Filnavn"]))
