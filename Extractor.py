import os
import time
import json
import re
import fitz
import asyncio
import sys
from dotenv import load_dotenv
from openai import AsyncOpenAI


# -----------------------------
# Extrator de texto dos PDFs
# -----------------------------
    
def _extract_text(pdf_path):
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
Extraia e retorne os dados do Texto que foi extraido de um PDF substituindo eles nos valores do schema conforme o JSON.
Campos ausentes devem ser null.
{json.dumps(schema, indent=2, ensure_ascii=False)}
devolta exatamente nessa estrutura

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

        # print(f"→ {pdf_filename}: {response.usage.total_tokens} tokens | {time.time() - start:.2f}s")

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
# Atualização do result.json em tempo real
# -----------------------------
async def update_result_json(original_dataset, results, lock, output_path="json/result.json"):
    """Atualiza result.json mantendo a ordem original do dataset.json."""
    async with lock:
        result_map = {r.get("pdf_path"): r for r in results}
        ordered_results = []

        for item in original_dataset:
            pdf_path = item["pdf_path"]
            if pdf_path in result_map:
                merged = {**item, **result_map[pdf_path]}
                ordered_results.append(merged)

        tmp_path = f"{output_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(ordered_results, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, output_path)


# -----------------------------
# Funções de produtores/consumidores
# -----------------------------
async def producer_then_consumer(id, queue, dataset_slice, all_texts, extractor, results, lock, original_dataset):
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
        # print(f"[P{id}] + Adicionado à fila: {pdf_name} ({label})")

    # print(f"[P{id}] ✅ Finalizou produção ({produced_count} itens). Agora consumindo...")

    consumed_count = 0
    while True:
        try:
            task = await asyncio.wait_for(queue.get(), timeout=5.0)
        except asyncio.TimeoutError:
            # print(f"[P{id}] 🚪 Nenhum item novo há 5s, encerrando consumidor. Total consumido: {consumed_count}")
            break

        if task is None:
            # print(f"[P{id}] 🚪 Recebeu sinal de parada.")
            break

        schema, texto, pdf_name, label = task
        parsed = await extractor.extract_data(schema, texto, pdf_name)
        async with lock:
            results.append(parsed)
        consumed_count += 1
        # print(f"[P{id}] (como consumidor) ✓ Processado: {pdf_name} ({label})")
        queue.task_done()

        # 🔄 Atualiza o result.json após cada item
        await update_result_json(original_dataset, results, lock)


async def consumer(id, queue, extractor, results, lock, original_dataset):
    while True:
        if len(results)>=len(original_dataset):
            # print(f"[C{id}] 🚪 Encerrando consumidor.")
            break
        task = await queue.get()
        if task is None:
            # print(f"[C{id}] 🚪 Encerrando consumidor.")
            break

        schema, texto, pdf_name, label = task
        parsed = await extractor.extract_data(schema, texto, pdf_name)
        async with lock:
            results.append(parsed)
        # print(f"[C{id}] ✓ Processado: {pdf_name} ({label})")
        queue.task_done()

        # 🔄 Atualiza o result.json após cada item
        await update_result_json(original_dataset, results, lock)


# -----------------------------
# Main
# -----------------------------
async def main():
    load_dotenv()
    inicio = time.time()
    all_texts = {}
    pdf_args = sys.argv[1:]
    print(f"→ Argumentos recebidos: {pdf_args}")

# Se o último argumento for um JSON, trata como o buffed_path
    if pdf_args and pdf_args[-1].lower().endswith(".json"):
        buffed_path = pdf_args[-1]
        pdf_args = pdf_args[:-1]  # remove o último argumento da lista de PDFs
    else:
        buffed_path = "json/dataset.json"

    print(f"→ buffed.json usado: {buffed_path}")

    with open(buffed_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    original_dataset = dataset.copy()
    print(f"Total no dataset: {len(dataset)}")

    valid_pdfs = [p for p in pdf_args if p.lower().endswith(".pdf")]
    print(f"→ PDFs válidos detectados: {valid_pdfs}")

    for pdf_path in valid_pdfs:
        if os.path.exists(pdf_path):
            pdf_name = os.path.basename(pdf_path)
            try:
                all_texts[pdf_name] = _extract_text(pdf_path)
            except Exception as e:
                print(f"[!] Erro ao ler {pdf_path}: {e}")
        else:
            print(f"[!] Arquivo não encontrado: {pdf_path}")

    if not all_texts:
        print("[!] Nenhum PDF válido encontrado para processar.")
        return

    # print(f"Extração de PDFs: {time.time() - inicio:.2f}s")

    dataset = [d for d in dataset if d["pdf_path"] in all_texts]
    # print(f"Dataset filtrado: {len(dataset)} entradas correspondentes.")

    extractor = DataExtractor()
    results = []
    lock = asyncio.Lock()
    queue = asyncio.Queue()

    tempo_llm = time.time()

    num_producers = 1
    num_consumers = 200
    chunk_size = max(1, len(dataset) // num_producers)
    slices = [dataset[i:i + chunk_size] for i in range(0, len(dataset), chunk_size)]

    producer_tasks = [
        asyncio.create_task(producer_then_consumer(i + 1, queue, slices[i], all_texts, extractor, results, lock, original_dataset))
        for i in range(len(slices))
    ]

    consumer_tasks = [
        asyncio.create_task(consumer(i + 1, queue, extractor, results, lock, original_dataset))
        for i in range(num_consumers)
    ]

    await asyncio.gather(*producer_tasks)

    for _ in range(num_consumers):
        await queue.put(None)

    await asyncio.gather(*consumer_tasks)

    #print(f"\nLLM Total: {time.time() - tempo_llm:.2f}s")
    #print(f"Total resultados obtidos: {len(results)}")
    #print(f"\nTempo total: {time.time() - inicio:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
