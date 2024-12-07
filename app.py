import streamlit as st
import json
import re
from langchain_community.llms import HuggingFaceEndpoint
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

# Initialize Hugging Face model
llm = HuggingFaceEndpoint(
    endpoint_url="https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct",
    huggingfacehub_api_token="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",
    temperature=0.1,
    max_new_tokens=40,
)

# Initialize database
db = SQLDatabase.from_uri("sqlite:///myskills.db")

# Examples for few-shot prompting
examples = [
   {
        "input": "How many distinct roles are there in the system?",
        "query": "SELECT COUNT(DISTINCT role_id) AS role_count FROM allrolesreport;"
    },
    {
        "input": "Find all roles and the number of skills they have, including the names of skill sets.",
        "query": "SELECT r.role_title, COUNT(ss.skill_set_id) AS num_skill_sets FROM allrolesreport r JOIN skillsetrolematrixreport sr ON r.role_id = sr.role_id JOIN skillsetskillmatrixreport ss ON sr.skill_set_id = ss.skill_set_id GROUP BY r.role_title;"
    },
    {
        "input": "How many people are from the lead countries 'Germany', 'Switzerland', and 'Austria'?",
        "query": "SELECT lead_country, COUNT(user) AS user_count FROM userskillstatusreport WHERE lead_country IN ('Germany', 'Switzerland', 'Austria') GROUP BY lead_country;"
    },
    {
        "input": "How many skills are associated with skillset id 'lex_skillset_1629811534915930'?",
        "query": "SELECT COUNT(skill_id) AS skill_count FROM skillsetskillmatrixreport WHERE skill_set_id = 'lex_skillset_1629811534915930';"
    },
    {
        "input": "How many users have a role status of 'started'?",
        "query": "SELECT COUNT(user) AS user_count FROM fitgapuserrolesandskillsreport WHERE status_of_role = 'started';"
    },
    {   
        "input": "Which users are assigned to the role 'Category Manager'?",
        "query": "SELECT user FROM userrolesreport WHERE role_name = 'Category Manager';"
    },
    {
        "input": "What are the roles associated with a skill set named 'Finance & Controlling Expertise'?",
        "query": "SELECT r.role_title FROM skillsetrolematrixreport s JOIN allrolesreport r ON s.role_id = r.role_id WHERE s.skill_set_name = 'Finance & Controlling Expertise';"
    },
    {
        "input": "Which roles have the most number of skills associated with them?",
        "query": "SELECT r.role_title, COUNT(s.skill_id) AS num_skills FROM allrolesreport r JOIN roleskillmatrixreport s ON r.role_id = s.role_id GROUP BY r.role_title ORDER BY num_skills DESC;"
    },
    {
        "input": "How many users have skills marked as 'Advanced' in the 'Sales' job family?",
        "query": "SELECT COUNT(user) AS user_count FROM userskillstatusreport WHERE job_family = 'Sales' AND no_of_skills_on_advanced_level > 0;"
    },
    {
        "input": "How many roles have an associated skill level of 'Basic'?",
        "query": "SELECT COUNT(DISTINCT role_id) AS role_count FROM roleskillmatrixreport WHERE skill_level = 'Basic';"
    },
]

# Define the prompt template
example_prompt = PromptTemplate.from_template("User input: {input}\nSQL query: {query}")
prompt = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    prefix="You are a SQLite expert. Given an input question, create a syntactically correct SQLite query to run. "
           "Unless otherwise specified, do not return more than {top_k} rows.\n\n"
           "Here is the relevant table info: {table_info}\n\n"
           "Below are a number of examples of questions and their corresponding SQL queries.\n\n"
           "Please strictly return only the SQL query without any explanations, comments, or additional text.",
    suffix="User input: {input}\nSQL query (return only the SQL query, no explanations, comments, or additional text): ",
    input_variables=["input", "top_k=3", "table_info"],
)

# Create the SQL query chain
write_query = create_sql_query_chain(llm, db, prompt)

# Clean generated SQL query
def clean_generated_query(generated_query):
    generated_query = generated_query.strip()
    queries = generated_query.split(';')
    for query in queries:
        query = query.strip()
        if query.startswith("SELECT"):
            query = re.sub(r"SELECT\s+.*?\bSELECT\b", "", query, flags=re.DOTALL).strip()
            return query
    return ""

# Streamlit interface configuration
st.set_page_config(page_title="My Skills Querybot", layout="wide", page_icon="🔍")
st.markdown(
    """
    <style>
        body {
            background-color: #f9f9f9;
        }
        .main > div {
            background: #ffffff;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
        }
        .stButton > button {
            background-color: #0056b3;
            color: white;
            font-weight: bold;
            border: 0;
            border-radius: 8px;
            padding: 8px 20px;
        }
        .stButton > button:hover {
            background-color: #003d80;
        }
        .stTextInput > div > div > input {
            border: 1px solid #0056b3;
            border-radius: 8px;
        }
        .sidebar .sidebar-content {
            background: #0056b3;
            color: white;
        }
        .sidebar .sidebar-content h1 {
            color: white;
        }
        .sidebar .sidebar-content p {
            color: #d9d9d9;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar instructions
with st.sidebar:
    st.title("'My Skills' Querybot")
    st.write("Use this interface to interact with the 'My Skills' database:")
    st.markdown("- Type your question in plain English.")
    st.markdown("- Click **Submit** to generate an SQL query and see the results.")
    st.write("Example: 'How many users have advanced skills in sales?'")

# Main interface
st.title("🔍 'My Skills' Querybot")
st.subheader("Ask a Question")
st.write("Ask questions about 'My Skills' data, and let the bot handle the SQL query generation and execution!")

# User input
user_input = st.text_input("Enter your question:", placeholder="E.g., How many distinct roles are there in the system?")

if st.button("Submit"):
    if user_input:
        # Generate SQL query
        try:
            response = write_query.invoke({"question": user_input})
            generated_query = response if isinstance(response, str) else ''
            cleaned_query = clean_generated_query(generated_query)

            # Display generated query
            st.subheader("Generated SQL Query")
            st.code(cleaned_query)

            # Execute SQL query
            try:
                results = db.run(cleaned_query)
                st.subheader("Query Results")
                st.write(results)
            except Exception as exec_error:
                st.error(f"Error executing query: {exec_error}")
        except Exception as llm_error:
            st.error(f"Error generating SQL query: {llm_error}")
    else:
        st.warning("Please enter a question before submitting.")

# Footer
st.markdown(
    """
    <hr style="border-top: 1px solid #ddd;">
    <p style="text-align: center; font-size: 12px; color: #666;">
    Built using Streamlit, LangChain, and Hugging Face.
    </p>
    """,
    unsafe_allow_html=True,
)


