import streamlit as st
import openai
import fitz  # PyMuPDF
import toml
import os

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
def query_document(question, document_text, conversation_history, language):
    conversation_history.append({"role": "user", "content": question})
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"You are a math tutor which replies in {language}."},
            {"role": "user", "content": f"The following is a document: {document_text}"},
        ] + conversation_history
    )
    answer = response.choices[0].message["content"]
    conversation_history.append({"role": "assistant", "content": answer})
    
    return answer


# Main function for the Streamlit app
def main():
    st.set_page_config(page_title="Maths ChatBot", page_icon="📚", layout="wide")

    st.title("Maths ChatBot Class 12")

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


        st.header("Select a Chapter")

        # Using a form for chapter selection and submit action
        with st.form(key="chapter_form"):
            chapter = st.selectbox("Chapter Number", list(range(1, 14)))
            submit_button = st.form_submit_button(label="Submit")

        # Add a reset button in the sidebar
        if st.button("Reset Conversation"):
            # Clear session state
            st.session_state.conversation_history = []
            st.session_state.document_text = ""
            st.rerun()  # Refresh the app to reset the UI

    # Process the chat only if the submit button is clicked
    if submit_button: 
        # Load the corresponding PDF based on the selected chapter
        if language == "***English***":
            pdf_path = f"./NCERT_class_12_eng/{chapter}.pdf"
        elif language == "***Hindi***":
            pdf_path = f"./NCERT_class_12_hin/{chapter}.pdf"
        else:
            st.error("Language not selected")
        
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as pdf_file:
                # Store extracted document text in session state
                st.session_state.document_text = extract_text_from_pdf(pdf_file)
        else:
            st.error(f"PDF for Chapter {chapter} not found.")

    # Check if the document text has been loaded
    if st.session_state.document_text:
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
            answer = query_document(prompt, st.session_state.document_text, st.session_state.conversation_history, language)
            with st.chat_message("assistant"):
                print(answer)
                st.markdown(answer)

if __name__ == "__main__":
    main()