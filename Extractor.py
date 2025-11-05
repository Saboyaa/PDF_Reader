import os
import time
import json
import re
import fitz
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI


# -----------------------------
# Extrator de texto dos PDFs
# -----------------------------
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


# -----------------------------
# Extrator de dados com LLM
# -----------------------------
class DataExtractor:
    def __init__(self):
        self.client = AsyncOpenAI()

    async def extract_data(self, schema, texto, pdf_filename):
        prompt = f"""
Extraia e retorne os seguintes dados do texto fornecido no formato JSON.
Campos ausentes devem ser null.
Quanto mais para cima da página estiver a informação, maior a prioridade.

{json.dumps(schema, indent=2, ensure_ascii=False)}

Texto:
{texto}
"""
        start = time.time()
        response = await self.client.responses.create(
            model="gpt-5-mini",
            input=prompt,
            reasoning={"effort": "minimal"},
            text={"format": {"type": "json_object"}},
        )

        print(f"→ {pdf_filename}: {response.usage.total_tokens} tokens | {time.time() - start:.2f}s")

        text_content = response.output_text
        result = self._parse_json(text_content)
        result["pdf_path"] = pdf_filename
        return result

    def _parse_json(self, text_content):
        match = re.search(r"\{.*\}", text_content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {"error": "JSON inválido", "raw": text_content}
        else:
            return {"error": "JSON não encontrado", "raw": text_content}


# -----------------------------
# Funções de produtores/consumidores
# -----------------------------
async def producer_then_consumer(id, queue, dataset_slice, all_texts, extractor, results, lock):
    # Fase 1: Produção
    produced_count = 0

    for item in dataset_slice:
        pdf_name = item["pdf_path"]
        label = item["label"]

        schema = {
            "label": label,
            "extraction_schema": item["extraction_schema"]
        }
        texto = all_texts.get(pdf_name)
        if not texto:
            print(f"[P{id}] [!] Texto não encontrado para {pdf_name}")
            continue

        await queue.put((schema, texto, pdf_name, label))
        produced_count += 1
        print(f"[P{id}] + Adicionado à fila: {pdf_name} ({label})")

    print(f"[P{id}] ✅ Finalizou produção ({produced_count} itens). Agora consumindo...")

    # Fase 2: Vira consumidor
    consumed_count = 0
    while True:
        try:
            task = await asyncio.wait_for(queue.get(), timeout=5.0)
        except asyncio.TimeoutError:
            print(f"[P{id}] 🚪 Nenhum item novo há 5s, encerrando consumidor. "
                  f"Total consumido: {consumed_count}")
            break

        if task is None:
            print(f"[P{id}] 🚪 Recebeu sinal de parada.")
            break

        schema, texto, pdf_name, label = task
        parsed = await extractor.extract_data(schema, texto, pdf_name)
        async with lock:
            results.append(parsed)
        consumed_count += 1
        print(f"[P{id}] (como consumidor) ✓ Processado: {pdf_name} ({label})")
        queue.task_done()

async def consumer(id, queue, extractor, results, lock):
    while True:
        task = await queue.get()
        if task is None:
            print(f"[C{id}] 🚪 Encerrando consumidor.")
            break

        schema, texto, pdf_name, label = task
        parsed = await extractor.extract_data(schema, texto, pdf_name)
        async with lock:
            results.append(parsed)
        print(f"[C{id}] ✓ Processado: {pdf_name} ({label})")
        queue.task_done()


# -----------------------------
# Main
# -----------------------------
async def main():
    load_dotenv()
    inicio = time.time()

    with open("buffed.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)
    print(len(dataset))
    
    pdf_extractor = PDFExtractor("buffed_files")
    all_texts = pdf_extractor.extract_all_texts()
    print(f"Extração de PDFs: {time.time() - inicio:.2f}s")

    extractor = DataExtractor()
    results = []
    lock = asyncio.Lock()
    queue = asyncio.Queue()

    tempo_llm = time.time()

    num_producers = 1
    num_consumers = 4
    chunk_size = max(1, len(dataset) // num_producers)
    slices = [dataset[i:i + chunk_size] for i in range(0, len(dataset), chunk_size)]

    # 5 produtores que viram consumidores
    producer_tasks = [
        asyncio.create_task(producer_then_consumer(i + 1, queue, slices[i], all_texts, extractor, results, lock))
        for i in range(len(slices))
    ]

    # 2 consumidores fixos
    consumer_tasks = [
        asyncio.create_task(consumer(i + 1, queue, extractor, results, lock))
        for i in range(num_consumers)
    ]

    await asyncio.gather(*producer_tasks)

    # Após produtores (que também consumiram) terminarem, encerrar os consumidores fixos
    for _ in range(num_consumers):
        await queue.put(None)

    await asyncio.gather(*consumer_tasks)

    print(f"\nLLM Total: {time.time() - tempo_llm:.2f}s")

    print("\n=== RESULTADOS ===")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"Total resultados obtidos: {len(results)}")

    print(f"\nTempo total: {time.time() - inicio:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
