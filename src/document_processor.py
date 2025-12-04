import os
import io
import PyPDF2
import docx
import pandas as pd

class DocumentProcessor:
    def __init__(self):
        pass
        
    def process_files(self, uploaded_files):
        """
        Process a list of uploaded files (Streamlit UploadedFile objects)
        and return a combined text string and file details.
        """
        combined_text = ""
        file_details = []

        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            file_ext = os.path.splitext(file_name)[1].lower()
            content = ""
            
            try:
                if file_ext == '.pdf':
                    content = self._read_pdf(uploaded_file)
                elif file_ext == '.docx':
                    content = self._read_docx(uploaded_file)
                elif file_ext == '.txt':
                    content = self._read_txt(uploaded_file)
                elif file_ext in ['.xlsx', '.xls']:
                    content = self._read_excel(uploaded_file)
                else:
                    content = f"[Skipped unsupported file format: {file_name}]"

                if content:
                    combined_text += f"\n\n--- Content from {file_name} ---\n{content}"
                    file_details.append({"name": file_name, "status": "Processed"})
                else:
                     file_details.append({"name": file_name, "status": "Empty or Unreadable"})

            except Exception as e:
                file_details.append({"name": file_name, "status": f"Error: {str(e)}"})
                combined_text += f"\n\n--- Error reading {file_name} ---\n{str(e)}"

        return {
            "combined_text": combined_text.strip(),
            "file_details": file_details
        }

    def _read_pdf(self, file):
        text = ""
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
        return text

    def _read_docx(self, file):
        text = ""
        try:
            doc = docx.Document(file)
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            return f"Error reading DOCX: {str(e)}"
        return text

    def _read_txt(self, file):
        try:
            # uploaded_file is a binary IO, so decode it
            return file.getvalue().decode("utf-8")
        except Exception as e:
            return f"Error reading TXT: {str(e)}"

    def _read_excel(self, file):
        text = ""
        try:
            # Read all sheets
            xls = pd.read_excel(file, sheet_name=None)
            for sheet_name, df in xls.items():
                text += f"\nSheet: {sheet_name}\n"
                text += df.to_string(index=False)
        except Exception as e:
            return f"Error reading Excel: {str(e)}"
        return text
