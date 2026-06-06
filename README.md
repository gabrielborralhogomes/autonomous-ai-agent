# 🤖 Autonomous AI Agent

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/Claude-Anthropic-orange?style=for-the-badge" />
  <img src="https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=for-the-badge&logo=openai" />
  <img src="https://img.shields.io/badge/Gemini-Google-4285F4?style=for-the-badge&logo=google" />
  <img src="https://img.shields.io/badge/Playwright-Automation-2EAD33?style=for-the-badge&logo=playwright" />
  <img src="https://img.shields.io/badge/APScheduler-Scheduling-FF6B35?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Status-Private%20Project-red?style=for-the-badge" />
</p>

> O código-fonte é proprietário e confidencial. Este repositório serve como referência de portfólio.
> The source code is proprietary. This repository serves as a portfolio reference only.

---

Agente de IA autônomo desenvolvido em Python que recebe um objetivo em linguagem natural e executa tarefas complexas de automação de ponta a ponta — decidindo quais ferramentas usar, em qual ordem, e se recuperando de erros automaticamente até concluir a tarefa.

### Modos de operação

| Modo | Descrição |
|---|---|
| `orchestrate` | Loop reativo — o modelo decide cada passo em tempo real via múltiplas chamadas ao LLM |
| `plan_execute` | O modelo gera um plano completo em 1 chamada e a execução é determinística, sem novos LLM calls |

Após a primeira execução, o agente salva o plano e pode **reexecutar a mesma tarefa com zero custo de API** (Record & Replay).

### Funcionalidades

- **Multi-LLM:** Claude (Anthropic), GPT-4o (OpenAI), Gemini (Google), Llama via Groq e modelos locais via Ollama — troca de provedor via configuração
- **Caixa de ferramentas:** +30 ações cobrindo automação web (Playwright/Selenium), desktop Windows, e-mail (IMAP/SMTP), planilhas (Excel), PDFs, APIs REST, gerenciamento de arquivos e análise visual multimodal via screenshots
- **Agendador de processos:** módulo com APScheduler para execuções únicas, diárias, semanais, mensais, anuais e personalizadas, com controle de feriados e configuração via SQL
- **Recuperação automática:** motor que detecta falhas recuperáveis e as corrige sem interromper a tarefa
- **Controle de custo:** rastreamento de tokens e custo em USD por execução, com suporte a Prompt Caching da Anthropic

---

## 🏗️ Architecture

```mermaid
graph TB
    subgraph Entry["Entry Point"]
        CLI["CLI — main.py\n(plain-language objective)"]
    end

    subgraph Core["Core"]
        OA["Orchestrate Agent\nReactive · N LLM calls"]
        PEA["Plan-Execute Agent\n1 planning call + deterministic exec"]
        RE["Recovery Engine"]
        SCH["Scheduler\nAPScheduler · SQL config"]
    end

    subgraph Providers["LLM Providers"]
        CL["Claude · GPT-4o\nGemini · Groq · Ollama"]
    end

    subgraph Tools["Tool Registry"]
        WEB["Web — Playwright · Selenium"]
        EMAIL["Email — IMAP · SMTP"]
        WIN["Windows Desktop"]
        FILE["File · PDF · Spreadsheet"]
        API["HTTP APIs"]
        VIS["Visual Analysis"]
        DATA["Data · Memory"]
    end

    CLI --> OA
    CLI --> PEA
    CLI --> SCH
    OA --> Providers
    PEA --> Providers
    OA --> Tools
    PEA --> Tools
    OA --> RE
    RE --> Providers
```

---

## 🔄 Flows

### Orchestrate Mode

```mermaid
flowchart TD
    A(["Objective"]) --> B["LLM Call"]
    B --> C{Response?}
    C -->|Tool call| D["Execute Tool"]
    C -->|Text only| E["Inject reminder"]
    C -->|finish| Z(["✅ Done"])
    D --> G{Success?}
    G -->|Yes| H["Update context"] --> B
    G -->|Recoverable| I["Recovery Engine"] --> G
    G -->|Fatal| K(["❌ Failed"])
    E --> B
```

### Plan-Execute Mode

```mermaid
flowchart TD
    A(["Objective"]) --> B["Phase 1 — 1 LLM call\nGenerates full JSON plan"]
    B --> C["Phase 2 — Deterministic execution\n(no LLM)"]
    C --> D{Visual step?}
    D -->|Yes| E["Screenshot → Visual verification\ncheap LLM call"]
    E -->|Pass| F["Next step"]
    E -->|Fail| G["Recovery → re-execute"]
    G --> F
    D -->|No| F
    F --> H{More steps?}
    H -->|Yes| C
    H -->|No| Z(["✅ Done"])
```

### Scheduler

```mermaid
flowchart TD
    A(["SQL — Process config"]) --> B["Agenda\nLoad schedules"]
    B --> C{Schedule type?}
    C -->|Único| D["One-time · DateTrigger"]
    C -->|Diário| E["Daily · CronTrigger"]
    C -->|Semanal| F["Weekly · CronTrigger"]
    C -->|Mensal| G["Monthly · CronTrigger"]
    C -->|Anual| H["Annual · CronTrigger"]
    C -->|Personalizado| I["Custom days · CronTrigger"]
    D & E & F & G & H & I --> J["BackgroundScheduler\nExecute process"]
    J --> K{Holiday check}
    K -->|Feriado + trabFeriado=false| L["Skip"]
    K -->|OK| M(["✅ Process executed"])
```

---

## 🛠️ Technology Stack

| Category | Technologies |
|---|---|
| **Language** | Python 3.10+ · asyncio |
| **LLM Providers** | Claude (Anthropic) · GPT-4o (OpenAI) · Gemini (Google) · Llama/Groq · Ollama |
| **Web Automation** | Playwright · Selenium |
| **Desktop Automation** | pywin32 · ctypes |
| **Email** | imaplib · smtplib |
| **Spreadsheets / Docs** | openpyxl · pdfplumber · pandas |
| **Scheduling** | APScheduler · SQL |
| **HTTP / APIs** | httpx · aiohttp |
| **Architecture** | Tool Registry · Plan-Execute · Record & Replay · Auto-Recovery · Multi-Provider |

---

## 👤 Author

**Gabriel Paulino**
- GitHub: [@gabrielborralhogomes](https://github.com/gabrielborralhogomes)
- LinkedIn: [gabrielborralho](https://www.linkedin.com/in/gabrielborralho)
- Email: gabrielborralho98@gmail.com

---

> *Este projeto é proprietário. Este repositório serve apenas como referência de portfólio.*
> *This project is proprietary. This repository serves as a portfolio reference only.*
