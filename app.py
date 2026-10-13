import streamlit as st
import os
import re
import pandas as pd
import zipfile
import shutil
import tkinter as tk
from tkinter import filedialog

# --- STATE INITIALIZATION ---
if "source_folder" not in st.session_state:
    st.session_state.source_folder = ""
if "local_processing_complete" not in st.session_state:
    st.session_state.local_processing_complete = False
if "local_success_count" not in st.session_state:
    st.session_state.local_success_count = 0
if "local_pending_count" not in st.session_state:
    st.session_state.local_pending_count = 0

def select_folder():
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1) 
    folder_path = filedialog.askdirectory(master=root)
    root.destroy()
    return folder_path

st.set_page_config(page_title="Digital Auto Folder Organizer", page_icon="📂", layout="wide")

st.markdown("""
    <style>
    .metric-box { background-color: #F3F4F6; padding: 18px; border-radius: 10px; border-left: 6px solid #1E40AF; box-shadow: 0 2px 4px rgba(0,0,0,0.04); }
    .success-box { background-color: #ECFDF5; color: #047857; padding: 16px; border-radius: 8px; border: 1px solid #10B981; margin-top: 20px; font-size: 16px; }
    .premium-card { background: #FFFFFF; padding: 24px; border-radius: 14px; border-bottom: 5px solid #CBD5E1; box-shadow: 0 4px 20px rgba(0,0,0,0.03); text-align: center; }
    .card-title { font-size: 12px; color: #64748B; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .card-value { font-size: 38px; font-weight: 800; margin-top: 8px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("## 📦 Auto ZIP & Local File Organizer")
st.markdown("📌 **Select the folder containing your Excel sheet and .zip files. The tool will auto-detect everything and organize files automatically into an 'Organized_Data' folder inside it.**")
st.write("---")

st.markdown("### ⚙️ Select Source Folder")

col1, col2 = st.columns([4, 1])

with col1:
    manual_path = st.text_input("Source Path (Where ZIPs & Excel are):", value=st.session_state.source_folder)
    if manual_path != st.session_state.source_folder:
        st.session_state.source_folder = manual_path

with col2:
    st.write("") 
    st.write("") 
    if st.button("📂 Browse Folder", use_container_width=True):
        folder = select_folder()
        if folder:
            st.session_state.source_folder = folder
            st.rerun()

output_folder = ""
if st.session_state.source_folder:
    output_folder = os.path.join(st.session_state.source_folder, "Organized_Data")
    st.info(f"📂 **Output will be saved automatically to:** `{output_folder}`")

st.write("---")

run_organizer = st.button("🔄 Extract & Organize Files", type="primary", use_container_width=True, disabled=(not st.session_state.source_folder))

if run_organizer:
    src = st.session_state.source_folder
    if not os.path.exists(src):
        st.error("❌ Source folder does not exist. Please check the path.")
    else:
        st.session_state.local_processing_complete = False
        st.session_state.local_success_count = 0
        st.session_state.local_pending_count = 0
        
        with st.status("Auto-Detecting and Organizing...", expanded=True) as status_box:
            try:
                excel_files = [f for f in os.listdir(src) if f.lower().endswith('.xlsx') and not f.startswith('~$')]
                if not excel_files:
                    st.error("❌ No .xlsx file found in the source folder!")
                    status_box.update(state="error")
                    st.stop()
                
                excel_path = os.path.join(src, excel_files[0])
                status_box.write(f"📄 Found Excel: {excel_files[0]}")
                
                df_local = pd.read_excel(excel_path)
                if 'CUSTOMER NAME' not in df_local.columns or 'AGREEMENT NO' not in df_local.columns:
                    st.error("Excel must contain 'CUSTOMER NAME' and 'AGREEMENT NO' columns.")
                    status_box.update(state="error")
                    st.stop()
                    
                df_local = df_local.dropna(subset=['CUSTOMER NAME', 'AGREEMENT NO'])
                mapping = {str(row['CUSTOMER NAME']).strip().upper(): str(row['AGREEMENT NO']).strip() for _, row in df_local.iterrows()}

                os.makedirs(output_folder, exist_ok=True)
                pending_folder = os.path.join(output_folder, "Pending")
                os.makedirs(pending_folder, exist_ok=True)

                status_box.write("🔍 Scanning and Extracting files...")
                
                def process_file(filename, file_data=None, original_path=None):
                    match = re.match(r'^\d+\s+(.*)\.\w+$', filename)
                    extracted_name = match.group(1).strip().upper() if match else os.path.splitext(filename)[0].strip().upper()

                    matched = False
                    for excel_name, agr_no in mapping.items():
                        if excel_name == extracted_name or excel_name in extracted_name:
                            target_folder = os.path.join(output_folder, agr_no)
                            os.makedirs(target_folder, exist_ok=True)
                            dest_path = os.path.join(target_folder, filename)
                            matched = True
                            break
                            
                    if not matched:
                        dest_path = os.path.join(pending_folder, filename)
                        
                    if file_data:
                        with open(dest_path, 'wb') as f:
                            f.write(file_data)
                    elif original_path:
                        shutil.copy2(original_path, dest_path)
                        
                    if matched:
                        st.session_state.local_success_count += 1
                    else:
                        st.session_state.local_pending_count += 1

                zip_files = [f for f in os.listdir(src) if f.lower().endswith('.zip')]
                for zip_name in zip_files:
                    status_box.write(f"📦 Extracting from: {zip_name}")
                    zip_path = os.path.join(src, zip_name)
                    with zipfile.ZipFile(zip_path, 'r') as z:
                        for item in z.infolist():
                            if item.is_dir(): continue
                            filename = os.path.basename(item.filename)
                            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf')): continue
                            file_data = z.read(item.filename)
                            process_file(filename, file_data=file_data)

                for root_dir, dirs, files in os.walk(src):
                    if output_folder in root_dir: continue
                    for file in files:
                        if file.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf')):
                            process_file(file, original_path=os.path.join(root_dir, file))

                status_box.update(label="✅ File Extraction & Organization Complete!", state="complete", expanded=False)
                st.session_state.local_processing_complete = True
                st.balloons()
                    
            except Exception as e:
                st.error(f"Error during organizing: {e}")
                status_box.update(state="error")

if st.session_state.local_processing_complete:
    st.write("---")
    st.markdown("### 🏁 Organization Summary")
    m1, m2 = st.columns(2)
    with m1:
        st.markdown(f'<div class="premium-card" style="border-bottom: 5px solid #10B981;"><span class="card-title">Successfully Matched</span><div class="card-value" style="color:#10B981;">{st.session_state.local_success_count}</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="premium-card" style="border-bottom: 5px solid #F59E0B;"><span class="card-title">Sent to Pending</span><div class="card-value" style="color:#F59E0B;">{st.session_state.local_pending_count}</div></div>', unsafe_allow_html=True)