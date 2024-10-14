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
def extract_text_from_pdf(file):
    # Open the file using a file-like object (not a file path)
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        text = ""
        for page in doc:
            text += page.get_text()
    return text


def query_document(question, conversation_history, language, document_text=None):
    conversation_history.append({"role": "user", "content": question})
    
    if document_text:
        system_message = f"You are a math tutor which replies in {language}. Use the following document context to answer the question. The document text is: {document_text}."
    else:
        system_message = f"You are a math tutor which replies in {language}."
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_message},
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
            if language.lower() != "english":
                translated_part = translate_text(part, language)
                processed_parts.append(translated_part)
            else:
                processed_parts.append(part)
    
    processed_answer = ''.join(processed_parts)
    conversation_history.append({"role": "assistant", "content": processed_answer})
    
    return processed_answer

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
    
    if target_language.lower() == 'hindi':
        target_language = 'hi'
    # Add more language mappings as needed
    
    result = translate_client.translate(text, target_language=target_language)
    
    # Decode HTML entities that might be present in the translated text
    translated_text = html.unescape(result['translatedText'])
    
    return translated_text

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
            if message["role"] == "user":
                st.markdown(f"**Question:** {message['content']}")
            else:
                st.markdown(f"**Answer:** {message['content']}")

    # Input box for the user's question
    if prompt := st.chat_input("Ask a question about the uploaded document or anything else:"):
        # Add user message to chat history
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        
        # Display the user's question
        with st.chat_message("user"):
            st.markdown(f"**Question:** {prompt}")

        # Get assistant response and update chat history
        document_text = st.session_state.document_text if uploaded_file is not None else None
        
        # Convert the language selection to the format expected by query_document
        selected_language = "Hindi" if language == "***Hindi***" else "English"
        
        answer = query_document(prompt, st.session_state.conversation_history, selected_language, document_text)
        
        # Display the assistant's answer
        with st.chat_message("assistant"):
            st.markdown(f"**Answer:** {answer}")

if __name__ == "__main__":
    main()
