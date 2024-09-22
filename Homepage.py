import streamlit as st
import openai
import fitz  # PyMuPDF
import toml
import os
import re

# Load configuration from config.toml
config = toml.load("config.toml")
openai.api_key = config["openai"]["api_key"]

# Function to extract text from a PDF file
@st.cache_data(show_spinner=False, ttl=3600)
def extract_text_from_pdf(pdf_path):
    with fitz.open(pdf_path) as doc:
        text = ""
        for page in doc:
            text += page.get_text()
    return text

# Function to query the document and maintain the conversation context
def query_document(question, conversation_history, language):
    conversation_history.append({"role": "user", "content": question})
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"You are a math tutor which replies in {language}. Give responses in latex."},
        ] + conversation_history
    )
    answer = response.choices[0].message["content"]
    conversation_history.append({"role": "assistant", "content": answer})
    
    return answer


# Main function for the Streamlit app
def main():
    st.set_page_config(page_title="Maths ChatBot", page_icon="📚", layout="wide")
    st.title("Maths ChatBot")

    # Initialize session state for conversation history
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    
    # Initialize session state for document text
    if "document_text" not in st.session_state:
        st.session_state.document_text = ""

    # Sidebar for chapter selection and submit button
    with st.sidebar:
        st.header("Select language")

        language = st.radio("",
        ["***English***", "***Hindi***"],index=0)


        # Add a reset button in the sidebar
        if st.button("Reset Conversation"):
            # Clear session state
            st.session_state.conversation_history = []
            st.session_state.document_text = ""
            st.rerun()  # Refresh the app to reset the UI

    # Display chat messages from history
    for message in st.session_state.conversation_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    # Input box for the user's question
    if prompt := st.chat_input("Ask a question about this chapter:"):
        # Add user message to chat history and display it
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        # Get assistant response and update chat history
        answer = query_document(prompt, st.session_state.conversation_history, language)
        with st.chat_message("assistant"):
            print(answer)
            st.markdown(answer)

if __name__ == "__main__":
    main()