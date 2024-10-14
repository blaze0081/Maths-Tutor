import streamlit as st
import openai 
import fitz  # PyMuPDF
import toml
from io import BytesIO
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import re
from google.cloud import translate_v2 as translate
import html

openai.api_key = st.secrets["openai"]["api_key"]

querry_context = ""

def extract_text_from_pdf(pdf_file):
    document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page_num in range(len(document)):
        page = document.load_page(page_num)
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

def query_document(question, document_text, language):
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"You are a maths tutor and you have to make some questions. If another question paper is uploaded then make questions on same topic. Respond in {language}."},
            {"role": "user", "content": f"The following is a document: {document_text}"},
            {"role": "user", "content": f"Question: {question}"}
        ]
    )
    answer = response.choices[0].message.content

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
    return processed_answer

def create_pdf(text):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    lines = text.split("\n")
    y = height - 40
    for line in lines:
        p.drawString(40, y, line)
        y -= 15
        if y < 40:
            p.showPage()
            y = height - 40

    p.save()
    buffer.seek(0)
    return buffer

def create_word_doc(text):
    doc = Document()
    lines = text.split("\n")
    for line in lines:
        doc.add_paragraph(line)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def main():
    st.set_page_config(page_title="Generate Questions")
    st.header("Generate Questions")

    toughness = st.selectbox(
        "Toughness of questions",
        ("Medium", "Hard")
    )

    language = st.selectbox(
        "Language to generate in",
        ("English", "Hindi")
    )
    number = st.number_input("Insert a number of questions", 1, 50)

    question_type = st.selectbox(
        "Type of questions",
        ("Multiple Choice Questions", "Fill in the Blanks", "Short Answer Type", "True and False")
    )

    user_question = f"Generate {number} questions to ask students in examinations in {language} of {question_type} with difficulty {toughness} from the content of this document and list their answers after listing all the questions."
    
    uploaded_file = st.sidebar.file_uploader("Choose a PDF file", type=["pdf"])
    if uploaded_file is not None:
        st.sidebar.write("Document uploaded successfully!")
        
        if st.button("Process"):
            with st.spinner("Extracting text from PDF..."):
                document_text = extract_text_from_pdf(uploaded_file)
            with st.spinner("Querying the document..."):
                answer = query_document(user_question, document_text, language)
                st.subheader("Generated Questions and Answers")
                st.markdown(answer)  # Using st.markdown to render LaTeX
                word_doc = create_word_doc(answer)
                st.download_button(
                    label="Download Word Document",
                    data=word_doc,
                    file_name="questions_and_answers.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                pdf = create_pdf(answer)
                st.download_button(
                    label="Download PDF",
                    data=pdf,
                    file_name="questions_and_answers.pdf",
                    mime="application/pdf"
                )
    
if __name__ == "__main__":
    main()
