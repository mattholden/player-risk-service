"""
Streamlit Dashboard for Player Risk Service.

This is an internal tool for:
- Demoing the service to stakeholders
- Manual player monitoring
- Uploading players to track
- Viewing risk assessments

This UI calls the backend API (src/) for all data.
Keep this simple and focused on business value demo.
"""

import streamlit as st
import requests
import pandas as pd
import os
from datetime import datetime

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")  # Backend API

# Page config
st.set_page_config(
    page_title="Player Risk Monitor",
    page_icon="⚠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("⚠️ Player Risk Monitor")
st.markdown("*Real-time injury and playing time risk assessment*")

# Sidebar
with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Select Page",
        ["Dashboard", "Upload Players", "Risk Assessments", "Articles"]
    )
    
    st.markdown("---")
    st.caption("Player Risk Service v0.1.0")

# Main content based on page selection
if page == "Dashboard":
    st.header("📊 Risk Dashboard")
    
    # Placeholder for when API is ready
    st.info("🚧 Dashboard coming soon - will show high-risk players in real-time")
    
    # Mock data for demo
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Players", "0", delta="0")
    with col2:
        st.metric("High Risk", "0", delta="0")
    with col3:
        st.metric("Articles Today", "0", delta="0")
    with col4:
        st.metric("LLM Analyses", "0", delta="0")
    
    st.markdown("---")
    
    # Placeholder table
    st.subheader("🔴 High Risk Players")
    st.caption("Players requiring immediate attention")
    
    # Empty state
    st.info("No high-risk players at this time")

elif page == "Upload Players":
    st.header("➕ Add Players to Monitor")
    
    with st.form("add_player_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            player_name = st.text_input("Player Name", placeholder="e.g., Jaden Ivey")
            team = st.text_input("Team", placeholder="e.g., Detroit Pistons")
        
        with col2:
            position = st.selectbox("Position", ["PG", "SG", "SF", "PF", "C"])
            
        submitted = st.form_submit_button("Add Player")
        
        if submitted:
            if player_name:
                # TODO: Call backend API to add player
                # response = requests.post(f"{API_BASE_URL}/players", json={...})
                st.success(f"✅ Added {player_name} to monitoring (mock)")
            else:
                st.error("Please enter a player name")
    
    st.markdown("---")
    
    # Bulk upload
    st.subheader("📄 Bulk Upload")
    uploaded_file = st.file_uploader("Upload CSV with players", type=['csv'])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df)
        if st.button("Upload All"):
            st.success(f"✅ Uploaded {len(df)} players (mock)")

elif page == "Risk Assessments":
    st.header("📋 Risk Assessments")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        risk_filter = st.selectbox("Risk Level", ["All", "Critical", "High", "Medium", "Low"])
    with col2:
        date_filter = st.date_input("From Date", datetime.now())
    with col3:
        player_filter = st.text_input("Search Player")
    
    st.markdown("---")
    
    # Placeholder
    st.info("🚧 Risk assessments will appear here once articles are analyzed")

elif page == "Articles":
    st.header("📰 News Articles")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        source_filter = st.multiselect("Source", ["ESPN", "The Athletic", "CBS Sports"])
    with col2:
        date_range = st.date_input("Date Range", [])
    
    st.markdown("---")
    
    # Placeholder
    st.info("🚧 Articles will be fetched from NewsAPI and displayed here")

# Footer
st.markdown("---")
st.caption("Built with Streamlit • Powered by AI")

