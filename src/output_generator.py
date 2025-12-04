import os
import re
import markdown
from datetime import datetime
from xhtml2pdf import pisa
from bs4 import BeautifulSoup

class OutputGenerator:
    def __init__(self, output_dir='outputs'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def _get_paths(self, prefix, ext):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.{ext}"
        return os.path.join(self.output_dir, filename)

    def save_markdown(self, content, prefix="report"):
        path = self._get_paths(prefix, "md")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def save_txt(self, content, prefix="report"):
        path = self._get_paths(prefix, "txt")
        
        # To get a truly clean text version from Markdown, 
        # the best way is to render it to HTML and then extract text.
        html = markdown.markdown(content, extensions=['tables', 'fenced_code'])
        soup = BeautifulSoup(html, "html.parser")
        
        # Add some spacing for block elements to maintain readability
        for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr']):
            element.append('\n')
            
        text_content = soup.get_text()
        
        # Clean up excessive newlines
        text_content = re.sub(r'\n{3,}', '\n\n', text_content)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text_content.strip())
        return path
    
    def save_docx(self, content, prefix="report"):
        # We need python-docx
        import docx
        from docx.shared import Pt, RGBColor
        
        path = self._get_paths(prefix, "docx")
        doc = docx.Document()
        
        # Simple Markdown to DOCX parser
        lines = content.split('\n')
        
        # Track state for code blocks
        in_code_block = False
        
        for line in lines:
            stripped = line.strip()
            
            # Code blocks
            if stripped.startswith('```'):
                in_code_block = not in_code_block
                continue
            
            if in_code_block:
                p = doc.add_paragraph(line)
                p.style = 'Quote' # Use Quote style for code for now
                continue
                
            # Headers
            if line.startswith('# '):
                doc.add_heading(line[2:], level=1)
            elif line.startswith('## '):
                doc.add_heading(line[3:], level=2)
            elif line.startswith('### '):
                doc.add_heading(line[4:], level=3)
            elif line.startswith('#### '):
                doc.add_heading(line[5:], level=4)
            
            # List items
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                p = doc.add_paragraph(line.strip()[2:], style='List Bullet')
                
            elif re.match(r'^\d+\.\s', line.strip()):
                # Ordered list
                text = re.sub(r'^\d+\.\s', '', line.strip())
                p = doc.add_paragraph(text, style='List Number')
                
            # Table rows (basic handling: join cells with spaces)
            elif '|' in line:
                # Skip separator lines like |---|---|
                if re.match(r'^\s*\|?[-:| ]+\|?\s*$', line):
                    continue
                # Convert table row to text
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if cells:
                     doc.add_paragraph(" | ".join(cells))
                
            # Regular paragraph
            elif stripped:
                # Basic bold/italic removal for clean docx text
                clean_line = line.replace('**', '').replace('__', '')
                doc.add_paragraph(clean_line)
            else:
                # Empty line
                pass
                
        doc.save(path)
        return path

    def save_pdf(self, content, prefix="report"):
        path = self._get_paths(prefix, "pdf")
        
        # Convert MD to HTML using markdown library with extensions for tables
        html_content = markdown.markdown(content, extensions=['tables', 'fenced_code'])
        
        # Add styling for PDF
        styled_html = f"""
        <html>
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <style>
                @page {{
                    size: A4;
                    margin: 2cm;
                }}
                body {{ 
                    font-family: Helvetica, Arial, sans-serif; 
                    font-size: 11pt; 
                    line-height: 1.5;
                    color: #333;
                }}
                h1 {{ color: #2c3e50; font-size: 18pt; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 0; }}
                h2 {{ color: #2c3e50; font-size: 14pt; margin-top: 20px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
                h3 {{ color: #34495e; font-size: 12pt; margin-top: 15px; }}
                
                /* Tables */
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 15px;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                    color: #333;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                
                /* Code blocks */
                pre {{
                    background-color: #f8f9fa;
                    padding: 10px;
                    border-radius: 4px;
                    border: 1px solid #eee;
                    white-space: pre-wrap;
                }}
                code {{
                    font-family: Courier, monospace;
                    background-color: #f8f9fa;
                    padding: 2px 4px;
                }}
                
                /* Lists */
                ul, ol {{ margin-bottom: 10px; padding-left: 20px; }}
                li {{ margin-bottom: 5px; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        with open(path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(styled_html, dest=pdf_file, encoding='utf-8')
            
        if pisa_status.err:
            raise Exception("PDF generation failed")
            
        return path
