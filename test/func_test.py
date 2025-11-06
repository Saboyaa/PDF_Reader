import json
import os
import re
import unicodedata

def normalizar_nome_pdf(nome):
    """
    Normaliza o nome do PDF para encontrar o gabarito correspondente.
    Mantém o primeiro número (ex: oab_1_2_0.pdf → oab_1.pdf).
    """
    nome = os.path.basename(nome).lower().strip()
    base, ext = os.path.splitext(nome)

    # Mantém o primeiro grupo (_\d+), remove o restante
    base = re.sub(r"^(.+?_\d+)(?:(_\d+)*)$", r"\1", base)

    return base + ext

def normalizar_texto(valor):
    """Normaliza texto para comparação mais robusta."""
    if valor is None:
        return None

    # Remove acentuação
    valor = unicodedata.normalize("NFKD", valor)
    valor = "".join(c for c in valor if not unicodedata.combining(c))

    # Substitui quebras de linha e múltiplos espaços por um espaço
    valor = re.sub(r"[\n\r,;]+", " ", valor)
    valor = re.sub(r"\s+", " ", valor)

    # Remove espaços no início/fim e deixa minúsculo
    return valor.strip().lower()

def encontrar_gabarito(gabaritos, pdf_path):
    """Tenta encontrar o gabarito correspondente a um PDF."""
    nome_limpo = normalizar_nome_pdf(pdf_path)
    for g in gabaritos:
        if normalizar_nome_pdf(g["pdf_path"]) == nome_limpo:
            return g
    return None

def comparar_campos(schema_ref, schema_pred):
    """Compara dois dicionários campo a campo e calcula a acurácia."""
    total = 0
    acertos = 0
    campos_resultado = {}

    for campo, valor_ref in schema_ref.items():
        total += 1
        valor_pred = schema_pred.get(campo)
        correto = (normalizar_texto(str(valor_ref)) == normalizar_texto(str(valor_pred)))
        campos_resultado[campo] = {
            "esperado": valor_ref,
            "obtido": valor_pred,
            "correto": correto
        }
        if correto:
            acertos += 1

    return {
        "acertos": acertos,
        "total": total,
        "campos": campos_resultado,
        "acuracia": acertos / total if total else 0
    }

def calcular_acuracia(gabaritos, resultados):
    total_campos = 0
    total_acertos = 0
    docs_resultado = []

    for r in resultados:
        gabarito = encontrar_gabarito(gabaritos, r["pdf_path"])
        if not gabarito:
            docs_resultado.append({
                "pdf_path": r["pdf_path"],
                "acuracia": 0,
                "detalhes": "❌ Gabarito não encontrado"
            })
            continue

        comparacao = comparar_campos(gabarito["extraction_schema"], r["extraction_schema"])
        total_campos += comparacao["total"]
        total_acertos += comparacao["acertos"]

        docs_resultado.append({
            "pdf_path": r["pdf_path"],
            "acuracia": round(comparacao["acuracia"] * 100, 2),
            "detalhes": comparacao["campos"]
        })

    acuracia_geral = round((total_acertos / total_campos) * 100, 2) if total_campos else 0
    return acuracia_geral, total_acertos, total_campos, docs_resultado

def main():
    with open("gabarito.json", "r", encoding="utf-8") as f:
        gabaritos = json.load(f)

    with open("../json/result.json", "r", encoding="utf-8") as f:
        resultados = json.load(f)

    acuracia_geral, total_acertos, total_campos, docs_resultado = calcular_acuracia(gabaritos, resultados)

    print(f"\n📊 Acurácia geral: {acuracia_geral}%")
    print(f"✔ {total_acertos} campos corretos / {total_campos} totais")
    print("──────────────────────────────")
    print("📄 Por documento:")
    for doc in docs_resultado:
        print(f" - {doc['pdf_path']}: {doc['acuracia']}%")
    print("──────────────────────────────")

    with open("relatorio_acuracia.json", "w", encoding="utf-8") as f:
        json.dump({
            "acuracia_geral": acuracia_geral,
            "total_acertos": total_acertos,
            "total_campos": total_campos,
            "documentos": docs_resultado
        }, f, ensure_ascii=False, indent=2)

    print("💾 Relatório salvo em relatorio_acuracia.json")

if __name__ == "__main__":
    main()
