import os
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

    def save_pdf(self, content, prefix="report"):
        path = self._get_paths(prefix, "pdf")
        
        # Convert MD to HTML first
        html_content = markdown.markdown(content)
        
        # Add minimal styling for PDF
        styled_html = f"""
        <html>
        <style>
            body {{ font-family: Helvetica, sans-serif; font-size: 12pt; }}
            h1 {{ color: #333; font-size: 18pt; border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
            h2 {{ color: #666; font-size: 14pt; margin-top: 20px; }}
            li {{ margin-bottom: 4px; }}
        </style>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        with open(path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(styled_html, dest=pdf_file)
            
        if pisa_status.err:
            raise Exception("PDF generation failed")
            
        return path
