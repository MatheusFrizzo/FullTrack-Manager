#!/usr/bin/env python3
"""
╔════════════════════════════════════════════════════════════════╗
║          AUTOMAÇÃO FULLTRACK - BUSCA DE NÚMEROS               ║
║                                                                ║
║  Recebe: JSON com lista de números via stdin                  ║
║  Processa: Busca cada número no FullTrack                     ║
║  Retorna: JSON com resultados (status, resultado, mensagem)   ║
║                                                                ║
║  Uso:                                                          ║
║    python buscar_fulltrack.py < numeros.json                  ║
║    echo '[{"numero":"12345"}]' | python buscar_fulltrack.py   ║
╚════════════════════════════════════════════════════════════════╝
"""

import sys
import json
import time
import logging
from typing import Dict, List, Any
from datetime import datetime

# Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, 
    StaleElementReferenceException, WebDriverException
)

# ============================================================================
# CONFIG
# ============================================================================

CONFIG = {
    "FULLTRACK_URL": "https://12308-htm-indust-de-equip-eletro-eletronicos-ltda.fulltrackapp.com/mapaGeral_v3/#/",
    "HEADLESS": True,  # False = com interface (debug), True = sem interface
    "TIMEOUT": 20,
    "DELAY_AFTER_CLICK": 2,
    "DELAY_BETWEEN_SEARCHES": 1,
    "MAX_RETRIES": 2,
    "LOG_LEVEL": "INFO",
    
    # SELETORES CSS/XPATH - AJUSTE CONFORME SEU SITE
    # Use F12 no Chrome para inspecionar e encontrar os valores corretos
    "SELECTORS": {
        "search_field": "input[type='search']",  # ⚠️ AJUSTAR
        "search_button": "button[type='submit']",  # ⚠️ AJUSTAR
        "first_result": ".resultado-item",  # ⚠️ AJUSTAR
        "comandos_text": "Comandos enviados",  # ⚠️ AJUSTAR
        "send_button": "//button[contains(text(), 'Enviar')]",  # ⚠️ AJUSTAR
    }
}

# ============================================================================
# LOGGING
# ============================================================================

def setup_logging():
    """Configura logger"""
    logging.basicConfig(
        level=getattr(logging, CONFIG["LOG_LEVEL"]),
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================================================
# DRIVER SETUP
# ============================================================================

def setup_driver() -> webdriver.Chrome:
    """
    Configura e retorna driver Chrome com opções otimizadas
    """
    logger.info("🚀 Iniciando driver Chrome...")
    
    options = Options()
    
    # Modo headless (sem interface visual)
    if CONFIG["HEADLESS"]:
        options.add_argument("--headless")
        logger.info("  → Modo headless ativado")
    
    # Otimizações
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # User agent para parecer um navegador real
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    try:
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        logger.info("✅ Driver Chrome inicializado com sucesso")
        return driver
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar driver: {e}")
        sys.exit(1)

# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def wait_for_element(driver, by: By, value: str, timeout: int = None) -> bool:
    """
    Aguarda elemento aparecer na página
    """
    if timeout is None:
        timeout = CONFIG["TIMEOUT"]
    
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return True
    except TimeoutException:
        return False

def find_element_safe(driver, by: By, value: str):
    """
    Procura elemento com tratamento de erro
    """
    try:
        return driver.find_element(by, value)
    except NoSuchElementException:
        return None

def buscar_numero(driver, numero: str) -> Dict[str, Any]:
    """
    Busca um número de série no FullTrack
    
    Retorna:
        Dict com: {
            "numero": str,
            "status": "sucesso" | "erro" | "nao_encontrado",
            "resultado": str | None,
            "mensagem": str,
            "timestamp": str
        }
    """
    resultado = {
        "numero": numero,
        "status": "erro",
        "resultado": None,
        "mensagem": "",
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        logger.info(f"⏱️  Processando número: {numero}")
        
        # ================== STEP 1: Ir para página inicial ==================
        logger.debug(f"  1/7 - Acessando URL: {CONFIG['FULLTRACK_URL']}")
        driver.get(CONFIG['FULLTRACK_URL'])
        time.sleep(CONFIG['DELAY_AFTER_CLICK'])
        
        # ================== STEP 2: Encontrar campo de busca ==================
        logger.debug(f"  2/7 - Procurando campo de busca...")
        
        search_field = wait_for_element(
            driver, By.CSS_SELECTOR, 
            CONFIG["SELECTORS"]["search_field"]
        )
        
        if not search_field:
            # Tentar alternativas
            search_field = find_element_safe(
                driver, By.XPATH,
                "//input[@type='text' or @type='search']"
            )
        
        if not search_field:
            resultado["mensagem"] = "Campo de busca não encontrado"
            logger.warning(f"  ⚠️  Campo de busca não encontrado para {numero}")
            return resultado
        
        # ================== STEP 3: Inserir número ==================
        logger.debug(f"  3/7 - Inserindo número no campo...")
        search_field.clear()
        search_field.send_keys(numero)
        logger.info(f"  ✓ Número '{numero}' inserido no campo")
        
        time.sleep(CONFIG['DELAY_BETWEEN_SEARCHES'])
        
        # ================== STEP 4: Enviar busca ==================
        logger.debug(f"  4/7 - Enviando busca...")
        search_field.send_keys(Keys.RETURN)
        
        time.sleep(CONFIG['DELAY_AFTER_CLICK'])
        
        # ================== STEP 5: Clicar no resultado ==================
        logger.debug(f"  5/7 - Clicando no resultado...")
        
        first_result = find_element_safe(
            driver, By.CSS_SELECTOR,
            CONFIG["SELECTORS"]["first_result"]
        )
        
        if not first_result:
            resultado["status"] = "nao_encontrado"
            resultado["mensagem"] = f"Número '{numero}' não encontrado no sistema"
            logger.warning(f"  ✗ Número não encontrado: {numero}")
            return resultado
        
        first_result.click()
        logger.info(f"  ✓ Resultado clicado")
        
        time.sleep(CONFIG['DELAY_AFTER_CLICK'])
        
        # ================== STEP 6: Procurar "Comandos enviados" ==================
        logger.debug(f"  6/7 - Procurando 'Comandos enviados'...")
        
        try:
            comandos_link = WebDriverWait(driver, CONFIG["TIMEOUT"]).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    f"//*[contains(text(), '{CONFIG['SELECTORS']['comandos_text']}')]"
                ))
            )
            comandos_link.click()
            logger.info(f"  ✓ 'Comandos enviados' clicado")
            
            time.sleep(CONFIG['DELAY_AFTER_CLICK'])
        except TimeoutException:
            resultado["mensagem"] = "Seção 'Comandos enviados' não encontrada"
            logger.warning(f"  ⚠️  'Comandos enviados' não encontrado para {numero}")
            return resultado
        
        # ================== STEP 7: Coletar dados ==================
        logger.debug(f"  7/7 - Coletando dados...")
        
        # Tentar extrair conteúdo (ajuste conforme estrutura do seu site)
        content = None
        
        # Opção 1: Por classe
        content_elem = find_element_safe(driver, By.CLASS_NAME, "comandos-content")
        if content_elem:
            content = content_elem.text
        
        # Opção 2: Por ID
        if not content:
            content_elem = find_element_safe(driver, By.ID, "comandos-data")
            if content_elem:
                content = content_elem.text
        
        # Opção 3: Conteúdo geral da página
        if not content:
            content = driver.find_element(By.TAG_NAME, "body").text[:500]
        
        if content:
            resultado["resultado"] = content
            resultado["status"] = "sucesso"
            logger.info(f"  ✓ Dados coletados com sucesso")
        else:
            resultado["mensagem"] = "Não conseguiu extrair conteúdo da página"
            logger.warning(f"  ⚠️  Não conseguiu extrair conteúdo para {numero}")
            return resultado
        
        # ================== BONUS: Enviar comando ==================
        logger.debug(f"  BONUS - Tentando enviar comando...")
        
        try:
            send_button = find_element_safe(
                driver, By.XPATH,
                CONFIG["SELECTORS"]["send_button"]
            )
            
            if send_button:
                send_button.click()
                resultado["status"] = "enviado"
                logger.info(f"  ✓ Comando enviado com sucesso")
                time.sleep(2)
            else:
                logger.debug(f"  - Botão 'Enviar' não encontrado (opcional)")
        except Exception as e:
            logger.debug(f"  - Erro ao enviar: {e}")
        
        return resultado
        
    except StaleElementReferenceException:
        resultado["mensagem"] = "Elemento desapareceu durante processamento (stale element)"
        logger.warning(f"  ⚠️  Stale element para {numero}")
        return resultado
        
    except WebDriverException as e:
        resultado["mensagem"] = f"Erro do driver: {str(e)[:100]}"
        logger.error(f"  ✗ Erro do Selenium para {numero}: {e}")
        return resultado
        
    except Exception as e:
        resultado["mensagem"] = f"Erro inesperado: {str(e)[:100]}"
        logger.error(f"  ✗ Erro inesperado para {numero}: {e}")
        return resultado

# ============================================================================
# PROCESSAMENTO EM BATCH
# ============================================================================

def processar_numeros(driver, numeros: List[str]) -> List[Dict[str, Any]]:
    """
    Processa lista de números e retorna resultados
    """
    resultados = []
    total = len(numeros)
    
    logger.info(f"📊 Iniciando processamento de {total} número(s)...")
    logger.info("=" * 70)
    
    for i, numero in enumerate(numeros, 1):
        logger.info(f"[{i}/{total}] Processando...")
        
        resultado = buscar_numero(driver, numero)
        resultados.append(resultado)
        
        # Delay entre requisições
        if i < total:
            time.sleep(CONFIG['DELAY_BETWEEN_SEARCHES'])
    
    logger.info("=" * 70)
    
    # Estatísticas
    sucessos = len([r for r in resultados if r["status"] == "sucesso"])
    erros = len([r for r in resultados if r["status"] == "erro"])
    nao_encontrados = len([r for r in resultados if r["status"] == "nao_encontrado"])
    
    logger.info(f"📈 RESUMO:")
    logger.info(f"   ✓ Sucessos: {sucessos}/{total}")
    logger.info(f"   ✗ Erros: {erros}/{total}")
    logger.info(f"   ⚠️  Não encontrados: {nao_encontrados}/{total}")
    
    return resultados

# ============================================================================
# ENTRADA/SAÍDA
# ============================================================================

def processar_entrada() -> List[str]:
    """
    Processa entrada de números (stdin ou argumento)
    
    Formatos aceitos:
    - JSON: [{"numero":"12345"}, {"numero":"67890"}]
    - JSON simples: ["12345", "67890"]
    - Uma por linha: 12345\n67890
    """
    
    # Tentar ler de stdin
    try:
        input_data = sys.stdin.read().strip()
        
        if not input_data:
            logger.warning("⚠️  Nenhuma entrada recebida. Usando dados de teste...")
            return ["12345", "67890"]  # Dados de teste
        
        # Tentar JSON
        try:
            data = json.loads(input_data)
            
            # Se for lista de dicts
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], dict):
                    return [str(item.get("numero", "")) for item in data]
                else:
                    return [str(item) for item in data]
        except json.JSONDecodeError:
            pass
        
        # Se for uma por linha
        if '\n' in input_data:
            return [line.strip() for line in input_data.split('\n') if line.strip()]
        
        # Uma linha só
        return [input_data]
    
    except Exception as e:
        logger.warning(f"⚠️  Erro ao ler entrada: {e}")
        return ["12345"]  # Default

def processar_saida(resultados: List[Dict[str, Any]]):
    """
    Retorna resultados como JSON (stdout)
    """
    output = {
        "timestamp": datetime.now().isoformat(),
        "total": len(resultados),
        "sucessos": len([r for r in resultados if r["status"] == "sucesso"]),
        "erros": len([r for r in resultados if r["status"] == "erro"]),
        "nao_encontrados": len([r for r in resultados if r["status"] == "nao_encontrado"]),
        "resultados": resultados
    }
    
    # Imprimir JSON
    print(json.dumps(output, ensure_ascii=False, indent=2))
    
    return output

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Função principal"""
    
    logger.info("🎯 FullTrack Automação - Iniciando...")
    logger.info(f"   Headless: {CONFIG['HEADLESS']}")
    logger.info(f"   Timeout: {CONFIG['TIMEOUT']}s")
    
    # Ler entrada
    numeros = processar_entrada()
    
    if not numeros or not any(numeros):
        logger.error("❌ Nenhum número fornecido")
        sys.exit(1)
    
    logger.info(f"📥 Números recebidos: {len(numeros)}")
    for num in numeros[:5]:  # Mostrar primeiros 5
        logger.info(f"   • {num}")
    if len(numeros) > 5:
        logger.info(f"   ... e mais {len(numeros) - 5}")
    
    driver = None
    resultados = []
    
    try:
        # Inicializar driver
        driver = setup_driver()
        
        # Processar números
        resultados = processar_numeros(driver, numeros)
        
    except KeyboardInterrupt:
        logger.warning("⚠️  Interrompido pelo usuário")
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)
        
    finally:
        # Limpar
        if driver:
            logger.info("🧹 Fechando driver...")
            driver.quit()
        
        # Retornar resultados
        logger.info("📤 Retornando resultados...")
        processar_saida(resultados)

if __name__ == "__main__":
    main()
