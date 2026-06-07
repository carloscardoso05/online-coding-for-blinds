# Égua Assist — Documentação Completa

> IDE web assistida por voz para ensino de lógica de programação a estudantes com deficiência visual, usando a linguagem [Égua](https://egua.dev/).

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Arquitetura do Sistema](#2-arquitetura-do-sistema)
3. [Pré-requisitos e Instalação](#3-pré-requisitos-e-instalação)
4. [Configuração do Ambiente](#4-configuração-do-ambiente)
5. [Como Iniciar o Projeto](#5-como-iniciar-o-projeto)
6. [Guia de Uso](#6-guia-de-uso)
7. [Assistentes de Voz (Construtores de Blocos)](#7-assistentes-de-voz-construtores-de-blocos)
8. [Atalhos de Teclado](#8-atalhos-de-teclado)
9. [Referência de Servidores e Portas](#9-referência-de-servidores-e-portas)
10. [Arquivos e Estrutura do Projeto](#10-arquivos-e-estrutura-do-projeto)
11. [Sistema RAG (Retrieval-Augmented Generation)](#11-sistema-rag-retrieval-augmented-generation)
12. [Modelos de IA Suportados](#12-modelos-de-ia-suportados)
13. [Sintaxe da Linguagem Égua](#13-sintaxe-da-linguagem-égua)
14. [Variáveis de Ambiente](#14-variáveis-de-ambiente)
15. [Fluxos de Dados](#15-fluxos-de-dados)
16. [Configuração via Interface](#16-configuração-via-interface)

---

## 1. Visão Geral

O **Égua Assist** é uma extensão para a IDE Égua que torna o aprendizado de programação acessível a estudantes com deficiência visual. O sistema substitui a digitação por **comandos de voz** e fornece **feedback auditivo** em cada etapa.

### Como funciona em resumo

```
Usuário fala → Transcrição por IA → Assistente faz perguntas por voz
     → Código Égua gerado → Interpretador executa → Explicação pedagógica falada
```

### Recursos principais

- **Construção de código por voz** em diálogos guiados passo a passo
- **Execução de código** Égua diretamente no navegador
- **Explicação pedagógica** de erros e sucessos por síntese de voz
- **5 modelos de IA** intercambiáveis (Gemini, GPT, Phi-2, Llama, Qwen2)
- **3 modos de transcrição**: Whisper local, Whisper API, Web Speech API
- **Acessibilidade completa**: aria-labels, navegação por teclado, leitura de caracteres digitados

---

## 2. Arquitetura do Sistema

O sistema é composto por três camadas:

```
┌─────────────────────────────────────────────────────┐
│                   NAVEGADOR (Frontend)               │
│                                                     │
│  ┌─────────┐  ┌───────────┐  ┌────────────────┐   │
│  │ Editor  │  │ Assistente│  │ Síntese de Voz │   │
│  │ Égua    │  │ de Código │  │ (Web Speech)   │   │
│  │(CodeFlask│  │(constructor│  │ (assist.js)    │   │
│  │)        │  │.js)       │  │                │   │
│  └────┬────┘  └─────┬─────┘  └────────────────┘   │
│       │             │                              │
└───────┼─────────────┼──────────────────────────────┘
        │             │ HTTP/REST (localhost)
┌───────┼─────────────┼──────────────────────────────┐
│       │    CAMADA DE SERVIÇOS (Python/PHP)          │
│       │             │                              │
│  ┌────▼──────┐ ┌────▼──────┐ ┌────────────────┐   │
│  │ Explicador│ │ Construtor│ │   Transcritor  │   │
│  │ (5000-    │ │ (7000-    │ │ (3000/PHP)     │   │
│  │  5400)    │ │  7400)    │ │                │   │
│  └───────────┘ └───────────┘ └────────────────┘   │
│                                                     │
│  ┌────────────────────────────────────────────┐    │
│  │          Gerador de Código (4000-4500)      │    │
│  └────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────┐    │
│  │       Conversor de Números (5050)           │    │
│  └────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
        │
┌───────▼───────────────────────────────────────────┐
│                  APIs EXTERNAS                    │
│         Google Gemini API / OpenAI API            │
└───────────────────────────────────────────────────┘
```

### Componentes do Frontend

| Arquivo | Responsabilidade |
|---|---|
| `index.html` | Interface principal, toolbar, modais, editor |
| `js/index.js` | Lógica do editor, demos, leitura de caracteres digitados |
| `js/assist.js` | Síntese de voz, atalhos de teclado, navegação acessível |
| `js/config.js` | Modal de configurações, localStorage dos modelos |
| `js/constructor.js` | Assistentes de construção de código por voz |
| `js/translate-models.js` | Roteamento de modelos, transcrição, envio de prompts |
| `js/explain-code.js` | Execução do código e envio para análise pedagógica |
| `js/demos.js` | Exemplos de código Égua pré-definidos |

### Componentes do Backend

| Diretório | Servidores | Função |
|---|---|---|
| `servers/transcription/` | `whisper-local.py` (3000) | Transcrição de áudio via Whisper |
| `servers/code_generation/` | 5 servidores (4000–4500) | Prompt de voz → código Égua |
| `servers/code_explainer/` | 5 servidores (5000–5400) | Análise pedagógica do código |
| `servers/block_constructor/` | 5 servidores (7000–7400) | JSON estruturado → código Égua |
| `servers/translate_number.py` | (5050) | Número por extenso → numeral |

---

## 3. Pré-requisitos e Instalação

### Requisitos de sistema

- **Python 3.9+** (recomendado 3.12)
- **PHP 8+** com suporte a `php -S`
- **Node.js 18+** com npm (apenas para ESLint, opcional)
- **uv** (gerenciador de pacotes Python) — recomendado
- **Navegador moderno** com suporte a Web Speech API (Chrome/Edge recomendado)

### 1. Clonar e configurar ambiente Python

```bash
# Clonar o repositório
git clone <URL_DO_REPOSITORIO>
cd online-coding-for-blinds

# Instalar dependências core com uv (recomendado)
uv sync

# OU com pip tradicional
pip install flask flask-cors google-generativeai openai python-dotenv \
            deep-translator fastapi "uvicorn[standard]" numpy
```

Para usar modelos locais (Llama, Phi-2, Qwen2, Whisper local):

```bash
# Dependências pesadas — instalar somente se for usar modelos locais
uv sync --extra local-models
```

### 2. Instalar dependências PHP

```bash
composer install
```

### 3. Configurar variáveis de ambiente

Crie o arquivo `.env` na raiz do projeto (veja seção [Variáveis de Ambiente](#14-variáveis-de-ambiente)):

```bash
cp .env.example .env
# Edite o arquivo com suas chaves de API
```

---

## 4. Configuração do Ambiente

### Arquivo `.env` (obrigatório)

```bash
# Google Gemini API — necessário para os servidores Gemini
GOOGLE_API_KEY=sua_chave_aqui

# OpenAI API — necessário para Whisper API e servidores GPT
OPENAI_API_KEY=sk-sua_chave_aqui

# Endpoint da API Whisper (não altere sem motivo)
OPENAI_CURL=https://api.openai.com/v1/audio/transcriptions
```

> **Modelos locais (Llama, Phi-2, Qwen2) não precisam de chaves de API**, mas requerem arquivos `.gguf` baixados localmente. Veja os comentários nos arquivos de cada servidor em `servers/` para os caminhos esperados.

### Preparar índices FAISS (RAG)

Os índices FAISS são gerados automaticamente na primeira execução de cada servidor. Se você adicionou novos exemplos ao JSONL, apague os índices antigos para forçar reconstrução:

```bash
rm -rf rag/faiss_indexes/
```

O servidor irá reconstruir o índice na próxima inicialização (pode demorar alguns minutos dependendo da quantidade de exemplos e da velocidade da API de embeddings).

---

## 5. Como Iniciar o Projeto

Cada serviço é um processo independente. Você só precisa iniciar os serviços dos modelos que pretende usar.

### Configuração mínima (Gemini + Whisper local)

Abra **4 terminais** e execute um comando em cada:

```bash
# Terminal 1 — Transcrição de voz (Whisper local, sem chave de API)
python servers/transcription/whisper-local.py

# Terminal 2 — Construtor de blocos Gemini (precisa de GOOGLE_API_KEY)
python servers/block_constructor/gemini_constructor.py

# Terminal 3 — Explicador de código Gemini (precisa de GOOGLE_API_KEY)
python servers/code_explainer/gemini_code_explainer.py

# Terminal 4 — Servidor web PHP
php -S localhost:8080
```

Acesse: **http://localhost:8080**

### Serviços opcionais

Inicie conforme o modelo desejado nas configurações da IDE:

```bash
# Gerador de código por prompt livre (microfone → código)
python servers/code_generation/gemini_code_generator.py   # porta 4000

# Conversor de números por extenso (usado pelos assistentes de voz)
python servers/translate_number.py                         # porta 5050
```

### Iniciando modelos locais (sem internet)

```bash
# Llama — requer arquivo .gguf na pasta configurada no script
python servers/block_constructor/llama_constructor.py      # porta 7300
python servers/code_explainer/llama_code_explainer.py     # porta 5300
```

---

## 6. Guia de Uso

### Primeira vez

1. Abra `http://localhost:8080`
2. O **modal de boas-vindas** aparecerá — pressione **Enter** ou clique em "Iniciar Experiência" para ouvir a narração introdutória
3. Configure os modelos desejados clicando no botão **⚙️** (engrenagem) na toolbar

### Escrevendo código manualmente

O editor CodeFlask suporta syntax highlighting para Égua. Cada caractere digitado é lido em voz alta (ex: `=` → "igual", `(` → "abre parênteses").

### Usando os assistentes de voz

Clique em um dos botões da toolbar para iniciar um assistente guiado:

| Botão | Cor | O que cria |
|---|---|---|
| **Criar variável** | Verde | Variáveis simples ou vetores |
| **Operação** | Azul | Expressões matemáticas ou lógicas |
| **Condicional** | Vermelho | Estrutura `se / senão` |
| **Laço** | Laranja | `enquanto`, `para` ou `fazer-enquanto` |
| **Função** | Verde-azulado | Funções com parâmetros e retorno |
| **Classe** | Roxo | Classes com métodos e herança |
| **Imprimir valor na tela** | Roxo | Instrução `escreva()` |

### Executando o código

- Pressione **F6** ou **Shift+E** ou clique em **Executar**
- O resultado aparece no painel direito e é lido em voz alta
- O assistente pedagógico explica o que aconteceu

### Usando o microfone para prompts livres

- Clique no botão **🎤** para iniciar a captura contínua de voz
- Fale um comando (ex: "crie uma variável número com valor 10")
- Clique em **⏹️** para parar e enviar para o modelo de geração de código

---

## 7. Assistentes de Voz (Construtores de Blocos)

### 7.1 Criar Variável

**Atalho:** F2 | **Botão:** "Criar variável"

**Tipos suportados:**
- **Variável simples**: numérica, texto, booleana
- **Vetor**: numérico ou de texto, com até 5 posições

**Fluxo de diálogo (variável simples):**
```
1. "O que você deseja criar? Variável simples ou vetor?"
   → Usuário: "variável simples"
2. "Qual o tipo? Numérica, texto ou booleana?"
   → Usuário: "numérica"
3. "Qual o nome da variável?"
   → Usuário: "idade"
4. "Qual o valor?"
   → Usuário: "vinte e cinco"
→ Gera: var idade = 25;
```

### 7.2 Operação

**Atalho:** F3 | **Botão:** "Operação"

**Tipos:** matemática (+ - * /) ou lógica (== != > < e ou)

**Fluxo:**
```
1. "Tipo da operação? Matemática ou lógica?"
2. "Qual o primeiro operando?"
3. "Qual o operador?" (mais, menos, vezes, dividido por, igual, diferente, maior que...)
4. "Qual o segundo operando?"
5. "Deseja adicionar mais operações?"
6. "Deseja guardar em uma variável?"
→ Gera: var resultado = a + b;
```

### 7.3 Condicional

**Atalho:** F4 | **Botão:** "Condicional"

```
1. "Qual a condição do SE?"
2. "Qual a primeira operação do bloco SE?"
3. "Deseja adicionar mais operações ao bloco SE?"
4. "Deseja adicionar um bloco SENÃO?"
→ Gera:
   se (condicao) {
       acoes;
   } senão {
       acoes;
   }
```

### 7.4 Laço

**Botão:** "Laço"

#### Enquanto (while)
```
1. "Tipo: enquanto, para ou fazer enquanto?"
2. "Qual a condição de continuação?"
3. "Qual a primeira operação do corpo?"
→ Gera: enquanto (condicao) { acoes; }
```

#### Para (for)
```
1. "Tipo: para"
2. "Nome da variável de controle?" (ex: i)
3. "Valor inicial?" (ex: zero → 0)
4. "Valor final?"
5. "Incremento?" (ex: um → 1)
6. "Operações do corpo?"
→ Gera: para (var i = 0; i < 10; i = i + 1) { acoes; }
```

#### Fazer-Enquanto (do-while)
```
1. "Tipo: fazer enquanto"
2. "Operações do corpo?" (executadas ao menos uma vez)
3. "Condição de continuação?"
→ Gera: fazer { acoes; } enquanto (condicao)
```

### 7.5 Função

**Botão:** "Função"

```
1. "Qual o nome da função?"
2. "A função terá parâmetros?"
   → Se sim: "Quantos?" → nome de cada um
3. "Operações do corpo?"
4. "A função retorna algum valor?"
   → Se sim: "Qual?"
→ Gera:
   função nome(param1, param2) {
       acoes;
       retorna valor;
   }
```

### 7.6 Classe

**Botão:** "Classe"

```
1. "Qual o nome da classe?"
2. "A classe herda de outra?"
   → Se sim: "Nome da classe pai?"
3. Loop de métodos:
   a. "Nome do método?"
   b. "Tem parâmetros?"
   c. "Operações do método?"
   d. "Deseja adicionar outro método?"
→ Gera:
   classe Nome herda Pai {
       metodo(param) {
           acoes;
       }
   }
```

### 7.7 Imprimir valor na tela

**Atalho:** F5 | **Botão:** "Imprimir valor na tela"

```
1. "O que imprimir? Variável ou texto livre?"
   → Variável: "Qual o nome da variável?"
   → Texto: "Qual o texto?"
→ Gera: escreva(variavel); ou escreva("texto");
```

---

## 8. Atalhos de Teclado

### Editor de Código

| Atalho | Ação |
|---|---|
| `Shift + →` | Ler próximo caractere |
| `Shift + ←` | Ler caractere anterior |
| `Shift + ↓` | Ler próxima linha |
| `Shift + ↑` | Ler linha anterior |
| `Ctrl + →` | Ler próxima palavra |
| `Ctrl + ←` | Ler palavra anterior |
| `Ctrl + L` | Ler todo o código |
| `F6` / `Shift+E` | Executar código |
| `F7` | Ir para linha (por voz) |
| `F8` / `Shift+R` | Ler output do console novamente |
| `F10` / `Ctrl+R` | Limpar editor |
| `F11` / `Ctrl+S` | Exportar código |
| `F12` / `Alt+C` | Focar no editor |
| `Ctrl+G` | Ir para linha (número) |

### Assistentes e Navegação

| Atalho | Ação |
|---|---|
| `F1` | Ajuda dos assistentes (lista falada) |
| `Ctrl+H` | Ajuda do editor (lista falada) |
| `F2` | Criar variável |
| `F3` | Operação |
| `F4` | Condicional |
| `F5` | Imprimir na tela |
| `F9` / `Ctrl+K` | Ativar/desativar microfone |
| `Ctrl+Espaço` | Menu audível de 8 opções |
| `ESC` | Parar fala atual |
| `Ctrl+ESC` | Abortar operação do assistente |
| `Shift+Tab` | Retornar à navegação por Tab |

### Controle de Voz

| Atalho | Ação |
|---|---|
| `Ctrl + →` | Aumentar velocidade da voz |
| `Ctrl + ←` | Diminuir velocidade da voz |
| `Ctrl + ↑` | Aumentar tom da voz |
| `Ctrl + ↓` | Diminuir tom da voz |

---

## 9. Referência de Servidores e Portas

| Porta | Servidor | Modelo | Chave de API |
|---|---|---|---|
| **3000** | Transcrição Whisper local | OpenAI Whisper (local) | Não |
| **4000** | Gerador de código | Gemini 2.0 Flash | `GOOGLE_API_KEY` |
| **4100** | Gerador de código | GPT-4o Mini | `OPENAI_API_KEY` |
| **4300** | Gerador de código | Phi-2 (local) | Não |
| **4400** | Gerador de código | Llama 3.2 1B (local) | Não |
| **4500** | Gerador de código | Qwen2 1.5B (local) | Não |
| **4600** | Gerador de código | Transformer 19.5M | Não |
| **5000** | Explicador de código | Gemini 2.0 Flash | `GOOGLE_API_KEY` |
| **5050** | Conversor de números | Google Translate (free) | Não |
| **5100** | Explicador de código | GPT-4o Mini | `OPENAI_API_KEY` |
| **5200** | Explicador de código | Phi-2 (local) | Não |
| **5300** | Explicador de código | Llama 3.2 1B (local) | Não |
| **5400** | Explicador de código | Qwen2 1.5B (local) | Não |
| **7000** | Construtor de blocos | Gemini 1.5 Flash | `GOOGLE_API_KEY` |
| **7100** | Construtor de blocos | GPT-4o Mini | `OPENAI_API_KEY` |
| **7200** | Construtor de blocos | Phi-2 (local) | Não |
| **7300** | Construtor de blocos | Llama 3.2 1B (local) | Não |
| **7400** | Construtor de blocos | Qwen2 1.5B (local) | Não |
| **8080** | Servidor web | PHP (serve o frontend) | Não |

---

## 10. Arquivos e Estrutura do Projeto

```
online-coding-for-blinds/
│
├── index.html                     # Interface principal da IDE
├── transcribe.php                 # Proxy PHP para Whisper API (OpenAI)
├── composer.json                  # Dependência PHP: vlucas/phpdotenv
├── pyproject.toml                 # Dependências Python (gerenciadas por uv)
├── ruff.toml                      # Configuração do linter Python
├── CLAUDE.md                      # Guia para o assistente Claude Code
├── DOCUMENTACAO.md                # Este arquivo
├── RELATORIO_NOVOS_CONSTRUTORES.md # Relatório dos construtores implementados
│
├── css/
│   ├── style.css                  # Estilos principais
│   └── theme.css                  # Tema e customizações visuais
│
├── js/
│   ├── index.js                   # Lógica central do editor
│   ├── assist.js                  # Sistema de acessibilidade por voz
│   ├── config.js                  # Gerenciamento de configurações
│   ├── constructor.js             # Assistentes de construção por voz
│   ├── translate-models.js        # Roteamento de modelos e transcrição
│   ├── explain-code.js            # Execução e análise pedagógica
│   ├── demos.js                   # Exemplos de código Égua
│   ├── codeflask.min.js           # Editor com syntax highlighting
│   ├── words-to-numbers.min.js    # Conversão extenso → número (JS)
│   ├── egua/
│   │   └── egua.min.js            # Interpretador Égua (lexer, parser, runtime)
│   └── eslint.config.js           # Configuração do ESLint
│
├── servers/
│   ├── translate_number.py        # Flask: conversor de números (porta 5050)
│   ├── transcription/
│   │   └── whisper-local.py       # FastAPI: Whisper local (porta 3000)
│   ├── code_generation/
│   │   ├── gemini_code_generator.py  # Gemini RAG gerador (porta 4000)
│   │   ├── gpt_code_generator.py     # GPT-4o gerador (porta 4100)
│   │   ├── phi_code_generator.py     # Phi-2 gerador (porta 4300)
│   │   ├── llama_code_generator.py   # Llama gerador (porta 4400)
│   │   ├── qwen2_code_generator.py   # Qwen2 gerador (porta 4500)
│   │   └── transformer_code_generator.py  # Transformer (porta 6969)
│   ├── code_explainer/
│   │   ├── gemini_code_explainer.py  # Gemini RAG explicador (porta 5000)
│   │   ├── gpt_code_explainer.py     # GPT-4o explicador (porta 5100)
│   │   ├── phi_code_explainer.py     # Phi-2 explicador (porta 5200)
│   │   ├── llama_code_explainer.py   # Llama explicador (porta 5300)
│   │   └── qwen2_code_explainer.py   # Qwen2 explicador (porta 5400)
│   └── block_constructor/
│       ├── gemini_constructor.py     # Gemini RAG construtor (porta 7000)
│       ├── gpt_constructor.py        # GPT-4o construtor (porta 7100)
│       ├── phi2_constructor.py       # Phi-2 construtor (porta 7200)
│       ├── llama_constructor.py      # Llama construtor (porta 7300)
│       └── qwen2_constructor.py      # Qwen2 construtor (porta 7400)
│
├── rag/
│   ├── RAG_exemplos_codigo.jsonl              # 396 exemplos: prompt → código Égua
│   ├── RAG_exemplos_hibrido.jsonl             # 434 exemplos: JSON → código Égua
│   ├── RAG_token_parser_interpreter_examples.jsonl  # 50 exemplos pedagógicos
│   └── docs.txt                               # Documentação da linguagem Égua
│
├── audio/
│   ├── start_record.wav           # Som de início de gravação
│   └── end_record.wav             # Som de fim de gravação
│
└── assets/
    ├── logo_egua.svg
    └── egua.png
```

---

## 11. Sistema RAG (Retrieval-Augmented Generation)

O RAG melhora a qualidade da geração de código fornecendo exemplos relevantes ao modelo de linguagem antes de gerar a resposta.

### Como funciona

```
JSON de entrada
     │
     ▼
Gerar embedding (Gemini embedding-001 / 768 dims)
     │
     ▼
Busca por similaridade no FAISS (K=5 exemplos mais próximos)
     │
     ▼
Montar prompt: System Prompt + Exemplos Recuperados + JSON atual
     │
     ▼
Modelo de linguagem gera código Égua (temperature=0.0)
```

### Arquivos de dados

| Arquivo | Usado por | Formato | Exemplos |
|---|---|---|---|
| `RAG_exemplos_hibrido.jsonl` | Construtores de blocos | `{json_input, codigo_gerado}` | 434 |
| `RAG_exemplos_codigo.jsonl` | Gerador de código por prompt | `{prompt, codigo}` | 396 |
| `RAG_token_parser_interpreter_examples.jsonl` | Explicador pedagógico | `{codigo, tokens, ast, interpretador}` | 50 |
| `docs.txt` | Todos os servidores | Texto livre (parágrafos) | — |

### Índices FAISS

Gerados automaticamente em `rag/faiss_indexes/` na primeira inicialização:

```
rag/faiss_indexes/
├── gemini_constructor/
│   ├── index.faiss      # Vetores FAISS
│   └── metadados.json   # Referências para recuperação
├── gemini_explainer/
│   └── ...
└── gemini_generator/
    └── ...
```

> Apague `rag/faiss_indexes/` sempre que adicionar novos exemplos ao JSONL.

---

## 12. Modelos de IA Suportados

### Transcrição de Voz

| Opção | Descrição | Requer API |
|---|---|---|
| **Web Speech API** | Nativo do navegador, resultado imediato | Não |
| **Whisper local** | Modelo Whisper "turbo" rodando em CPU/GPU local | Não |
| **Whisper API** | API da OpenAI (via `transcribe.php`) | `OPENAI_API_KEY` |

### Geração de Código, Explicação e Construção de Blocos

| Modelo | Tipo | Qualidade | Velocidade | Requer API |
|---|---|---|---|---|
| **Gemini 2.0 Flash** | Cloud | ⭐⭐⭐⭐⭐ | Rápido | `GOOGLE_API_KEY` |
| **GPT-4o Mini** | Cloud | ⭐⭐⭐⭐ | Rápido | `OPENAI_API_KEY` |
| **Phi-2** | Local | ⭐⭐⭐ | Lento (CPU) | Não |
| **Llama 3.2 1B** | Local | ⭐⭐⭐ | Lento (CPU) | Não |
| **Qwen2 1.5B** | Local | ⭐⭐⭐ | Lento (CPU) | Não |

---

## 13. Sintaxe da Linguagem Égua

### Variáveis

```
var nome = "João";
var idade = 25;
var ativo = verdadeiro;
var vazio;                    // valor nulo
var lista = [1, 2, 3];
```

### Operadores

```
// Aritméticos
a + b    a - b    a * b    a / b    a % b    a ** b

// Comparação
a == b    a != b    a > b    a < b    a >= b    a <= b

// Lógicos
a e b    a ou b    a em lista
```

### Condicional

```
se (condicao) {
    escreva("verdadeiro");
} senão se (outraCondicao) {
    escreva("outro caso");
} senão {
    escreva("falso");
}
```

### Laços

```
// Enquanto (while)
enquanto (condicao) {
    // corpo
}

// Para (for estilo C)
para (var i = 0; i < 10; i = i + 1) {
    escreva(i);
}

// Fazer-enquanto (do-while)
fazer {
    // corpo executado ao menos uma vez
} enquanto (condicao)
```

### Funções

```
função somar(a, b) {
    var resultado = a + b;
    retorna resultado;
}

// Chamada
var total = somar(3, 5);
escreva(total);              // exibe: 8
```

### Classes

```
classe Animal {
    correr() {
        escreva("Correndo!");
    }
}

classe Cachorro herda Animal {
    latir() {
        escreva("Au Au!");
    }
}

// Instância
var meuCachorro = Cachorro();
meuCachorro.correr();       // Correndo!
meuCachorro.latir();        // Au Au!
```

### Entrada e Saída

```
escreva("Olá, Mundo!");
escreva("Valor: " + texto(42));    // conversão número → string
```

---

## 14. Variáveis de Ambiente

Crie o arquivo `.env` na raiz do projeto:

```bash
# Obrigatório para usar Gemini (geração, explicação, construção)
GOOGLE_API_KEY=AIzaSy...

# Obrigatório para usar GPT-4o ou Whisper API
OPENAI_API_KEY=sk-proj-...

# URL do endpoint de transcrição (padrão OpenAI, não altere)
OPENAI_CURL=https://api.openai.com/v1/audio/transcriptions
```

| Variável | Quem usa | Obrigatório |
|---|---|---|
| `GOOGLE_API_KEY` | Todos os servidores `gemini_*.py` | Se usar Gemini |
| `OPENAI_API_KEY` | `transcribe.php`, `gpt_*.py` | Se usar GPT ou Whisper API |
| `OPENAI_CURL` | `transcribe.php` | Se usar Whisper API |

---

## 15. Fluxos de Dados

### Fluxo 1: Construtor de Blocos por Voz

```
[Usuário clica "Criar variável"]
         │
         ▼
[Assistente faz perguntas por síntese de voz]
  "Qual o tipo?" → Microfone → Transcrição
  "Qual o nome?" → Microfone → Transcrição
  "Qual o valor?" → Microfone → textoParaNumero()
         │
         ▼
[JSON estruturado montado]
  { acao: "criarVariavel", tipo: "numérica", nome: "idade", valor: 25 }
         │
         ▼
[POST para servidor construtor selecionado]
  localhost:7000/gerar-codigo (Gemini)
         │
         ▼
[Servidor: RAG busca exemplos + Gemini gera código]
  → "var idade = 25;"
         │
         ▼
[Código inserido no editor + feedbackAudio("Código criado!")]
```

### Fluxo 2: Prompt Livre por Microfone

```
[Usuário clica 🎤 e fala: "crie uma variável x com valor 10"]
         │
         ▼
[MediaRecorder captura áudio]
         │
         ▼
[POST áudio para transcritor]
  localhost:3000/transcrever (Whisper local)
  → "crie uma variável x com valor 10"
         │
         ▼
[POST {prompt, codigo_atual} para gerador]
  localhost:4000/gerar-codigo (Gemini)
         │
         ▼
[RAG + Gemini gera código]
  → "var x = 10;"
         │
         ▼
[Código inserido no editor]
```

### Fluxo 3: Execução + Feedback Pedagógico

```
[Usuário pressiona F6]
         │
         ▼
[runCode() em explain-code.js]
  Lexer → tokens
  Parser → AST
  runBlock() → output do console
         │
         ▼
[POST {codigo, tokens, ast, output} para explicador]
  localhost:5000/ (Gemini)
         │
         ▼
[Servidor: RAG recupera exemplos pedagógicos + Gemini analisa]
  → Markdown com explicação/feedback
         │
         ▼
[processarRespostaCompleta()]
  DOM: Texto estruturado + blocos de código
  Áudio: feedbackAudio() narrada em pt-BR
```

---

## 16. Configuração via Interface

Clique no botão **⚙️** na toolbar para abrir o painel de configurações.

### Modelos disponíveis por função

**Transcrição (Fala → Texto):**
- `Whisper (local)` — requer servidor na porta 3000
- `Whisper (API)` — requer `OPENAI_API_KEY` no `.env`
- `Web Speech API` — nativo do navegador (sem servidor)

**Tradução Fala → Código:**
- `gemini-1.5-flash-latest` — porta 4000
- `gpt-4o-mini` — porta 4100
- `transformer-19.5M` — porta 6969
- `Phi-2` — porta 4300
- `Llama 3.2 1B Instruct` — porta 4400
- `Qwen2-1.5B-Instruct` — porta 4500

**Assistente (Explicação Pedagógica):**
- `gemini-2.0-flash-latest` — porta 5000
- `gpt-4o-mini` — porta 5100
- `Phi-2` — porta 5200
- `Llama 3.2 1B Instruct` — porta 5300
- `Qwen2-1.5B-Instruct` — porta 5400

**Construtor de Blocos:**
- `gemini-1.5-flash-latest` — porta 7000
- `gpt-4o-mini` — porta 7100
- `Phi-2` — porta 7200
- `Llama 3.2 1B Instruct` — porta 7300
- `Qwen2-1.5B-Instruct` — porta 7400

> As configurações são salvas no `localStorage` do navegador e persistem entre sessões.

---

*Documentação gerada em: 2026-06-07 | Versão do projeto: 0.1.0*
