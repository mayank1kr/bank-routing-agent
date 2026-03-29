import streamlit as st
import pandas as pd
import json
import re
import time
from io import BytesIO
from langchain-openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.agents import initialize_agent, AgentType

# --- Streamlit UI Setup ---
st.set_page_config(page_title="Bank Finder Agent", page_icon="🏦")
st.title("🏦 Bank Routing Look-up Agent")
st.markdown("""
Extract Bank Names, Home URLs, and Login Portals using AI. 
Enter numbers manually or upload an Excel file.
""")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Enter OpenAI API Key", type="password")
    st.info("This app uses DuckDuckGo (Free) for searching to ensure accuracy.")

# --- Core Agent Logic ---
class BankingAgent:
    def __init__(self, key):
        self.llm = ChatOpenAI(model="gpt-4o", api_key=key, temperature=0)
        self.search = DuckDuckGoSearchRun()
        self.agent = initialize_agent(
            tools=[self.search],
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=False
        )

    def get_info(self, rn: str):
        prompt = (
            f"Find the Bank Name, Home URL, and Login URL for US Routing Number: {rn}. "
            "Return ONLY JSON with keys: 'routing_number', 'bank_name', 'home_url', 'login_url'."
        )
        try:
            response = self.agent.run(prompt)
            match = re.search(r'\{.*\}', response, re.DOTALL)
            return json.loads(match.group()) if match else {"routing_number": rn, "error": "Format Error"}
        except Exception as e:
            return {"routing_number": rn, "error": str(e)}

# --- App Logic ---
if api_key:
    bot = BankingAgent(api_key)
    
    tab1, tab2 = st.tabs(["Manual Input", "Bulk Upload (Excel)"])

    with tab1:
        user_input = st.text_input("Enter Routing Numbers (comma separated)", placeholder="021000021, 121000358")
        if st.button("Run Manual Search"):
            rns = [x.strip() for x in user_input.split(',') if x.strip()]
            results = []
            progress_bar = st.progress(0)
            
            for i, rn in enumerate(rns):
                res = bot.get_info(rn)
                results.append(res)
                progress_bar.progress((i + 1) / len(rns))
                time.sleep(1) # Rate limiting
            
            st.write("### Results")
            st.json(results)

    with tab2:
        uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx", "csv"])
        if uploaded_file and st.button("Process Spreadsheet"):
            df_in = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
            rns = df_in.iloc[:, 0].astype(str).tolist()
            
            results = []
            status_text = st.empty()
            progress_bar = st.progress(0)

            for i, rn in enumerate(rns):
                status_text.text(f"Searching for: {rn}...")
                res = bot.get_info(rn)
                results.append(res)
                progress_bar.progress((i + 1) / len(rns))
                time.sleep(1)

            df_out = pd.DataFrame(results)
            st.dataframe(df_out)

            # Excel Download logic
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_out.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Download Results as Excel",
                data=output.getvalue(),
                file_name="bank_details_output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
else:
    st.warning("Please enter your OpenAI API Key in the sidebar to start.")