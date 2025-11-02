import os
import time
from dotenv import load_dotenv
import json
import fitz  # PyMuPDF
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI

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
print(texto)

# Preparar LLM e prompt
llm = ChatOpenAI(model='gpt-5-mini', temperature=0)  # Corrigido: gpt-4o-mini

template = """
Você deve **extrair informações estruturadas** do texto fornecido e retornar **apenas um JSON válido** no formato abaixo. 
Se algum dado não estiver presente no texto, preencher com null.

Formato do JSON esperado:
{{
  "label": "carteira_oab",
  "extraction_schema": {{
    "nome": "Nome do profissional, normalmente no canto superior esquerdo da imagem",
    "inscricao": "Número de inscrição do profissional",
    "seccional": "Seccional do profissional (UF)",
    "subsecao": "Subseção à qual o profissional faz parte",
    "categoria": "Categoria: ADVOGADO, ADVOGADA, SUPLEMENTAR, ESTAGIARIO ou ESTAGIARIA",
    "endereco_profissional": "Endereço completo do profissional",
    "telefone_profissional": "Telefone do profissional",
    "situacao": "Situação do profissional, normalmente no canto inferior direito"
  }},
  "pdf_path": "oab_1.pdf"
}}

**Apenas retornar o JSON**, sem explicações, comentários ou texto adicional.

Texto do PDF a ser analisado:
{texto}
"""

prompt = PromptTemplate(input_variables=['texto'], template=template)
json_parser = JsonOutputParser()

# Criar chain e executar
chain = prompt | llm | json_parser
parsed = chain.invoke({"texto": texto})

print(json.dumps(parsed, indent=2, ensure_ascii=False))

fim = time.time()
print(f"O código levou {fim - inicio:.6f} segundos para executar.")