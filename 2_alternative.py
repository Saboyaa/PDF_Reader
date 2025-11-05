import os
import time
import json
import fitz
from dotenv import load_dotenv
from openai import OpenAI

class PDFExtractor:
    def __init__(self, folder_path):
        self.folder_path = folder_path
    
    def extract_all_texts(self):
        all_texts = {}
        for filename in os.listdir(self.folder_path):
            if filename.endswith('.pdf'):
                pdf_path = os.path.join(self.folder_path, filename)
                text = self._extract_text(pdf_path)
                all_texts[filename] = text
        return all_texts
    
    def _extract_text(self, pdf_path):
        text = ''
        with fitz.open(pdf_path) as pdf:
            for page in pdf:
                text += page.get_text()
        return text

class OABExtractor:
    def __init__(self):
        self.client = OpenAI()
    
    def extract_data(self, texto, pdf_filename):
        prompt = self._build_prompt(texto)
        
        response = self.client.responses.create(
            model="gpt-5-mini",  
            input=prompt,
            reasoning={ "effort": "minimal" },
            text={ "format":{"type":"json_object"}},
        )
        
        text_content = response.output_text
        print(response.usage.total_tokens)
        return self._parse_csv(text_content, pdf_filename)
    
    def _build_prompt(self, texto):
        return f"""Extraia do texto e retorne apenas o JSON (use null se vazio).

Texto:
{texto}"""
    
    def _parse_csv(self, csv_content, pdf_filename):
        # Remove espaços extras e quebras de linha
        csv_content = csv_content.strip()
        
        # Se o modelo retornou explicações, pega só a última linha
        if '\n' in csv_content:
            csv_content = csv_content.split('\n')[-1]
        
        # Split por vírgula
        values = [v.strip() for v in csv_content.split(',')]
        
        # Garante que temos 8 valores
        while len(values) < 8:
            values.append('null')
        
        return {
            "label": "carteira_oab",
            "extraction_schema": {
                "nome": values[0] if values[0] != 'null' else None,
                "inscricao": values[1] if values[1] != 'null' else None,
                "seccional": values[2] if values[2] != 'null' else None,
                "subsecao": values[3] if values[3] != 'null' else None,
                "categoria": values[4] if values[4] != 'null' else None,
                "endereco_profissional": values[5] if values[5] != 'null' else None,
                "telefone_profissional": values[6] if values[6] != 'null' else None,
                "situacao": values[7] if values[7] != 'null' else None,
            },
            "pdf_path": pdf_filename
        }

def main():
    load_dotenv()
    inicio = time.time()
    
    # Extrai textos dos PDFs
    pdf_extractor = PDFExtractor('files')
    all_texts = pdf_extractor.extract_all_texts()
    print(all_texts["oab_3.pdf"])


if __name__ == "__main__":
    main()