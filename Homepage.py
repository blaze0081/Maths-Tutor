import streamlit as st
import openai
import fitz  # PyMuPDF
import toml
import os
import re

openai.api_key = st.secrets["openai"]["api_key"]

# Function to extract text from a PDF file
@st.cache_data(show_spinner=False, ttl=3600)
def extract_text_from_pdf(file):
    # Open the file using a file-like object (not a file path)
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        text = ""
        for page in doc:
            text += page.get_text()
    return text

# Function to query the document and maintain the conversation context
def query_document(question, conversation_history, language, document_text=None):
    conversation_history.append({"role": "user", "content": question})
    
    # If a document is uploaded, append the extracted text
    if document_text:
        system_message = f"You are a math tutor which replies in {language}. Use the following document context to answer the question. The document text is: {document_text}."
    else:
        system_message = f"You are a math tutor which replies in {language}."
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_message},
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

    # Sidebar for language selection and reset button
    with st.sidebar:
        st.header("Select language")

        language = st.radio("",
            ["***English***", "***Hindi***"], index=0)

        # Add a reset button in the sidebar
        if st.button("Reset Conversation"):
            # Clear session state
            st.session_state.conversation_history = []
            st.session_state.document_text = ""
            st.rerun()  # Refresh the app to reset the UI

    # File uploader to upload a PDF document
    uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")

    # Process the uploaded PDF file and extract text
    if uploaded_file is not None:
        with st.spinner('Extracting text from PDF...'):
            st.session_state.document_text = extract_text_from_pdf(uploaded_file)
        st.success("PDF text extracted successfully!")

    # Display chat messages from history
    for message in st.session_state.conversation_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input box for the user's question
    if prompt := st.chat_input("Ask a question about the uploaded document or anything else:"):
        # Add user message to chat history and display it
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get assistant response and update chat history
        document_text = st.session_state.document_text if uploaded_file is not None else None
        answer = query_document(prompt, st.session_state.conversation_history, language, document_text)
        with st.chat_message("assistant"):
            st.markdown(answer)

if __name__ == "__main__":
    main()
