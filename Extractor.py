import os
import time
from dotenv import load_dotenv
import json
import re
import fitz  # PyMuPDF

from openai import OpenAI

load_dotenv()
folder_path = 'files'
all_texts = {}
inicio = time.time()

# Extrair texto dos PDFs
for filename in os.listdir(folder_path):
    if filename.endswith('.pdf'):
        pdf_path = os.path.join(folder_path, filename)
        text = ''
        with fitz.open(pdf_path) as pdf:
            for page in pdf:
                text += page.get_text()
        all_texts[filename] = text

texto = all_texts["oab_1.pdf"]
print(f"Extração: {time.time() - inicio:.2f}s")

# Chamada direta e síncrona
client = OpenAI()
prompt_text = f"""
Extraia e retorne os seguintes dados do texto fornecido no seguinte formato JSON (caso não tenha algum dado completar com null):
{{
  "label": "carteira_oab",
  "extraction_schema": {{
    "nome": "Nome do profissional, normalmente no canto superior esquerdo da imagem",
    "inscricao": "Número de inscrição do profissional",
    "seccional": "Seccional do profissional",
    "subsecao": "Subseção à qual o profissional faz parte",
    "categoria": "Categoria, pode ser ADVOGADO, ADVOGADA, SUPLEMENTAR, ESTAGIARIO, ESTAGIARIA",
    "endereco_profissional": "Endereço do profissional",
    "telefone_profissional": "Telefone do profissional",
    "situacao": "Situação do profissional, normalmente no canto inferior direito."
  }},
  "pdf_path": "oab_1.pdf"
}}
Texto do PDF a ser analisado:
{texto}
"""

tempo_llm = time.time()
response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[{"role": "user", "content": prompt_text}],
    temperature=1,                 
    max_completion_tokens=1000     
)
text_content = response.choices[0].message.content
match = re.search(r"\{.*\}", text_content, re.DOTALL)
if match:
    parsed = json.loads(match.group(0))
else:
    raise ValueError("JSON não encontrado na resposta do modelo")
print(f"LLM: {time.time() - tempo_llm:.2f}s")
print(json.dumps(parsed, indent=2, ensure_ascii=False))
print(f"\nTotal: {time.time() - inicio:.2f}s")
