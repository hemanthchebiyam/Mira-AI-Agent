import os
import io
import re
import chardet
import pandas as pd
import docx

# Try to import better PDF libraries, fallback to PyPDF2
try:
    import pdfplumber
    PDF_PARSER = 'pdfplumber'
except ImportError:
    try:
        import fitz  # PyMuPDF (imported as fitz)
        PDF_PARSER = 'pymupdf'
    except ImportError:
        import PyPDF2
        PDF_PARSER = 'pypdf2'


class DocumentProcessor:
    def __init__(self):
        self.supported_formats = ['.pdf', '.docx', '.txt', '.xlsx', '.xls']
        
    def process_files(self, uploaded_files):
        """
        Process a list of uploaded files (Streamlit UploadedFile objects)
        and return a combined text string and file details.
        
        Args:
            uploaded_files: List of Streamlit UploadedFile objects
            
        Returns:
            dict with 'combined_text' and 'file_details' keys
        """
        combined_text = ""
        file_details = []

        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            file_ext = os.path.splitext(file_name)[1].lower()
            content = ""
            metadata = {}
            
            try:
                if file_ext == '.pdf':
                    content, metadata = self._read_pdf(uploaded_file)
                elif file_ext == '.docx':
                    content, metadata = self._read_docx(uploaded_file)
                elif file_ext == '.txt':
                    content, metadata = self._read_txt(uploaded_file)
                elif file_ext in ['.xlsx', '.xls']:
                    content, metadata = self._read_excel(uploaded_file)
                else:
                    content = f"[Skipped unsupported file format: {file_name}]"
                    metadata = {"error": "Unsupported format"}

                if content and not content.startswith("[Skipped") and not content.startswith("Error"):
                    # Add metadata info if available
                    metadata_str = ""
                    if metadata:
                        if 'pages' in metadata:
                            metadata_str = f" ({metadata['pages']} pages)"
                        elif 'sheets' in metadata:
                            metadata_str = f" ({len(metadata['sheets'])} sheets)"
                        elif 'encoding' in metadata:
                            metadata_str = f" (encoding: {metadata['encoding']})"
                    
                    combined_text += f"\n\n--- Content from {file_name}{metadata_str} ---\n{content}"
                    file_details.append({
                        "name": file_name, 
                        "status": "Processed",
                        "metadata": metadata
                    })
                else:
                    file_details.append({
                        "name": file_name, 
                        "status": "Empty or Unreadable",
                        "metadata": metadata
                    })

            except Exception as e:
                error_msg = str(e)
                file_details.append({
                    "name": file_name, 
                    "status": f"Error: {error_msg}",
                    "metadata": {"error": error_msg}
                })
                combined_text += f"\n\n--- Error reading {file_name} ---\n{error_msg}"

        return {
            "combined_text": combined_text.strip(),
            "file_details": file_details
        }

    def _read_pdf(self, file):
        """
        Read PDF file with improved text extraction.
        Tries pdfplumber first, then pymupdf, then PyPDF2 as fallback.
        
        Returns:
            tuple: (text_content, metadata_dict)
        """
        text = ""
        metadata = {}
        
        try:
            # Reset file pointer
            file.seek(0)
            
            if PDF_PARSER == 'pdfplumber':
                with pdfplumber.open(file) as pdf:
                    metadata['pages'] = len(pdf.pages)
                    metadata['parser'] = 'pdfplumber'
                    
                    for i, page in enumerate(pdf.pages):
                        page_text = page.extract_text()
                        if page_text:
                            text += f"\n[Page {i+1}]\n{page_text}\n"
                        
                        # Try to extract tables
                        tables = page.extract_tables()
                        if tables:
                            for table in tables:
                                text += "\n[Table]\n"
                                for row in table:
                                    if row:
                                        text += " | ".join(str(cell) if cell else "" for cell in row) + "\n"
                                text += "\n"
            
            elif PDF_PARSER == 'pymupdf':
                import fitz  # PyMuPDF
                file.seek(0)
                pdf_bytes = file.read()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                metadata['pages'] = len(doc)
                metadata['parser'] = 'pymupdf'
                
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    page_text = page.get_text()
                    if page_text:
                        text += f"\n[Page {page_num+1}]\n{page_text}\n"
                
                doc.close()
            
            else:  # PyPDF2 fallback
                file.seek(0)
                pdf_reader = PyPDF2.PdfReader(file)
                metadata['pages'] = len(pdf_reader.pages)
                metadata['parser'] = 'pypdf2'
                
                for i, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n[Page {i+1}]\n{page_text}\n"
            
            # Clean up excessive whitespace
            text = re.sub(r'\n{3,}', '\n\n', text)
            
        except Exception as e:
            return f"Error reading PDF: {str(e)}", {"error": str(e)}
        
        return text.strip(), metadata

    def _read_docx(self, file):
        """
        Read DOCX file with support for paragraphs, tables, lists, and formatting.
        
        Returns:
            tuple: (text_content, metadata_dict)
        """
        text = ""
        metadata = {}
        
        try:
            file.seek(0)
            doc = docx.Document(file)
            
            # Count elements
            para_count = len(doc.paragraphs)
            table_count = len(doc.tables)
            
            metadata['paragraphs'] = para_count
            metadata['tables'] = table_count
            
            # Process paragraphs
            for para in doc.paragraphs:
                para_text = para.text.strip()
                if para_text:
                    # Check if it's a heading
                    if para.style.name.startswith('Heading'):
                        level = para.style.name.replace('Heading ', '')
                        text += f"\n{'#' * int(level)} {para_text}\n" if level.isdigit() else f"\n## {para_text}\n"
                    else:
                        text += para_text + "\n"
            
            # Process tables
            for table_idx, table in enumerate(doc.tables):
                text += f"\n[Table {table_idx + 1}]\n"
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells)
                    if row_text.strip():
                        text += row_text + "\n"
                text += "\n"
            
            # Clean up
            text = re.sub(r'\n{3,}', '\n\n', text)
            
        except Exception as e:
            return f"Error reading DOCX: {str(e)}", {"error": str(e)}
        
        return text.strip(), metadata

    def _read_txt(self, file):
        """
        Read TXT file with automatic encoding detection.
        
        Returns:
            tuple: (text_content, metadata_dict)
        """
        metadata = {}
        
        try:
            file.seek(0)
            raw_data = file.read()
            
            # Detect encoding
            detected = chardet.detect(raw_data)
            encoding = detected.get('encoding', 'utf-8')
            confidence = detected.get('confidence', 0)
            
            metadata['encoding'] = encoding
            metadata['confidence'] = f"{confidence:.2%}"
            
            # Try to decode with detected encoding
            try:
                text = raw_data.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                # Fallback to utf-8 with error handling
                text = raw_data.decode('utf-8', errors='replace')
                metadata['encoding'] = 'utf-8 (fallback)'
            
            # Clean up line endings
            text = text.replace('\r\n', '\n').replace('\r', '\n')
            
        except Exception as e:
            return f"Error reading TXT: {str(e)}", {"error": str(e)}
        
        return text.strip(), metadata

    def _read_excel(self, file):
        """
        Read Excel file with improved structure preservation.
        Handles multiple sheets, preserves table structure, and extracts metadata.
        
        Returns:
            tuple: (text_content, metadata_dict)
        """
        text = ""
        metadata = {}
        
        try:
            file.seek(0)
            
            # Determine engine based on file extension
            # Try openpyxl for .xlsx, xlrd for .xls (if available)
            file_ext = getattr(file, 'name', '').lower()
            engine = 'openpyxl' if file_ext.endswith('.xlsx') else None
            
            # Read all sheets
            excel_file = pd.ExcelFile(file, engine=engine)
            sheet_names = excel_file.sheet_names
            metadata['sheets'] = sheet_names
            metadata['sheet_count'] = len(sheet_names)
            
            for sheet_name in sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                
                text += f"\n{'='*60}\n"
                text += f"Sheet: {sheet_name}\n"
                text += f"{'='*60}\n\n"
                
                if df.empty:
                    text += "[Empty sheet]\n\n"
                    continue
                
                # Add column names
                text += "Columns: " + ", ".join(str(col) for col in df.columns) + "\n\n"
                
                # Convert DataFrame to string with better formatting
                # For small tables, use to_string
                if len(df) <= 100:
                    text += df.to_string(index=False, max_rows=None) + "\n\n"
                else:
                    # For large tables, show first and last few rows
                    text += "[First 50 rows]\n"
                    text += df.head(50).to_string(index=False) + "\n\n"
                    text += f"[... {len(df) - 100} rows omitted ...]\n\n"
                    text += "[Last 50 rows]\n"
                    text += df.tail(50).to_string(index=False) + "\n\n"
                
                # Add summary statistics for numeric columns
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    text += "\n[Summary Statistics]\n"
                    summary = df[numeric_cols].describe()
                    text += summary.to_string() + "\n\n"
            
            excel_file.close()
            
        except Exception as e:
            return f"Error reading Excel: {str(e)}", {"error": str(e)}
        
        return text.strip(), metadata
