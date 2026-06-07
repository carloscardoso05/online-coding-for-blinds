# Relatório: Implementação dos Novos Construtores de Blocos

## Visão Geral do Projeto

**Égua Assist** é uma extensão para a IDE Égua que ensina lógica de programação a estudantes com deficiência visual. O sistema usa reconhecimento de voz e síntese de fala para guiar o usuário na criação de código Égua por meio de diálogos estruturados — sem necessidade de digitar.

A arquitetura é composta por:

- **Frontend**: HTML/CSS/JS puro servido via PHP (`index.html`, `js/constructor.js`)
- **Backend**: microserviços Python Flask/FastAPI por modelo de linguagem
- **RAG**: sistema de recuperação por similaridade (FAISS + embeddings) para melhorar a qualidade da geração de código

---

## Funcionalidades Já Existentes (Antes desta Implementação)

| Botão | Função JS | Descrição |
|---|---|---|
| Criar variável | `criarVariavel()` | Variável simples (numérica, texto, booleana) ou vetor |
| Operação | `operacao()` | Expressões matemáticas e lógicas |
| Condicional | `condicional()` | Estrutura `se / senão` |
| Imprimir valor na tela | `escrever()` | `escreva()` com variável ou texto livre |

---

## Novas Funcionalidades Implementadas

### 1. Construtor de Laços (`laco()`)

**Botão**: `Laço` — cor laranja-escuro `#b05c00`

**Tipos de laço suportados:**

#### Enquanto (while)
Repete um bloco enquanto uma condição for verdadeira.

```
enquanto (condição) {
    // ações
}
```

**Fluxo de voz:**
1. Pergunta o tipo de laço ("enquanto", "para" ou "fazer enquanto")
2. Pergunta a condição de continuação
3. Coleta as ações do corpo (igual aos outros construtores)

**Exemplo de JSON gerado:**
```json
{
  "acao": "laco",
  "tipo": "enquanto",
  "condicao": "contador maior que zero",
  "acoes": ["escreva o contador", "decremente o contador em um"]
}
```

**Código Égua resultante:**
```
enquanto (contador > 0) {
    escreva(contador);
    contador = contador - 1;
}
```

---

#### Para (for)
Laço com variável de controle, valor inicial, valor final e incremento.

```
para (var i = 0; i < 5; i = i + 1) {
    // ações
}
```

**Fluxo de voz:**
1. Pergunta o nome da variável de controle
2. Pergunta o valor inicial (convertido de extenso para número)
3. Pergunta o valor final
4. Pergunta o incremento
5. Coleta as ações do corpo

**Exemplo de JSON gerado:**
```json
{
  "acao": "laco",
  "tipo": "para",
  "variavel": "i",
  "inicio": 0,
  "fim": 10,
  "incremento": 1,
  "acoes": ["escreva o valor de i"]
}
```

**Código Égua resultante:**
```
para (var i = 0; i < 10; i = i + 1) {
    escreva(i);
}
```

---

#### Fazer-Enquanto (do-while)
Executa o corpo ao menos uma vez antes de verificar a condição.

```
fazer {
    // ações
} enquanto (condição)
```

**Fluxo de voz:**
1. Coleta as ações do corpo **primeiro**
2. Pergunta a condição de continuação ao final

**Exemplo de JSON gerado:**
```json
{
  "acao": "laco",
  "tipo": "fazer-enquanto",
  "condicao": "resposta diferente de sair",
  "acoes": ["mostre o menu", "leia a resposta"]
}
```

**Código Égua resultante:**
```
fazer {
    mostrar_menu();
    ler_resposta();
} enquanto (resposta != "sair")
```

---

### 2. Construtor de Funções (`criarFuncao()`)

**Botão**: `Função` — cor verde-azulado `#006b6b`

Cria funções nomeadas com parâmetros opcionais e retorno opcional.

```
função nome(param1, param2) {
    // ações
    retorna valor;
}
```

**Fluxo de voz:**
1. Pergunta o nome da função
2. Pergunta se a função tem parâmetros (sim/não)
   - Se sim: pergunta a quantidade e o nome de cada parâmetro individualmente
3. Coleta as ações do corpo
4. Pergunta se a função retorna algum valor (sim/não)
   - Se sim: pergunta qual valor ou variável retornar

**Exemplo de JSON gerado:**
```json
{
  "acao": "funcao",
  "nome": "calcular media",
  "parametros": ["nota1", "nota2"],
  "acoes": ["some nota1 e nota2 e divida por 2 guardando em media"],
  "retorna": "media"
}
```

**Código Égua resultante:**
```
função calcular_media(nota1, nota2) {
    var media = (nota1 + nota2) / 2;
    retorna media;
}
```

**Observações:**
- Nomes com espaços são convertidos para snake_case pelo modelo
- O campo `retorna` é `null` quando a função não retorna nada
- A keyword `retorna` é emitida no código apenas quando necessário

---

### 3. Construtor de Classes (`criarClasse()`)

**Botão**: `Classe` — cor roxo `#5a0080`

Cria classes com métodos e herança opcional, seguindo a orientação a objetos do Égua.

```
classe NomeDaClasse {
    metodo(param) {
        // ações
    }
}

// com herança:
classe Filha herda Pai {
    outroMetodo() {
        // ações
    }
}
```

**Fluxo de voz:**
1. Pergunta o nome da classe
2. Pergunta se a classe herda de outra (sim/não)
   - Se sim: pergunta o nome da classe pai
3. Loop de coleta de métodos (mínimo 1):
   - Pergunta o nome do método
   - Pergunta se o método tem parâmetros (sim/não)
     - Se sim: pergunta a quantidade e o nome de cada parâmetro
   - Coleta as ações do corpo do método
   - Pergunta se o usuário quer adicionar outro método

**Exemplo de JSON gerado:**
```json
{
  "acao": "classe",
  "nome": "Cachorro",
  "herda": "Animal",
  "metodos": [
    {
      "nome": "latir",
      "parametros": [],
      "acoes": ["escreva au au au"]
    },
    {
      "nome": "buscar",
      "parametros": ["objeto"],
      "acoes": ["escreva buscando objeto"]
    }
  ]
}
```

**Código Égua resultante:**
```
classe Cachorro herda Animal {
    latir() {
        escreva("Au Au Au!");
    }
    buscar(objeto) {
        escreva("Buscando " + objeto);
    }
}
```

---

## Dataset RAG — Exemplos Adicionados

O arquivo `rag/RAG_exemplos_hibrido.jsonl` recebeu **45 novos exemplos**:

| Tipo | Qtd | Detalhes |
|---|---|---|
| Laço `enquanto` | 7 | contadores, validação, iteração por lista |
| Laço `para` | 6 | iterações numéricas, acesso a vetor, tabuada |
| Laço `fazer-enquanto` | 2 | menu interativo, leitura validada |
| Função sem param/retorno | 3 | saudar, separador, exibir nome |
| Função com parâmetros | 6 | exibir mensagem, verificar aprovação, par/ímpar |
| Função com retorno | 6 | somar, média, área, fatorial, desconto, conversão |
| Classe simples | 10 | Animal, Veiculo, Calculadora, Produto, Jogo, etc. |
| Classe com herança | 5 | Cachorro→Animal, Estudante→Pessoa, Gato→Animal, etc. |

**Total de exemplos no dataset após a implementação: 434**

> **Atenção:** Os índices FAISS existentes em `rag/faiss_indexes/` devem ser deletados para que os servidores reconstruam o índice incluindo os novos exemplos.

---

## Histórico de Commits

| Hash | Mensagem |
|---|---|
| `65ddf28` | `rag: adiciona 15 exemplos de laços ao dataset híbrido` |
| `d8238d5` | `feat(constructor): implementa construtor de laços por voz (laco)` |
| `a0bbfa1` | `feat(ui): adiciona botão 'Laço' na barra de ferramentas` |
| `5ef8e22` | `rag: adiciona 15 exemplos de funções ao dataset híbrido` |
| `4e463f2` | `feat(constructor): implementa construtor de funções por voz (criarFuncao)` |
| `55b1dcd` | `feat(ui): adiciona botão 'Função' na barra de ferramentas` |
| `950fa54` | `rag: adiciona 15 exemplos de classes ao dataset híbrido` |
| `65d18d8` | `feat(constructor): implementa construtor de classes por voz (criarClasse)` |
| `dc52941` | `feat(ui): adiciona botão 'Classe' na barra de ferramentas` |

---

## Arquivos Modificados

| Arquivo | Tipo de modificação |
|---|---|
| `js/constructor.js` | Adição das funções `laco()`, `criarFuncao()`, `criarClasse()` |
| `index.html` | Adição de 3 botões na toolbar, estilos CSS para cada um |
| `rag/RAG_exemplos_hibrido.jsonl` | 45 novos exemplos de treinamento |

---

## Sintaxe Égua — Referência Rápida

### Laços

```
// While
enquanto (condicao) {
    // corpo
}

// For (estilo C)
para (var i = 0; i < 10; i = i + 1) {
    // corpo
}

// Do-while
fazer {
    // corpo
} enquanto (condicao)
```

### Funções

```
função somar(a, b) {
    var resultado = a + b;
    retorna resultado;
}

// Chamada
escreva(somar(3, 5)); // exibe 8
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

var meuCachorro = Cachorro();
meuCachorro.correr();
meuCachorro.latir();
```

---

## Como Testar

1. Delete os índices FAISS antigos (se existirem):
   ```sh
   rm -rf rag/faiss_indexes/
   ```

2. Inicie um serviço de construção de blocos (ex: Gemini):
   ```sh
   python servers/block_constructor/gemini_constructor.py
   ```

3. Inicie o servidor PHP:
   ```sh
   php -S localhost:8080
   ```

4. Abra `http://localhost:8080` no navegador

5. Clique em **Laço**, **Função** ou **Classe** na barra de ferramentas e siga as instruções de voz

---

## Considerações de Acessibilidade

Todos os novos botões foram desenvolvidos com acessibilidade como prioridade:

- **`aria-label` descritivo** em cada botão, explicando o que o construtor faz
- **Feedback de áudio** em cada etapa do diálogo (via `feedbackAudio()`)
- **Feedback de erro** explícito quando o usuário não responde ou responde algo não reconhecido
- **Interrupção por teclado** (`Ctrl+Escape`) funciona em todos os novos construtores, pois todos usam `ouvirComTentativas()` que respeita o flag `interromperOuvir`
- **Tolerância a erros de reconhecimento** via função `corrigir()` (distância de Levenshtein) nas respostas sim/não
