# Agent Runtime

Framework de automação baseado em LLM com suporte a múltiplos provedores, dois modos de operação, prompt caching da Anthropic e verificação visual por step.

---

## Configuração (`agent_runtime/shared/config.py`)

### Selecionar o provedor

```python
PROVIDER = "claude-haiku"
# Opções: "claude-sonnet" | "claude-haiku" | "groq" | "openai" | "gemini" | "ollama" | "herbert"
```

### Selecionar o modo do agente

```python
AGENT_MODE = "plan_execute"
# Opções: "plan_execute" | "orchestrate"
```

Também pode ser definido via variável de ambiente:
```bash
AGENT_MODE=orchestrate python main.py
```

### Modelos disponíveis

| Provider | Modelo |
|---|---|
| `claude-sonnet` | claude-sonnet-4-20250514 |
| `claude-haiku` | claude-haiku-4-5-20251001 |
| `groq` | llama-3.3-70b-versatile |
| `openai` | gpt-4o-mini |
| `gemini` | gemini-2.0-flash |
| `ollama` | glm-5.1:cloud |
| `herbert` | herbert-0.2:latest (Qwen fine-tuned local) |

---

## Modos de operação

### Modo `orchestrate` — `ClaudeAutomationAgent`

O LLM atua como orquestrador a cada passo:

```
Objetivo + Histórico → LLM → Ferramentas → LLM → Ferramentas → ... → finish
```

- Cada iteração envia o objetivo + histórico (janela deslizante de `CONTEXT_KEEP_LAST_STEPS` steps)
- O LLM decide qual ferramenta chamar a cada passo
- Mais flexível para tarefas exploratórias, mas mais caro em tokens

**Fluxo do loop principal (4 casos — if/elif/else):**

1. **Sem ferramentas + tem texto** → reinjeta lembrete para chamar `finish` (nudge uma vez)
2. **Sem ferramentas + sem texto** → aborta com erro
3. **Ferramenta `finish`** → salva resultado e encerra
4. **Ferramentas normais** → executa e adiciona ao histórico

### Modo `plan_execute` — `PlanExecuteAgent`

1 chamada LLM para planejamento → execução determinística → verificação visual por step:

```
Objetivo → LLM (plano JSON) → Step 1 → Screenshot → LLM mínimo (verificar?) → Step 2 → ...
```

**Vantagens em custo:**
- Verificação visual: ~$0.0000004 por step (imagem + ~50 tokens)
- Planejamento: 1 chamada LLM por objetivo novo
- Recuperação (LLM ativo): só quando a verificação falha

**Estrutura de um step normal:**

```json
{
  "id": 1,
  "description": "Preencher campo",
  "tool": "web_playwright",
  "action": "fill",
  "args": { "target": {"selector": "#username"}, "value": "student" },
  "save_as": null,
  "verify": "Campo preenchido",
  "screenshot": true,
  "on_fail": "abort"
}
```

**`on_fail`:** `"abort"` | `"recover"` | `"skip"`

**Variáveis dinâmicas:** use `$nome` ou `$nome.campo` em `args` para referenciar valores salvos com `save_as`.

### Condicionais no plano (`if/elif/else`)

Branch puro (sem tool call):
```json
{
  "id": 5,
  "description": "Escolher fluxo",
  "condition": {"left": "$status", "operator": "==", "right": "admin"},
  "if_true": [ ... steps ... ],
  "if_false": [ ... steps ou outro branch ... ]
}
```

Guard em step comum (pular se condição falsa):
```json
{ "id": 6, "tool": "web_playwright", "action": "close", "args": {},
  "condition": {"left": "$logado", "operator": "falsy"} }
```

**Operadores:** `==` `!=` `>` `<` `>=` `<=` `in` `not in` `contains` `startswith` `endswith` `empty` `not empty` `exists` `truthy` `falsy`

### Loops no plano (`for` / `for_each` / `while`)

**`for_each`** — itera sobre uma lista:
```json
{
  "id": 10, "type": "for_each", "description": "Processar cada linha",
  "items": "$rows", "item_var": "row", "index_var": "i",
  "collect_from": "resultado_row", "collect_as": "todos_resultados",
  "max_iterations": 10000, "on_fail": "abort",
  "body": [
    { "id": "10.1", "tool": "web_playwright", "action": "fill",
      "args": {"target": {"selector": "#nome"}, "value": "$row.nome"}, "on_fail": "skip" }
  ]
}
```

**`for`** — range numérico:
```json
{ "id": 11, "type": "for", "description": "Repetir 5 vezes",
  "range": {"start": 1, "end": 6, "step": 1}, "index_var": "i",
  "max_iterations": 1000, "body": [ ... ] }
```

**`while`** — repete enquanto condição for verdadeira:
```json
{ "id": 12, "type": "while", "description": "Tentar até encontrar",
  "condition": {"left": "$encontrado", "operator": "falsy"},
  "max_iterations": 20, "on_fail": "abort", "body": [ ... ] }
```

**`break` / `continue`** — controle de fluxo dentro do body:
```json
{ "id": "10.2", "type": "break", "condition": {"left": "$erro", "operator": "truthy"} }
{ "id": "10.3", "type": "continue", "condition": {"left": "$row.nome", "operator": "empty"} }
```

**Caso de uso — iterar planilha:**
1. `document.dataframe_records` → `save_as: "rows"`
2. `for_each items="$rows" item_var="row"` com steps no body usando `$row.campo`

**Arquivos de plano:** `plans/pe_{hash_objetivo}.json` (prefixo `pe_` diferencia de planos do modo orchestrate)

**Prompts específicos (`agent_runtime/schemas/plan_prompt.py`):**
- `PLAN_SYSTEM_PROMPT`: instrui o LLM a gerar o plano JSON completo (inclui docs de condicionais e loops)
- `VERIFY_SYSTEM_PROMPT`: prompt mínimo para verificação visual por step
- `RECOVER_SYSTEM_PROMPT`: mini-orquestrador ativado quando verificação falha

---

## Otimizações de token

### 1. Prompt Caching (Anthropic)

Ativo automaticamente para `claude-sonnet` e `claude-haiku`.

- `cache_control: {"type": "ephemeral"}` aplicado no system prompt e na última tool
- Requer header `anthropic-beta: prompt-caching-2024-07-31` (adicionado em `providers/claude.py`)
- Preços do cache (Haiku):

| Tipo | Preço/M tokens |
|---|---|
| Normal (input) | $0.80 |
| Cache write | $1.00 |
| Cache read | $0.08 (**10× mais barato**) |

### 2. Janela deslizante de contexto

Configurável via `CONTEXT_KEEP_LAST_STEPS` (padrão: 8).

- Mantém os últimos 8 steps completos no histórico
- Steps mais antigos são comprimidos em resumos de 1 linha
- Os resumos são injetados no texto do objetivo

### 3. Truncação de resultados de ferramentas

Resultados grandes são truncados antes de entrar no histórico (`max_chars=6000`):

| Tipo de dado | Tratamento |
|---|---|
| JSON ≤ 6000 chars | Sem alteração |
| DataFrame com chave `rows` | Mantém 5 linhas de amostra |
| Dict genérico | Remove valores > 500 chars |
| Lista | Mantém primeiros 5 itens |
| String | Trunca em 2000 chars |

### 4. Remoção de `memory_preview`

O bloco `memory_preview` que antes era injetado em todas as respostas de tool foi removido. Economiza tokens em toda execução longa sem perda relevante de contexto.

---

## Custo em USD

Ao final de cada execução, o agente exibe um resumo de tokens e custo:

```
=== Token Usage Summary ===
  Steps executados:       12
  Input tokens:        45,230
  Output tokens:        3,890
  Cache write tokens:  38,000
  Cache read tokens:   42,100
  Custo estimado:       $0.0581 USD
  Economia de cache:    $0.0337 USD
===========================
```

Para o modo `plan_execute`, o resumo separa por tipo de chamada:
- `planning_calls`: planejamento inicial
- `verification_calls`: verificações visuais por step
- `recovery_calls`: chamadas de recuperação quando step falha

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `AGENT_MODE` | `plan_execute` | Modo do agente |
| `CONTEXT_KEEP_LAST_STEPS` | `8` | Steps mantidos completos no histórico |
| `PLANS_DIR` | `plans` | Diretório onde planos JSON são salvos |
| `MEMORY_DIR` | `memory` | Diretório de memória persistente |
| `OLLAMA_TIMEOUT_SECONDS` | `90` | Timeout para modelos Ollama/Herbert |
| `OLLAMA_LOCAL_MAX_TOKENS` | `768` | Max tokens para modelos locais |
| `ANTHROPIC_API_KEY` | — | Chave Anthropic (alternativa ao config.py) |
| `GROQ_API_KEY` | — | Chave Groq |
| `OPENAI_API_KEY` | — | Chave OpenAI |
| `GEMINI_API_KEY` | — | Chave Gemini |

---

## Arquitetura em alto nível

### Entry point (`main.py`)

1. Lê `PROVIDER`, `AGENT_MODE` da config
2. Cria o cliente do provedor com `create_provider`
3. Constrói o `ToolRegistry`
4. Instancia `PlanExecuteAgent` ou `ClaudeAutomationAgent` conforme `AGENT_MODE`
5. Carrega o objetivo de `objective.txt` ou do argumento de linha de comando
6. Chama `await agent.run(objective)`
7. Imprime o JSON final do resultado

### Core do agente (`agent_runtime/core/`)

- `agent.py`: loop principal do modo orchestrate, gravação de planos, sliding window, resumo de tokens
- `plan_execute_agent.py`: modo plan_execute com verificação visual e recuperação por step
- `context.py`: contexto em memória da sessão (AgentContext)
- `executor.py`: roteamento central de todas as tool calls
- `recovery.py`: estratégias automáticas de recuperação

### Provedores (`agent_runtime/shared/providers/`)

Todos implementam `BaseProvider` com `create_message()` e normalizam para o formato interno do runtime.

| Provider | Arquivo | Nota |
|---|---|---|
| `claude-sonnet`, `claude-haiku` | `claude.py` | REST direto, prompt caching ativo |
| `groq`, `openai` | `openai_compat.py` | OpenAI-compat, multimodal base64 |
| `gemini` | `gemini.py` | generateContent, converte tool calling |
| `ollama`, `herbert` | `ollama_sdk.py` | AsyncClient, inicia `ollama serve` se necessário |

---

## Record vs Replay de planos

### Modo orchestrate

- **Novo objetivo** → grava passos bem-sucedidos em `plans/{hash}.json`
- **Plano completo existente** → replay determinístico sem chamar o LLM
- **Plano incompleto** → apaga e recomeça do zero

Cada step salvo contém: `tool`, `action`, `args`.

### Modo plan_execute

- **Novo objetivo** → gera plano via LLM e salva em `plans/pe_{hash}.json`
- **Plano existente** → executa diretamente sem nova chamada de planejamento
- Steps contêm também: `verify`, `screenshot`, `on_fail`, `save_as`

---

## Catálogo de tools

| Tool | Namespace | Ações principais |
|---|---|---|
| `WebPlaywrightTool` | `web_playwright` | navigate, click, fill, read_text, screenshot, press_key |
| `WebSeleniumTool` | `web_selenium` | mesmas ações via Selenium |
| `WindowsTool` | `windows` | connect, click, fill, inspect, press_keys |
| `VisualTool` | `visual` | screenshot, click_target, fill_target, click_coords |
| `SmartActionTool` | `smart_action` | click, fill, read (com fallback visual) |
| `FileTool` | `file` | read, write_text, list, copy, move, delete, zip, unzip |
| `DocumentTool` | `document` | load_dataframe, extract_text, extract_pdf_table, filter, save |
| `DataTool` | `data` | match_tables, fuzzy_search, validate_schema, join_tables |
| `SpreadsheetTool` | `spreadsheet` | build_workbook (multi-aba, formatação automática) |
| `MemoryTool` | `memory` | set, get, approve, reject, list (persistência JSON por namespace) |
| `ApiTool` | `api` | open, authenticate, request |
| `EmailTool` | `email` | open, send |
| `UserInteractionTool` | `user_interaction` | ask_text, ask_choice, confirm |
| `finish` | — | encerra execução e salva plano completo |

---

## Recovery automático

O `RecoveryEngine` cobre:

- **Falha web**: tenta Escape, inspeciona elementos, clica em "fechar/close/ok"
- **Clique web falhou**: screenshot + análise visual para encontrar coordenadas
- **Falha Windows**: fecha dialogs e repete
- **Arquivo não encontrado**: busca arquivos semelhantes e atualiza path em memória
- **CAPTCHA/anti-bot**: bloqueado explicitamente, não tenta contornar

---

## Riscos e pendências técnicas

1. **Segredos hardcoded em `config.py`** — chaves de API estão no código-fonte
2. **Bug em `data.match_tables`** — variável `with_candidates` usada sem ser definida no fluxo LLM
3. **Herbert sem preço mapeado** — custo USD pode ficar impreciso para esse provedor
4. **`pyautogui.FAILSAFE = False`** — desliga proteção padrão de automação visual
5. **Sem `requirements.txt`** — dependências precisam ser instaladas manualmente

---

## Como executar

```bash
# 1. Instalar dependências
pip install requests pandas pdfplumber PyPDF2 rapidfuzz openpyxl playwright selenium webdriver-manager pyautogui pywinauto ollama
playwright install chromium

# 2. Configurar em agent_runtime/shared/config.py:
#    PROVIDER = "claude-haiku"   (ou outro)
#    AGENT_MODE = "plan_execute" (ou "orchestrate")

# 3. Definir o objetivo em objective.txt ou passar um arquivo/objetivo pela linha de comando

# 4. Rodar
python main.py
# ou
python main.py caminho\para\meu_objetivo.txt
```

---

## Sobre o Modelfile

Define o modelo local Herbert para o ecossistema Ollama: parte de `herbert-0.1:latest`, fixa `temperature`, `num_ctx`, `num_predict` e inclui exemplos de tool calling. Não é carregado pelo runtime Python — serve apenas para construir/manter o modelo no Ollama.
