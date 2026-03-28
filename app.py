import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from io import BytesIO

# --- CORE LOGIC ---

def get_bank_name(routing_number):
    """Scrapes the Federal Reserve portal for the official bank name."""
    url = f"https://www.frbservices.org/p-search-fedach?routing={routing_number}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        name_cell = soup.find("td", {"data-label": "Bank Name"})
        return name_cell.text.strip() if name_cell else "Not Found"
    except:
        return "Search Error"

def get_bank_urls(bank_name):
    """Finds Home and Login URLs using DuckDuckGo Lite (No API required)."""
    if bank_name in ["Not Found", "Search Error"]:
        return {"home": "N/A", "login": "N/A"}
    
    query = f"{bank_name} official website online banking login"
    # Using DDG Lite for simple HTML structure
    search_url = f"https://duckduckgo.com/lite/?q={query.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        res = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        links = [a["href"] for a in soup.find_all("a", class_="result-link")]
        
        home = links[0] if links else "N/A"
        login = "N/A"
        # Search snippets for common login indicators
        for link in links[:5]:
            if any(term in link.lower() for term in ["login", "portal", "signin", "online"]):
                login = link
                break
        return {"home": home, "login": login if login != "N/A" else home}
    except:
        return {"home": "N/A", "login": "N/A"}

# --- STREAMLIT UI ---

st.set_page_config(page_title="Free Bank Routing Lookup Agent", layout="wide")
st.title("🏦 Bank Routing Lookup Agent")
st.markdown("Lookup Bank Names, Home URLs, and Login Pages for free using Federal Reserve & DDG data.")

# Input Section
input_mode = st.radio("Choose Input Type:", ["Single / Multiple (Comma Separated)", "Bulk Upload (Excel)"])

routing_numbers = []

if input_mode == "Single / Multiple (Comma Separated)":
    text_input = st.text_input("Enter Routing Number(s):", placeholder="e.g., 021000021, 121000358")
    if text_input:
        routing_numbers = [x.strip() for x in text_input.split(",")]

else:
    uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "xls"])
    if uploaded_file:
        df_input = pd.read_excel(uploaded_file)
        # Assumes the first column contains the routing numbers
        routing_numbers = df_input.iloc[:, 0].astype(str).tolist()

# Execution Section
if st.button("Run Agent"):
    if not routing_numbers:
        st.warning("Please provide at least one routing number.")
    else:
        results = []
        progress_bar = st.progress(0)
        
        for i, rn in enumerate(routing_numbers):
            name = get_bank_name(rn)
            urls = get_bank_urls(name)
            results.append({
                "Routing Number": rn,
                "Bank Name": name,
                "Home URL": urls["home"],
                "Login URL": urls["login"]
            })
            progress_bar.progress((i + 1) / len(routing_numbers))
            time.sleep(1) # Be respectful to the servers

        df_results = pd.DataFrame(results)
        
        # Display Results
        st.subheader("Results")
        st.dataframe(df_results)
        
        # Download Buttons
        col1, col2 = st.columns(2)
        
        # JSON Download
        json_data = df_results.to_json(orient="records", indent=4)
        col1.download_button("Download JSON", data=json_data, file_name="bank_data.json", mime="application/json")
        
        # Excel Download
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_results.to_excel(writer, index=False)
        col2.download_button("Download Excel", data=output.getvalue(), file_name="bank_data.xlsx", mime="application/vnd.ms-excel")

st.info("💡 **Note:** This tool uses free scraping methods. For large files (100+ rows), please allow several minutes to complete due to server rate limits.")