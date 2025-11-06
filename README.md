# 🧠 PDF Data Extractor com GPT-5-mini

Um sistema assíncrono e escalável para extração estruturada de dados a partir de PDFs, utilizando *producers* e *consumers* paralelos, e integração com o modelo **GPT-5-mini**.  
O pipeline é monitorado em tempo real por uma interface gráfica reativa, que exibe progresso, logs e métricas de acurácia.

---

## ⚙️ Visão Geral

O projeto é composto por **três camadas principais**:

1. **🖥️ Interface Gráfica (UI)** – onde o usuário inicia o processo, acompanha o progresso e visualiza os resultados.
2. **⚙️ Núcleo de Processamento (CORE)** – orquestra produtores e consumidores que interagem com o modelo de IA.
3. **🧠 GPT-5-mini** – responsável por interpretar o texto extraído dos PDFs e retornar o JSON padronizado com os campos definidos.

---

## 🧩 Arquitetura do Sistema

```mermaid
flowchart TD

subgraph UI["🖥️ Interface Gráfica"]
    A1["Usuário inicia processamento"]
    A2["Chama função principal (Extractor)"]
    A3["Monitora o arquivo de resultados (gabarito.json)"]
    A4["Atualiza visual em tempo real com progresso"]
end

subgraph CORE["⚙️ Núcleo de Processamento"]
    subgraph P["Produtores"]
        P1["Ler arquivos PDF"]
        P3["Criar prompts estruturados para GPT-5-mini"]
        P4["Enviar prompts para fila de requisições"]
    end

    subgraph C["Consumidores"]
        C1["Ler respostas do GPT-5-mini"]
        C2["Processar e validar resposta"]
        C3["Salvar resultados ordenadamente em JSON final"]
    end
end

subgraph MODEL["🧠 GPT-5-mini"]
    M1["Recebe prompt"]
    M2["Retorna JSON extraído"]
end

A1 --> A2
A2 --> P1
P1 --> P3
P3 --> P4
P4 --> M1
M1 --> M2
M2 --> C1
C1 --> C2
C2 --> C3
C3 -->|Ao consumir todos| A3
A3 --> A4

%% Ciclo interno de processamento
P --> |Ao acabar de produzir vira consumidor|C
C --> C3

%% Loop dos trabalhadores
P4 --> P1
C3 --> C1

classDef producer fill:#ffb347,stroke:#b36b00,color:#000;
classDef consumer fill:#77dd77,stroke:#2e8b57,color:#000;
classDef model fill:#89cff0,stroke:#0077b6,color:#000;
classDef ui fill:#f8d7da,stroke:#b22222,color:#000;

class P,P1,P2,P3,P4 producer;
class C,C1,C2,C3 consumer;
class M1,M2 model;
class UI,A1,A2,A3,A4 ui;

🔁 Fluxo de Execução

    O usuário inicia o processo na interface e seleciona os PDFs.

    A UI chama a função Extractor, que inicializa N produtores e M consumidores.

    Cada produtor:

        Lê um arquivo PDF.

        Gera o prompt no formato esperado pelo modelo.

        Envia o prompt para uma fila assíncrona.

    O modelo GPT-5-mini processa os prompts e retorna o JSON com os campos extraídos.

    Os consumidores:

        Leem as respostas do modelo.

        Validam e limpam os dados.

        Salvam os resultados em um arquivo final (respostas.json).

        Repetem o ciclo enquanto houver itens na fila.

    A UI monitora continuamente o arquivo gabarito.json e atualiza o progresso em tempo real.

🧰 Tecnologias Utilizadas
Componente	Função
Python 3.11+	Base da aplicação
asyncio / threading	Gerenciamento paralelo de produtores e consumidores
GPT-5-mini API	Extração inteligente de dados dos textos
Tkinter / PyQt / Streamlit (dependendo da versão da UI)	Interface gráfica
JSON Schema	Validação dos resultados extraídos
watchdog (opcional)	Monitoramento em tempo real de alterações no JSON
📊 Métricas de Acurácia

O sistema conta com uma função de avaliação automática que:

    Compara o resultado gerado (respostas.json) com o gabarito.json;

    Ignora diferenças de formatação como \n e espaços;

    Gera um relatório com acurácia geral, por campo e por documento.

🚀 Execução
1. Instalação das dependências

pip install -r requirements.txt

2. Execução normal (com UI)

python main.py

3. Execução em modo headless (sem UI)

python extractor.py --no-ui

4. Resultado

    Arquivo de saída: respostas.json

    Relatório de acurácia: relatorio_acuracia.json ou no painel da UI

💡 Características Avançadas

    🚀 Interface gráfica com Resposta atualizada para o cliente ter noção do que está acontecendo

    ✅ Produtores se transformam automaticamente em consumidores quando terminam suas tarefas.

    🔄 Loops contínuos até o esvaziamento completo das filas.

    ⚡ Processamento paralelo otimizado.

    🧩 Modular e expansível — fácil adicionar novos tipos de documento.

    📡 Comunicação assíncrona entre componentes.

🧑‍💻 Estrutura de Pastas

📁 projeto/
├── 🖥️ ui/
│   ├── main_ui.py
│   └── components/
├── ⚙️ core/
│   ├── extractor.py
│   ├── producers.py
│   ├── consumers.py
│   └── evaluator.py
├── 🧠 model/
│   └── gpt_client.py
├── 📄 data/
│   ├── pdfs/
│   ├── gabarito.json
│   └── respostas.json
└── README.md

🧑‍🎓 Autor

Desenvolvido por Gabriel Saboya
