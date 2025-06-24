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
st.title("File renaming assistant")

st.markdown("""
This tool helps you rename image files in bulk, so they follow naming conventions, comply with the European Accessability Act and are ready for use in e-mails, on website and Social Media.

### How it works:
1. Upload the images you want to rename.
2. Download an Excel template with the original file names.
3. Fill in the metadata fields in the Excel file. If a cell is left blank the app will simply skip this.
4. Upload the completed metadata file.
5. The app renames your files and gives you a ZIP with the re-named files.

### Naming rules (applied automatically):
- Use **English**
- Use **only lowercase letters**
- Use **hyphens (-)** as separator (not spaces or underscores)
- **No special characters**: æ, ø, å, %, &, @ etc.
- Keep names **short and descriptive** (max. 5–7 words)
- **Include brand name** as the final element (e.g. `-muuto`)
- Max **110 characters**, including file extension
""")

uploaded_images = st.file_uploader("1. Upload the images to be renamed", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_images:
    filenames = [img.name for img in uploaded_images]
    df_template = pd.DataFrame({
        'Original Filnavn': filenames,
        'Product family': '',
        'Product name': '',
        'Product variant': '',
        'Additional comment': '',
    })
    df_template['Brand'] = 'muuto'

    excel_bytes = BytesIO()
    df_template.to_excel(excel_bytes, index=False, engine='openpyxl')
    st.download_button("Download metadata template", data=excel_bytes.getvalue(), file_name="metadata_template.xlsx")

    st.markdown("---")
    uploaded_metadata = st.file_uploader("2. Upload the completed metadata file (Excel/CSV)", type=["csv", "xlsx"])

    if uploaded_metadata:
        try:
            if uploaded_metadata.name.endswith(".csv"):
                df = pd.read_csv(uploaded_metadata)
            else:
                df = pd.read_excel(uploaded_metadata)
        except Exception as e:
            st.error(f"Error reading file: {e}")
            st.stop()

        required_cols = ["Original Filnavn", "Product family", "Product name", "Product variant", "Additional comment", "Brand"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"The file must include the following columns: {', '.join(required_cols)}")
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
                parts = [row['Product family'], row['Product name'], row['Product variant'], row['Additional comment'], row['Brand']]
                clean_parts = []
                for part in parts:
                    p = str(part).strip().lower()
                    p = re.sub(r'[^a-z0-9\- ]', '', p)
                    p = p.replace(' ', '-')
                    clean_parts.append(p)

                new_name = '-'.join([p for p in clean_parts if p])
                new_name = re.sub(r'-+', '-', new_name)[:105]
                extension = os.path.splitext(img.name)[1].lower()
                final_name = f"{new_name}{extension}"

                output_path = os.path.join(output_dir, final_name)
                with open(output_path, "wb") as f:
                    f.write(img.read())

                renamed_files.append((img.name, final_name))

            zip_path = os.path.join(tmpdir, "renamed_images.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for file in os.listdir(output_dir):
                    zipf.write(os.path.join(output_dir, file), arcname=file)

            st.success("Files renamed successfully and ready for download")
            with open(zip_path, "rb") as f:
                st.download_button("Download ZIP with renamed files", f, file_name="renamed_images.zip")

            st.markdown("## Overview of changes")
            st.dataframe(pd.DataFrame(renamed_files, columns=["Original Filnavn", "New Filename"]))
