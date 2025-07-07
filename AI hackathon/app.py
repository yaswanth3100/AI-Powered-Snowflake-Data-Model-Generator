# File: app.py
import streamlit as st
import streamlit.components.v1 as components
import re
import uuid
from typing import Optional

from snowflake_utils import extract_table_metadata_cached
from llm_generator import generate_data_model, ask_schema_question
from llm_generator import validate_and_autocorrect_mermaid_code  

# --- Page Configuration ---
st.set_page_config(page_title="AI Data Model Generator", layout="wide")

# --- Custom Styling ---
st.markdown("""
<style>
    .main { background-color: #f9f9f9; }
    .block-container { padding: 2rem; }
    .stButton>button {
        background-color: #0066cc;
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
    }
    .stTextInput>div>input {
        border-radius: 10px;
        padding: 10px;
        border: 1px solid #ccc;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 AI-Powered Snowflake Data Model Generator")

# --- Helper Functions ---
def format_metadata(df, tables):
    return {
        table: [
            {"name": row["COLUMN_NAME"], "type": row["DATA_TYPE"]}
            for _, row in df[df["TABLE_NAME"] == table].iterrows()
        ]
        for table in tables
    }

def extract_mermaid_code(text: str) -> Optional[str]:
    match = re.search(r'```mermaid\n(.*?)```', text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else None


def render_mermaid_diagram(mermaid_code):
    div_id = f"mermaid-div-{uuid.uuid4().hex}"
    escaped_mermaid = mermaid_code.replace("`", "\\`")
    escaped_mermaid=escaped_mermaid.replace("NUMBER(38,2)", "NUMBER") 
    html_body = f"""
        <div id="{div_id}" class="mermaid">
            {mermaid_code}
        </div>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
            try {{
                mermaid.initialize({{ startOnLoad: false, theme: 'default' }});
                mermaid.parse(`{escaped_mermaid}`);
                mermaid.run();
            }} catch (e) {{
                const errorDiv = document.getElementById("{div_id}");
                if (errorDiv) {{
                    errorDiv.innerHTML = `<pre><b>Error rendering diagram:</b><br/>${{e.message}}</pre>`;
                }}
            }}
        </script>
    """
    components.html(f"<body>{html_body}</body>", height=700, scrolling=True)


# --- Load Metadata ---
try:
    with st.spinner("🔗 Connecting to Snowflake..."):
        df = extract_table_metadata_cached()
    table_list = sorted(df["TABLE_NAME"].unique())
    st.success("✅ Connected to Snowflake.")
except Exception as e:
    st.error(f"❌ Failed to connect to Snowflake: {e}")
    st.stop()

# --- Sidebar Inputs ---
st.sidebar.header("🔧 Configuration")
selected_tables = st.sidebar.multiselect("Choose tables", table_list, default=table_list)
schema_type = 'Dimensional' #st.sidebar.radio("Schema Type", ["Dimensional", "Normalized"])

if not selected_tables:
    st.warning("⚠️ Please select at least one table.")
    st.stop()

# --- Generate Data Model ---
if st.sidebar.button("🚀 Generate Data Model"):
    metadata_dict = format_metadata(df, selected_tables)

    with st.spinner("🧠 Gemini is generating the data model..."):
        llm_output = generate_data_model(metadata_dict, schema_type)

    st.success("✅ Data model generated!")

    summary = re.split(r'```', llm_output)[0].strip()
    summary = summary.replace("ERD Diagram", "").replace("ER Diagram", "").strip()

    mermaid_code = extract_mermaid_code(llm_output)
    sql_match = re.search(r'```sql\n(.*?)```', llm_output, re.DOTALL | re.IGNORECASE)
    sql_code = sql_match.group(1).strip() if sql_match else None

    tab1, tab2, tab3 , tab5, tab6 , tab4 = st.tabs(["📝 Summary", "📊 ER Diagram", "💾 SQL DDL", "Table Relationships and Logic", "Brief Explanation" , "Gemini response"])

    with tab1:
        st.header("Model Summary")
        st.markdown(summary or "No summary was generated.")

    with tab3:
        st.header("SQL Data Definition Language (DDL)")
        if sql_code:
            st.code(sql_code, language="sql")
            st.download_button("📥 Download SQL", sql_code, file_name="model_ddl.sql", mime="text/sql")
        else:
            st.warning("❌ SQL DDL not found in output.")

    with tab5:
        relationships_match = re.search(
            r'Relationships and Join Logic\s*\n+(.*?)(?=\n###|\Z)',
            llm_output,
            re.DOTALL | re.IGNORECASE
)
        if relationships_match:
            st.header("Table Relationships and Join Logic")
            relationships_text = relationships_match.group(1).strip()
            st.markdown(relationships_text)
        else:
            st.warning("No relationships or join logic found in the output.")
    
    # Display brief explanation of design decisions
    with tab6:
        explanation_match = re.search(
    r'###\s*\d*\.*\s*Brief Explanation\s*\n+(.*?)(?=\n###|\Z)',
    llm_output,
    re.DOTALL | re.IGNORECASE
        )
        if explanation_match:
            st.header("Brief Explanation of Design Decisions")
            explanation_text = explanation_match.group(1).strip()
            st.markdown(explanation_text)
        else:
            st.warning("No brief explanation found in the output.")
    
    with tab2:
        st.header("Entity Relationship Diagram (ERD)")
        if mermaid_code:
            # Validate and autocorrect Mermaid code via Gemini
            with st.spinner("🔎 Validating and repairing Mermaid syntax with Gemini..."):
                is_valid, repaired_code, error_msg = validate_and_autocorrect_mermaid_code(mermaid_code)

            if is_valid:
                st.info("✅ Mermaid code is valid.")
            else:
                st.warning("⚠️ Mermaid syntax was invalid. Attempting to auto-correct...")
                if repaired_code:
                    mermaid_code = repaired_code
                    st.success("✅ Mermaid code repaired using Gemini.")
                else:
                    st.error(f"❌ Mermaid code invalid and could not be repaired: {error_msg}")
                    with st.expander("🔍 View Full LLM Output"):
                        st.text(llm_output)
                    st.stop()

            with st.expander("🔍 View/Edit Mermaid Code"):
                st.code(mermaid_code, language="mermaid")

            render_mermaid_diagram(mermaid_code)

            standalone_html = f"""
            <!DOCTYPE html>
            <html>
            <head><title>ERD Diagram</title></head>
            <body>
                <div class="mermaid">{mermaid_code}</div>
                <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
                <script>mermaid.initialize({{startOnLoad: true}});</script>
            </body>
            </html>
            """
            st.download_button("📥 Download as HTML", standalone_html, file_name="data_model_erd.html", mime="text/html")
        else:
            st.warning("❌ Mermaid diagram not found.")
            with st.expander("🔍 View Full LLM Output"):
                st.text(llm_output)
        
            
    with tab4:
        st.header("🔍 Full LLM Output")
        st.text(llm_output)
    


# --- Optional Q&A ---
# st.markdown("---")
# st.header("💬 Ask a Follow-up Question")
# user_question = st.text_input("Ask a question about your selected tables:")
# if user_question:
#     if st.button("Ask Gemini"):
#         metadata_dict = format_metadata(df, selected_tables)
#         with st.spinner("🤔 Thinking..."):
#             answer = ask_schema_question(user_question, metadata_dict)
#             st.markdown(answer)

# --- Sidebar Footer ---
st.sidebar.markdown("---")
st.sidebar.info("This app uses AI to generate data models based on Snowflake metadata.")
st.sidebar.info("Refresh the page incase the diagram does not render properly.")

