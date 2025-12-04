import os
import re
import markdown
from datetime import datetime
from xhtml2pdf import pisa

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
        # Remove markdown syntax for plain text using regex
        # This is a basic stripper, can be enhanced
        text_content = re.sub(r'[#*_`]', '', content)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        return path
    
    def save_docx(self, content, prefix="report"):
        # We need python-docx again here if not imported globally
        import docx
        path = self._get_paths(prefix, "docx")
        doc = docx.Document()
        
        # Split by lines and add to doc
        # A simple conversion: headers based on #, others as paragraphs
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                doc.add_heading(line[2:], level=1)
            elif line.startswith('## '):
                doc.add_heading(line[3:], level=2)
            elif line.startswith('### '):
                doc.add_heading(line[4:], level=3)
            else:
                doc.add_paragraph(line)
                
        doc.save(path)
        return path

    def save_pdf(self, content, prefix="report"):
        path = self._get_paths(prefix, "pdf")
        
        # Clean content for PDF: remove emoji characters that might break xhtml2pdf
        # or replace them if possible. For now, we'll let them be but xhtml2pdf has poor emoji support.
        # We can try to replace common colored emojis with text if needed, or use a font that supports them.
        # For now, we will use a font configuration in CSS if available, or just standard cleanup.
        
        # Convert MD to HTML first
        html_content = markdown.markdown(content)
        
        # Add styling for PDF
        # Note: xhtml2pdf needs a font that supports unicode for emojis to show up, 
        # or they will be rectangles. Standard Helvetica doesn't support colored emojis.
        # We will switch to a font that has better coverage or just accept that PDF won't have colored emojis 
        # without a custom font file loaded.
        # To fix "black boxes", we can try to use a system font if available, but on cloud generic fonts are safer.
        # We will use a cleaner CSS to ensure layout is fine.
        
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
                p {{ margin-bottom: 10px; }}
                ul {{ margin-bottom: 10px; }}
                li {{ margin-bottom: 5px; }}
                code {{ background-color: #f8f9fa; padding: 2px 4px; border-radius: 3px; font-family: Courier, monospace; }}
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
