import google.generativeai as genai
import os
from dotenv import load_dotenv
import re

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-pro")

def generate_data_model(metadata_dict, schema_type):
    prompt = f"""
You are an expert Snowflake data modeler. Given this metadata (in JSON format), generate a consistent response with the following exact structure:

### Output Structure:
1. **Data Model Summary** (Markdown)
2. **Fact and Dimension Table List** (Markdown)
3. **ERD Diagram** - Mermaid `erDiagram` inside a code block
4. **Snowflake DDL** - SQL code to create tables (inside ```sql block)
5. **Relationships and Join Logic** (SQL or Markdown)
6. **Brief Explanation** - of design decisions

### Requirements:
- Format everything in **Markdown**, with appropriate code blocks.
- Ensure Mermaid is valid and begins with `erDiagram`.
- Keep the structure consistent.

### Metadata:
```json
{metadata_dict}
```

Generate a **{schema_type}** schema.
"""
    response = model.generate_content(prompt)
    return response.text

def validate_and_autocorrect_mermaid_code(code: str):

    prompt = f"""
            You are a Mermaid.js expert.

            1. Validate the following Mermaid ER diagram.
            2. If it is invalid, fix the syntax and return the corrected version.
            3. If it is valid, return it as-is.

            Only return the corrected Mermaid code inside a single ```mermaid code block.
            (strictly enforce v11-compatible ERD syntax)

            Here is the code:
            ```mermaid
            {code}
"""
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        match = re.search(r'```mermaid\n(.*?)```', response_text, re.DOTALL)
        if match:
            repaired_code = match.group(1).strip()
            return True, repaired_code, None
        elif "valid" in response_text.lower():
            return True, code, None
        else:
            return False, None, "Could not extract valid Mermaid code."
    except Exception as e:
        return False, None, str(e)



def ask_schema_question(question, metadata_dict):
    prompt = f"""
You are a Snowflake metadata expert. Use the following table metadata to answer this question:

### Metadata:
```json
{metadata_dict}
```

### Question:
{question}

Be accurate and concise.
"""
    response = model.generate_content(prompt)
    return response.text
