import streamlit as st
import openai
import fitz  # PyMuPDF
import toml
import os
import re
from google.cloud import translate_v2 as translate
import html

openai.api_key = st.secrets["openai"]["api_key"]

# Function to extract text from a PDF file
@st.cache_data(show_spinner=False, ttl=3600)
def extract_text_from_pdf(pdf_path):
    with fitz.open(pdf_path) as doc:
        text = ""
        for page in doc:
            text += page.get_text()
    return text

def convert_to_latex(math_content):
    # Use OpenAI's function calling to convert math to LaTeX
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a LaTeX conversion assistant."},
            {"role": "user", "content": f"Convert this math expression to LaTeX: {math_content}"}
        ],
        functions=[
            {
                "name": "convert_to_latex",
                "description": "Convert a math expression to LaTeX",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latex": {
                            "type": "string",
                            "description": "The LaTeX representation of the math expression"
                        }
                    },
                    "required": ["latex"]
                }
            }
        ],
        function_call={"name": "convert_to_latex"}
    )
    
    return response.choices[0].message.function_call.arguments['latex']

def translate_text(text, target_language):
    translate_client = translate.Client()
    
    # Remove asterisks and convert to lowercase
    target_language = target_language.replace('*', '').lower()
    
    if target_language == 'hindi':
        target_language = 'hi'
    elif target_language == 'english':
        return text  # No need to translate if it's already in English
    # Add more language mappings as needed
    
    result = translate_client.translate(text, target_language=target_language)
    
    # Decode HTML entities that might be present in the translated text
    translated_text = html.unescape(result['translatedText'])
    
    return translated_text

# Function to query the document and maintain the conversation context
def query_document(question, document_text, conversation_history, language):
    conversation_history.append({"role": "user", "content": question})
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"You are a math tutor which replies in {language}.If asked a question from document, list the question before answering"},
            {"role": "user", "content": f"The following is a document: {document_text}"},
        ] + conversation_history
    )
    answer = response.choices[0].message["content"]
    
    # Parse the answer to separate natural language and math parts
    parts = re.split(r'(\$.*?\$)', answer)
    
    processed_parts = []
    for part in parts:
        if part.startswith('$') and part.endswith('$'):
            # Math part: Convert to LaTeX
            math_content = part[1:-1]  # Remove the $ symbols
            latex_math = convert_to_latex(math_content)
            processed_parts.append(f'$${latex_math}$$')
        else:
            # Natural language part: Check language and translate if needed
            processed_parts.append(part)
    
    processed_answer = ''.join(processed_parts)
    conversation_history.append({"role": "assistant", "content": processed_answer})
    
    return processed_answer

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
                st.markdown(answer)

if __name__ == "__main__":
    main()
