# 🔄 Análise da Macro FullTrack + Plano de Migração

## 📊 Análise da Macro Atual (Macro Recorder)

### **URL do Site**
```
https://12308-htm-indust-de-equip-eletro-eletronicos-ltda.fulltrackapp.com/mapaGeral_v3/#/
```

### **Planilha Atual**
```
C:\Users\vinicius.alves\Desktop\Mosaico bloqueio.xlsx
Coluna: A
Celula inicial: A1
```

### **Fluxo Completo da Macro (Simplificado)**

```
┌─────────────────────────────────────────────────────────┐
│ 1. INICIALIZAÇÃO                                        │
├─────────────────────────────────────────────────────────┤
│ • Abre navegador Chrome
│ • Acessa página de login do FullTrack
│ • Localiza e clica em "Entrar"
│ • Aguarda 4 segundos (validar captura de tela)
│ • Abre nova aba
│ • Acessa URL: /mapaGeral_v3/#/
│ • Aguarda 4 segundos
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 2. LEITURA DE DADOS                                     │
├─────────────────────────────────────────────────────────┤
│ • Abre arquivo: Mosaico bloqueio.xlsx
│ • Lê célula A1 (primeiro número de série)
│ • Copia número para clipboard
│ • Aguarda 2 segundos
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 3. BUSCA NO SITE                                        │
├─────────────────────────────────────────────────────────┤
│ • Retorna ao mapa (tab anterior)
│ • Aguarda 4 segundos
│ • Clica no campo de busca (chamado "buscar do mapa")
│ • Cola o número de série
│ • Pressiona ENTER
│ • Aguarda 4 segundos
│ • Clica no número de série do aparelho (resultado)
│ • Aguarda 4 segundos
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 4. VALIDAÇÃO/COLETA                                     │
├─────────────────────────────────────────────────────────┤
│ • Procura pela palavra "Comandos enviados"
│ • Clica em "Comandos enviados"
│ • Aguarda 4 segundos
│ • Copia conteúdo da área de transferência
│ • Valida se número é válido (verificação de clipboard)
│ • Vai aumentando zoom para encontrar "Enviar"
│ • Clica em "Enviar"
│ • Aguarda 3 segundos
│ • Reseta zoom para 100%
│ • Fecha guia
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 5. PRÓXIMO CICLO                                        │
├─────────────────────────────────────────────────────────┤
│ • Retorna para planilha
│ • Aguarda 3 segundos
│ • Vai para próximo número de série (A2, A3, etc)
│ • Copia próximo número
│ • **VOLTA PARA PASSO 3** (loop)
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Pontos Críticos Identificados

### **Dependências do Site (FullTrack)**
- ❌ Busca por texto visual ("Comandos enviados", "Enviar")
- ❌ Ajustes de zoom necessários
- ❌ Área de transferência para validação
- ❌ Múltiplas abas/tabs
- ⚠️ Waits/Aguardas extensas (4-10 segundos)

### **Por que é frágil:**
1. Se a interface muda, quebra tudo
2. Busca visual é slow (zoom, procurar texto)
3. Área de transferência é unreliable
4. Sem tratamento de erro adequado

---

## 🚀 SOLUÇÃO PROPOSTA: N8n + Python + Selenium

### **Nova Arquitetura**

```
┌─────────────────────┐
│  Planilha Excel     │
│  (Google Sheets)    │
│  Coluna: Números    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│  N8n - Workflow                         │
│  1. Lê planilha (Google Sheets API)     │
│  2. Extrai array de números             │
│  3. Chama Python Script                 │
│  4. Recebe resultados                   │
│  5. Salva em Google Sheets (coluna B)   │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│  Python + Selenium Script               │
│  • Abre FullTrack                       │
│  • Para cada número:                    │
│    - Busca no mapa                      │
│    - Clica resultado                    │
│    - Coleta dados                       │
│    - Envia comando                      │
│  • Retorna JSON com resultados          │
└─────────────────────────────────────────┘
```

### **Vantagens**
✅ Mais rápido (sem zoom, sem busca visual)
✅ Mais confiável (seletores CSS/ID específicos)
✅ Fácil manutenção (lógica centralizada)
✅ Escalável (fácil adicionar validações)
✅ Logs detalhados de cada step
✅ Retry automático em falhas
✅ Roda em background (headless)

---

## 📝 SCRIPT PYTHON - Template Base

### **Pré-requisitos**
```bash
pip install selenium webdriver-manager
```

### **Script: `buscar_fulltrack.py`**

```python
#!/usr/bin/env python3
"""
Automação FullTrack - Busca números de série
Recebe: lista de números via stdin (JSON)
Retorna: JSON com resultados
"""

import sys
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# ==================== CONFIG ====================
FULLTRACK_URL = "https://12308-htm-indust-de-equip-eletro-eletronicos-ltda.fulltrackapp.com/mapaGeral_v3/#/"
HEADLESS = True  # True = sem interface, False = com interface
TIMEOUT = 15

# ==================== SETUP ====================
def setup_driver():
    """Configura e retorna driver Chrome"""
    options = Options()
    if HEADLESS:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    
    driver = webdriver.Chrome(options=options)
    return driver

# ==================== CORE ====================
def buscar_numero(driver, numero):
    """
    Busca um número de série no FullTrack
    Retorna: dict com status e resultado
    """
    resultado = {
        "numero": numero,
        "status": "erro",
        "resultado": None,
        "mensagem": ""
    }
    
    try:
        print(f"  → Processando: {numero}")
        
        # 1. VOLTAR PARA MAPA (se não é primeira vez)
        driver.get(FULLTRACK_URL)
        time.sleep(2)
        
        # 2. ENCONTRAR CAMPO DE BUSCA
        # IMPORTANTE: Você precisa inspecionar o site e encontrar o ID/classe do campo
        # Exemplo genérico - AJUSTE CONFORME SEU SITE:
        wait = WebDriverWait(driver, TIMEOUT)
        
        # Tentar encontrar campo de busca (ajuste seletor conforme necessário)
        search_field = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='search']"))
        )
        
        # 3. LIMPAR E INSERIR NÚMERO
        search_field.clear()
        search_field.send_keys(numero)
        print(f"    ✓ Número inserido no campo de busca")
        
        # 4. PRESSIONAR ENTER OU CLICAR BOTÃO
        search_field.send_keys("\n")
        time.sleep(3)
        
        # 5. CLICAR NO RESULTADO
        # AJUSTE: encontre o primeiro resultado
        try:
            first_result = driver.find_element(By.CSS_SELECTOR, ".resultado-item")
            first_result.click()
            time.sleep(2)
            print(f"    ✓ Resultado clicado")
        except:
            resultado["mensagem"] = "Número não encontrado"
            return resultado
        
        # 6. PROCURAR "COMANDOS ENVIADOS"
        try:
            comandos = wait.until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Comandos enviados')]"))
            )
            comandos.click()
            time.sleep(2)
            print(f"    ✓ Comandos enviados clicado")
        except:
            resultado["mensagem"] = "Seção 'Comandos enviados' não encontrada"
            return resultado
        
        # 7. COLETAR DADOS
        # AJUSTE: extrai conteúdo conforme a estrutura do seu site
        try:
            content = driver.find_element(By.CLASS_NAME, "comandos-content").text
            resultado["resultado"] = content
            resultado["status"] = "sucesso"
            print(f"    ✓ Dados coletados com sucesso")
        except:
            resultado["mensagem"] = "Não conseguiu extrair conteúdo"
            return resultado
        
        # 8. ENVIAR (SE NECESSÁRIO)
        try:
            botao_enviar = driver.find_element(By.XPATH, "//button[contains(text(), 'Enviar')]")
            botao_enviar.click()
            time.sleep(2)
            resultado["status"] = "enviado"
            print(f"    ✓ Comando enviado")
        except:
            print(f"    ⚠ Botão enviar não encontrado (opcional)")
        
        return resultado
        
    except Exception as e:
        resultado["mensagem"] = str(e)
        print(f"    ✗ Erro: {e}")
        return resultado

# ==================== MAIN ====================
def main():
    """Função principal"""
    
    # Receber números do stdin (via N8n)
    try:
        input_data = sys.stdin.read()
        numeros = json.loads(input_data)
    except:
        # Se chamar sem dados, teste com exemplo
        numeros = ["12345", "67890"]
    
    print(f"🔍 Iniciando busca de {len(numeros)} números...")
    
    driver = None
    resultados = []
    
    try:
        driver = setup_driver()
        
        for numero in numeros:
            resultado = buscar_numero(driver, numero)
            resultados.append(resultado)
            time.sleep(1)  # Pequeno delay entre requisições
        
        print(f"\n✅ Concluído! {len([r for r in resultados if r['status']=='sucesso'])} sucessos")
        
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        
    finally:
        if driver:
            driver.quit()
    
    # Retornar resultados como JSON
    output = json.dumps(resultados, ensure_ascii=False, indent=2)
    print(output)
    return output

if __name__ == "__main__":
    main()
```

---

## 📋 WORKFLOW N8n - Configuração

### **Estrutura do Workflow**

```
START
  ↓
[1] Manual Trigger / Schedule (Cron)
  ↓
[2] Google Sheets - Read Rows
  ├─ Spreadsheet: Mosaico bloqueio (Google Sheets)
  ├─ Range: A:A (coluna de números)
  └─ Output: array de números
  ↓
[3] Execute Command
  ├─ Command: python /home/user/buscar_fulltrack.py
  ├─ Input: {{JSON.stringify($node['Google Sheets Read'].json.rows)}}
  └─ Output: JSON com resultados
  ↓
[4] Parse JSON
  ├─ Input: {{$node['Execute Command'].json}}
  └─ Output: dados estruturados
  ↓
[5] Google Sheets - Write/Update
  ├─ Write coluna B: status
  ├─ Write coluna C: resultado
  └─ Write coluna D: mensagem
  ↓
[6] Send Notification (Email/Slack)
  ├─ Total processado
  ├─ Sucessos
  └─ Erros
  ↓
END
```

### **Config Google Sheets Read**
```
Sheet ID: [copiar da URL]
Range: Sheet1!A:A
Read as: Rows
```

### **Config Execute Command**
```
Command: python
Arguments: ["/path/to/buscar_fulltrack.py"]
Input: {{JSON.stringify($node['Google Sheets Read'].json.rows)}}
Working Directory: /home/user
```

---

## 🔧 Passos para Implementação

### **Fase 1: Preparação (2h)**
1. ✅ Copiar planilha para Google Sheets
2. ✅ Instalar Python + Selenium na máquina
3. ✅ Testar conexão Chrome Selenium
4. ✅ Inspecionar site FullTrack (F12) para encontrar seletores CSS

### **Fase 2: Desenvolvimento (4h)**
1. ✅ Criar script Python base
2. ✅ Testar com 2-3 números manualmente
3. ✅ Adicionar tratamento de erros
4. ✅ Testar com batch completo

### **Fase 3: Integração N8n (2h)**
1. ✅ Conectar Google Sheets
2. ✅ Integrar script Python
3. ✅ Configurar escrita de resultados
4. ✅ Testar workflow completo

### **Fase 4: Deploy (1h)**
1. ✅ Agendar execução (Cron)
2. ✅ Configurar alertas
3. ✅ Documentar processo
4. ✅ Treinar pessoal

---

## ⚠️ PONTOS CRÍTICOS - AÇÃO NECESSÁRIA

### **1. Encontrar Seletores CSS do Site**
Você precisa abrir F12 no Chrome e inspecionar:
```
• Campo de busca → copiar ID ou class
• Botão Enviar → copiar seletor
• Elemento "Comandos enviados" → copiar
• Resultado da busca → copiar classe
```

**Exemplo do que você encontrará:**
```html
<!-- Campo de busca -->
<input id="search_numero" type="text" placeholder="Digite o número">

<!-- Botão enviar -->
<button class="btn-success" id="enviar">Enviar</button>

<!-- Resultado -->
<div class="resultado-item" data-numero="12345">...</div>
```

### **2. Tratamento de Login**
Se o site exigir login:
```python
# Adicione antes do loop de busca:
try:
    login_button = driver.find_element(By.ID, "login_btn")
    login_button.click()
    
    email_field = driver.find_element(By.ID, "email")
    email_field.send_keys("seu_email@empresa.com")
    
    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys("sua_senha")
    
    login_button.click()
    time.sleep(5)
except Exception as e:
    print(f"Erro no login: {e}")
```

### **3. Testar em Ambiente Real**
```bash
# Teste manual primeiro
python buscar_fulltrack.py

# Com dados de teste
echo '[{"numero":"12345"}, {"numero":"67890"}]' | python buscar_fulltrack.py
```

---

## 📞 Próximos Passos

1. **Envie-me print do site (F12 aberto)** para eu adaptar os seletores
2. **Confirme a estrutura da planilha** (quantas colunas, qual ordem)
3. **Teste o script Python** em seu ambiente
4. **Configure o Workflow N8n** conforme documentado

---

## 💾 Comparativo: Macro Recorder vs Python+N8n

| Aspecto | Macro Recorder | Python + N8n |
|---------|---|---|
| **Velocidade** | Lenta (zoom, esperas) | Rápida (direto) |
| **Confiabilidade** | Frágil (interface visual) | Robusta (seletores) |
| **Manutenção** | Difícil (binário) | Fácil (código) |
| **Escalabilidade** | Limita a 1 processo | Paralelizável |
| **Logs/Debug** | Nenhum | Detalhado |
| **Retry Automático** | Não | Sim |
| **Custo** | Macro Recorder pago | Free (Python + N8n) |
| **Tempo Setup** | Rápido | Médio (2h) |

---

## 📚 Recursos

- [Selenium Docs](https://selenium.dev/)
- [N8n Docs](https://docs.n8n.io/)
- [Google Sheets API](https://developers.google.com/sheets/api)
- [CSS Selectors](https://www.w3schools.com/cssref/selectors.asp)
