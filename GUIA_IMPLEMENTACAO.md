# 🚀 Guia Prático de Implementação - FullTrack + N8n + Python

## 📋 Índice
1. [Setup Python + Selenium](#1-setup-python--selenium)
2. [Encontrar Seletores CSS](#2-encontrar-seletores-css)
3. [Testar Script Python](#3-testar-script-python)
4. [Integrar com N8n](#4-integrar-com-n8n)
5. [Troubleshooting](#5-troubleshooting)

---

## 1. Setup Python + Selenium

### **1.1 Instalar Python (se não tiver)**
```bash
# Windows: baixe em https://www.python.org/downloads/
# Linux/Mac:
sudo apt-get install python3 python3-pip
```

### **1.2 Instalar dependências**
```bash
pip install selenium webdriver-manager

# Opcional (para logs mais bonitos)
pip install colorama
```

### **1.3 Verificar instalação**
```bash
python3 --version
python3 -c "import selenium; print(f'Selenium: {selenium.__version__}')"
```

Esperado:
```
Python 3.8+
Selenium: 4.x.x
```

---

## 2. Encontrar Seletores CSS

### ⚠️ **ESTE É O PASSO MAIS IMPORTANTE**

Sem os seletores corretos, o script não funciona!

### **2.1 Abrir DevTools do Chrome**

1. Abra o site FullTrack no Chrome
2. Pressione `F12` para abrir Developer Tools
3. Vá para aba **Elements** (ou Inspect)

### **2.2 Encontrar Campo de Busca**

```
1. Na página do mapa, localize o campo onde você digita o número
2. Clique com botão direito → "Inspect" (ou Inspect Element)
3. Procure por uma linha assim:

   <input type="search" id="search_box" placeholder="Digite número">
   ou
   <input class="form-control" name="numero">
   ou
   <input type="text" data-id="search">

4. COPIE O ID, CLASS OU SELETOR CSS
```

**Exemplos de seletores:**
```python
# Se tem ID:
"input#search_box"  # ID = search_box

# Se tem class:
"input.form-control"  # Class = form-control

# Se tem type:
"input[type='search']"

# Genérico (último recurso):
"input[type='text']"
```

**Onde colocar no código:**
```python
# No arquivo buscar_fulltrack.py, linha ~45:
"search_field": "input#search_box",  # ← AJUSTE AQUI
```

### **2.3 Encontrar Botão de Busca**

```
1. Procure pelo botão "Buscar", "Enviar", lupa, etc
2. Clique direito → Inspect
3. Procure por:

   <button id="btn-search">Buscar</button>
   ou
   <button class="btn-primary">Buscar</button>
   ou
   <i class="icon-search"></i>

4. COPIE O SELETOR
```

**Exemplos:**
```python
"search_button": "button#btn-search"
"search_button": "button.btn-primary"
"search_button": "button:contains('Buscar')"  # XPath alternativo
```

### **2.4 Encontrar Resultado**

```
1. Execute uma busca de teste (manualmente)
2. DevTools continuando aberto
3. Procure pelo resultado que aparece:

   <div class="resultado-card" data-id="12345">...</div>
   ou
   <tr class="search-result">...</tr>
   ou
   <div class="item-resultado">...</div>

4. COPIE
```

### **2.5 Encontrar "Comandos Enviados"**

```
1. Clique no resultado (manualmente)
2. Procure pelo link/texto "Comandos Enviados"
3. DevTools aberto
4. Clique direito no texto → Inspect

Procure por:
   <a href="#" class="tab-link">Comandos Enviados</a>
   ou
   <span>Comandos Enviados</span>

Copie a classe ou ID
```

### **2.6 Encontrar Botão Enviar**

```
1. Depois de abrir "Comandos Enviados"
2. Procure pelo botão "Enviar" ou similar
3. Inspect
4. Procure por:

   <button class="btn btn-success">Enviar</button>
   <button id="submit-btn">Enviar</button>
   <input type="submit" value="Enviar">
```

### **📸 Exemplo Prático - Captura de Tela**

Se você enviar a captura, posso extrair os seletores automaticamente!

Tire print com:
```
1. F12 aberto
2. Elementos de interesse destacados
3. Envie para análise
```

---

## 3. Testar Script Python

### **3.1 Criar arquivo de configuração**

Crie `config_fulltrack.json`:
```json
{
  "FULLTRACK_URL": "https://12308-htm-indust-de-equip-eletro-eletronicos-ltda.fulltrackapp.com/mapaGeral_v3/#/",
  "HEADLESS": false,
  "SELECTORS": {
    "search_field": "input[type='search']",
    "search_button": "button.btn-search",
    "first_result": ".resultado-item",
    "comandos_text": "Comandos enviados",
    "send_button": "//button[contains(text(), 'Enviar')]"
  }
}
```

### **3.2 Testar com um número**

```bash
# Teste 1: Com um número (modo com interface para debug)
echo '["12345"]' | python3 buscar_fulltrack.py

# Saída esperada:
# {
#   "timestamp": "2024-01-15T10:30:00",
#   "total": 1,
#   "sucessos": 1,
#   "resultados": [
#     {
#       "numero": "12345",
#       "status": "sucesso",
#       "resultado": "dados coletados...",
#       "mensagem": ""
#     }
#   ]
# }
```

### **3.3 Interpretar resultado**

```python
{
  "status": "sucesso",      # ✅ Funcionou!
  "status": "nao_encontrado",  # ⚠️ Número não existe no sistema
  "status": "erro",         # ❌ Algo deu errado
}
```

### **3.4 Modo Debug (com interface)**

Se `HEADLESS: false`, o Chrome abre e você vê o que está acontecendo.

**Ótimo para debugar!**

```python
# Edite a linha ~80 do script:
CONFIG = {
    "HEADLESS": False,  # ← MUDE PARA False
    ...
}

# Rode e observe
python3 buscar_fulltrack.py < numeros.json
```

---

## 4. Integrar com N8n

### **4.1 Setup do Workflow N8n**

#### **Node 1: Trigger Manual**
```
Type: Manual Trigger
Executa quando você clicar "Execute Workflow"
```

#### **Node 2: Google Sheets Read**
```
Service: Google Sheets
Action: Read rows
Spreadsheet: Mosaico bloqueio (ou seu Google Sheets)
Range: Sheet1!A:A
Columns: numero
```

**Output esperado:**
```json
[
  { "numero": "12345" },
  { "numero": "67890" },
  { "numero": "11111" }
]
```

#### **Node 3: Execute Command**
```
Service: Execute Command
Command: python3
Arguments:
  - /path/to/buscar_fulltrack.py

Stdin:
  {{ JSON.stringify($node['Google Sheets Read'].json.rows) }}

Working Directory: /home/user
```

**Configuração detalhada:**

1. Clique em "Execute Command"
2. Em "Command", coloque: `python3`
3. Em "Arguments", adicione 1 item: `/path/to/buscar_fulltrack.py`
4. Em "Input" (se houver), coloque:
   ```
   {{ JSON.stringify($node['Google Sheets Read'].json.rows) }}
   ```
5. Deixe "Output in Separate Output" marcado

#### **Node 4: Parse JSON (opcional)**
```
Service: Set
Key: resultados_parsed
Value: {{ JSON.parse($node['Execute Command'].data.stdout) }}
```

#### **Node 5: Write to Google Sheets**
```
Service: Google Sheets
Action: Append rows
Spreadsheet: Mosaico bloqueio
Table: Sheet1
Columns:
  - numero: {{ $item.numero }}
  - status: {{ $item.status }}
  - resultado: {{ $item.resultado }}
  - mensagem: {{ $item.mensagem }}
  - timestamp: {{ $item.timestamp }}
```

#### **Node 6: Send Notification (Email)**
```
Service: Send Email (Gmail)
To: seu_email@empresa.com
Subject: FullTrack - Processamento Concluído
Body:
  Total processado: {{ $node['Google Sheets Read'].json.rows.length }}
  Sucessos: {{ $node['Parse JSON'].json.sucessos }}
  Erros: {{ $node['Parse JSON'].json.erros }}
```

### **4.2 Estrutura completa do Workflow em JSON**

Salve como `fulltrack_workflow.json`:

```json
{
  "nodes": [
    {
      "parameters": {},
      "name": "Manual Trigger",
      "type": "n8n-nodes-base.manualTrigger",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "authentication": "oauth2",
        "spreadsheetId": "YOUR_SHEET_ID",
        "range": "Sheet1!A:A",
        "firstDataRow": 2
      },
      "name": "Google Sheets Read",
      "type": "n8n-nodes-base.googleSheets",
      "typeVersion": 4,
      "position": [450, 300]
    },
    {
      "parameters": {
        "command": "python3",
        "arguments": "/path/to/buscar_fulltrack.py",
        "input": "{{ JSON.stringify($node['Google Sheets Read'].json) }}"
      },
      "name": "Execute Python",
      "type": "n8n-nodes-base.executeCommand",
      "typeVersion": 1,
      "position": [650, 300]
    },
    {
      "parameters": {
        "jsonParse": true
      },
      "name": "Parse Output",
      "type": "n8n-nodes-base.set",
      "typeVersion": 1,
      "position": [850, 300]
    }
  ],
  "connections": {
    "Manual Trigger": {
      "main": [[{"node": "Google Sheets Read", "type": "main", "index": 0}]]
    },
    "Google Sheets Read": {
      "main": [[{"node": "Execute Python", "type": "main", "index": 0}]]
    },
    "Execute Python": {
      "main": [[{"node": "Parse Output", "type": "main", "index": 0}]]
    }
  }
}
```

### **4.3 Importar Workflow no N8n**

1. Abra N8n
2. Menu → "Import from File"
3. Selecione `fulltrack_workflow.json`
4. Ajuste IDs do Google Sheets (Sheet ID)
5. Teste com "Execute Workflow"

---

## 5. Troubleshooting

### **❌ Erro: "Element not found"**

**Causa:** Seletor CSS está errado

**Solução:**
```bash
1. Abra DevTools (F12)
2. Console
3. Teste seu seletor:
   
   document.querySelector("input[type='search']")
   
   Se retornar null → SELETOR ESTÁ ERRADO
   Se retornar element → SELETOR ESTÁ CERTO

4. Ajuste o seletor conforme necessário
```

### **❌ Erro: "Timeout waiting for element"**

**Causa:** Elemento demora para carregar ou página está lenta

**Solução:**
```python
# Edite no script:
"TIMEOUT": 20,  # Aumente para 30 ou 40
"DELAY_AFTER_CLICK": 2,  # Aumente para 3 ou 4
```

### **❌ Erro: "Stale element reference"**

**Causa:** Elemento desapareceu durante processamento

**Solução:**
```python
# Já tratado no código, mas se persistir:
# Reduza a velocidade adicionando mais delays

"DELAY_AFTER_CLICK": 3,
"DELAY_BETWEEN_SEARCHES": 2,
```

### **❌ Erro: "Chrome driver not found"**

**Causa:** ChromeDriver não instalado

**Solução:**
```bash
# Instale webdriver-manager (já faz download automático)
pip install webdriver-manager
```

### **❌ Erro: "Permission denied"**

**Causa:** Arquivo não tem permissão de execução

**Solução (Linux/Mac):**
```bash
chmod +x buscar_fulltrack.py
./buscar_fulltrack.py
```

### **❌ Script fica pendurado**

**Causa:** Aguardando elemento que nunca aparece

**Solução:**
```bash
# Pressione Ctrl+C para interromper
Ctrl+C

# Aumente verbosidade de logs:
# No topo do script, mude:
"LOG_LEVEL": "DEBUG",  # ← MUDE PARA DEBUG
```

### **✅ Como verificar se funciona**

```bash
# 1. Teste unitário
echo '["TEST123"]' | python3 buscar_fulltrack.py

# 2. Verifique saída (procure por "sucesso" ou "nao_encontrado")
# Se apareceu, script funciona!

# 3. Teste com headless=False e observe visualmente
```

---

## 📞 Próximos Passos

1. **Você enviou os seletores CSS?** Sim → Vá para Passo 3
2. **Script testou com sucesso?** Sim → Vá para Passo 4
3. **Workflow N8n criado?** Sim → Configure Cron/Schedule

---

## 🔗 Links Úteis

- [Selenium Python Docs](https://selenium-python.readthedocs.io/)
- [CSS Selectors Reference](https://www.w3schools.com/cssref/selectors.asp)
- [XPath Syntax](https://www.w3schools.com/xml/xpath_syntax.asp)
- [N8n Documentation](https://docs.n8n.io/)
- [Chrome DevTools](https://developer.chrome.com/docs/devtools/)

---

## 📝 Checklist de Implementação

- [ ] Python 3.8+ instalado
- [ ] Selenium + webdriver-manager instalados
- [ ] Seletores CSS encontrados e testados
- [ ] Script Python testado com 1 número
- [ ] Script Python testado com lote de números
- [ ] Google Sheets configurada
- [ ] Workflow N8n criado
- [ ] Teste end-to-end do workflow
- [ ] Agendamento (Cron) configurado
- [ ] Email de notificação configurado
- [ ] Pessoal treinado

---

**Precisa de ajuda?** Envie:
- Prints do site (F12 aberto)
- Output do script Python
- Logs de erro
- Seu workflow N8n
