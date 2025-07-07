# File: snowflake_utils.py
import snowflake.connector
import pandas as pd
import os
from dotenv import load_dotenv
import streamlit as st


load_dotenv()

def get_snowflake_connection():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE")
    )

def extract_table_metadata():
    query = """
    SELECT table_name, column_name, data_type, ordinal_position
    FROM information_schema.columns
    WHERE table_schema = CURRENT_SCHEMA()
    ORDER BY table_name, ordinal_position;
    """
    conn = get_snowflake_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

@st.cache_data(ttl=300)
def extract_table_metadata_cached():
    return extract_table_metadata()
