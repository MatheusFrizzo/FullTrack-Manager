#!/usr/bin/env python3
"""
FullTrack Automation - Selenium Web Scraping

⚠️  SELETORES CSS: Os seletores marcados com '# ⚠️ AJUSTAR' precisam ser
    inspecionados no site real com F12 > DevTools > Inspecionar Elemento.
    O resto da lógica (login, busca, bloqueio) já está implementada.
"""

import time
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


class FullTrackAutomation:
    def __init__(self, config: dict, credentials: dict, log_callback=None):
        self.config = config
        self.credentials = credentials
        self.log = log_callback or (lambda lvl, msg, sid=None: print(f"[{lvl}] {msg}"))
        self.driver = None
        self.wait = None

    # ─── Controle do Navegador ───────────────────────────────────────────────────

    def start(self) -> bool:
        """Inicia o Chrome (headless no Linux)"""
        try:
            self.log("INFO", "🚀 Iniciando navegador Chrome...")

            options = Options()
            if self.config.get("headless", True):
                options.add_argument("--headless=new")
                self.log("INFO", "  → Modo headless ativado")

            # Configurações essenciais para Linux
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument(
                "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(5)
            self.wait = WebDriverWait(self.driver, self.config.get("timeout", 20))

            self.log("INFO", "✅ Navegador Chrome iniciado com sucesso")
            return True

        except Exception as e:
            self.log("ERROR", f"❌ Falha ao iniciar Chrome: {e}")
            self.log("ERROR", "   → Verifique se o ChromeDriver está instalado: sudo apt install chromium-driver")
            return False

    def stop(self):
        """Fecha o navegador"""
        if self.driver:
            try:
                self.driver.quit()
                self.log("INFO", "🧹 Navegador fechado")
            except Exception:
                pass
            self.driver = None

    # ─── Login ───────────────────────────────────────────────────────────────────

    def login(self) -> bool:
        """
        Realiza login no FullTrack.

        ⚠️ AJUSTAR: Se o site tiver uma página de login separada antes de
        acessar o mapa, os seletores abaixo precisam ser inspecionados com F12.
        """
        try:
            url = self.config.get("fulltrack_url", "")
            self.log("INFO", f"🌐 Acessando: {url}")
            self.driver.get(url)
            time.sleep(3)

            # Verifica se há formulário de login na página
            login_selectors = [
                "input[type='email']",
                "input[name='email']",
                "input[name='login']",
                "input[id='email']",
                "input[id='login']",
                "input[placeholder*='e-mail' i]",
                "input[placeholder*='usuário' i]",
                "input[placeholder*='login' i]",
            ]

            username_field = None
            for sel in login_selectors:
                try:
                    username_field = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                    )
                    break
                except TimeoutException:
                    continue

            if not username_field:
                # Sem tela de login detectada — acesso direto
                self.log("INFO", "✅ Sem tela de login (acesso direto ou sessão ativa)")
                return True

            self.log("INFO", "🔐 Tela de login detectada, autenticando...")

            # Preenche usuário
            username_field.clear()
            username_field.send_keys(self.credentials.get("username", ""))

            # ⚠️ AJUSTAR: seletor do campo senha
            password_field = self.driver.find_element(
                By.CSS_SELECTOR, "input[type='password']"
            )
            password_field.clear()
            password_field.send_keys(self.credentials.get("password", ""))

            # ⚠️ AJUSTAR: seletor do botão de login
            try:
                login_btn = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "button[type='submit'], input[type='submit'], button.btn-login, button#login, button.login"
                )
                login_btn.click()
            except NoSuchElementException:
                password_field.send_keys(Keys.RETURN)

            time.sleep(5)
            self.log("INFO", "✅ Login realizado")
            return True

        except Exception as e:
            self.log("ERROR", f"❌ Erro no login: {e}")
            return False

    # ─── Bloqueio de Serial ──────────────────────────────────────────────────────

    def bloquear_serial(self, numero: str) -> dict:
        """
        Busca e bloqueia um número de série no FullTrack.

        Fluxo:
          1. Acessa o mapa
          2. Digita o serial no campo de busca + ENTER
          3. Clica no resultado encontrado
          4. Clica em "Comandos enviados"
          5. Clica em "Enviar" (executa o bloqueio)

        ⚠️ AJUSTAR: Os seletores CSS/XPATH precisam ser validados com F12
        no site real. Os seletores genéricos abaixo tentam cobrir casos comuns.
        """
        resultado = {
            "numero": numero,
            "status": "erro",
            "mensagem": "",
            "resultado": "",
        }

        try:
            self.log("INFO", f"⏱️  Processando: {numero}")

            # === PASSO 1: Voltar ao mapa ===
            url = self.config.get("fulltrack_url", "")
            self.driver.get(url)
            time.sleep(2)

            # === PASSO 2: Campo de busca ===
            self.log("INFO", f"  🔍 Localizando campo de busca...")

            # 🔧 PARA TESTE: descomente a linha abaixo e preencha o seletor correto do site
            hardcoded_selector = "#sidebar-component > div.sc-kNecGe.bIRPZc > div > div.sc-hOynoF.gNXSOi > input[type=text]"

            # ⚠️ AJUSTAR: adicione o seletor real como primeiro da lista
            search_selectors = []
            if hardcoded_selector:
                search_selectors.append(hardcoded_selector)
                self.log("INFO", f"    (HARDCODED: {hardcoded_selector})")
            
            configured_selector = self.config.get("search_selector", "")
            if configured_selector:
                search_selectors.append(configured_selector)
                self.log("INFO", f"    (configurado: {configured_selector})")

            search_selectors.extend([
                "input[type='search']",
                "input[placeholder*='buscar' i]",
                "input[placeholder*='serial' i]",
                "input[placeholder*='número' i]",
                "input[placeholder*='pesquisar' i]",
                "#busca",
                "#search",
                ".search-input",
                ".input-busca",
            ])

            search_field = None
            for sel in search_selectors:
                try:
                    self.log("INFO", f"    ↳ Tentando: {sel}")
                    # Primeiro tenta ser clickable (espera 3s)
                    try:
                        search_field = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                        )
                        self.log("INFO", f"    ✓ Seletor encontrado (clickable): {sel}")
                        break
                    except TimeoutException:
                        # Se não for clickable, apenas verifica presença (espera 5s total)
                        search_field = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        self.log("INFO", f"    ✓ Seletor encontrado (presente): {sel}")
                        break
                except TimeoutException:
                    self.log("INFO", f"    ✗ Seletor não encontrado: {sel}")
                    continue

            if not search_field:
                sels_tried = "\n    ".join(search_selectors)
                resultado["mensagem"] = "Campo de busca não encontrado — ajuste o seletor CSS"
                self.log("ERROR", f"  ❌ {resultado['mensagem']}")
                self.log("WARNING", f"  Seletores testados:\n    {sels_tried}")
                
                # Log do HTML para debug
                try:
                    html_snippet = self.driver.page_source[:2000]
                    self.log("INFO", f"  HTML da página (primeiros 2000 chars):\n{html_snippet}")
                except:
                    pass
                
                return resultado

            # === PASSO 3: Digitar e buscar ===
            search_field.clear()
            search_field.send_keys(numero)
            time.sleep(0.5)
            search_field.send_keys(Keys.RETURN)
            time.sleep(self.config.get("delay_between", 2))
            self.log("INFO", f"  📝 Número '{numero}' inserido e busca enviada")

            # === PASSO 4: Clicar no resultado ===
            self.log("INFO", f"  👆 Aguardando resultado...")

            # ⚠️ AJUSTAR: seletor do resultado da busca no mapa
            result_selectors_css = [
                ".resultado-item",
                ".search-result-item",
                ".device-result",
                ".asset-item",
                "[data-serial]",
                ".list-group-item",
            ]
            result_selectors_xpath = [
                f"//*[contains(text(), '{numero}')]",
                f"//li[contains(., '{numero}')]",
                f"//tr[contains(., '{numero}')]",
            ]

            clicked = False
            for sel in result_selectors_css:
                try:
                    el = WebDriverWait(self.driver, 4).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    el.click()
                    clicked = True
                    break
                except Exception:
                    continue

            if not clicked:
                for xp in result_selectors_xpath:
                    try:
                        el = WebDriverWait(self.driver, 4).until(
                            EC.element_to_be_clickable((By.XPATH, xp))
                        )
                        el.click()
                        clicked = True
                        break
                    except Exception:
                        continue

            if not clicked:
                resultado["status"] = "nao_encontrado"
                resultado["mensagem"] = f"Serial '{numero}' não localizado no sistema"
                self.log("WARNING", f"  ⚠️  {resultado['mensagem']}")
                return resultado

            self.log("INFO", f"  ✓ Resultado clicado")
            time.sleep(2)

            # === PASSO 5: Clicar em "Comandos enviados" ===
            self.log("INFO", f"  📋 Abrindo 'Comandos enviados'...")
            try:
                comandos = WebDriverWait(self.driver, self.config.get("timeout", 20)).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//*[contains(text(), 'Comandos enviados') or "
                        "contains(text(), 'Comandos Enviados') or "
                        "contains(text(), 'comandos enviados')]"
                    ))
                )
                comandos.click()
                time.sleep(2)
                self.log("INFO", f"  ✓ 'Comandos enviados' aberto")

            except TimeoutException:
                resultado["mensagem"] = "'Comandos enviados' não encontrado — ajuste o seletor XPATH"
                self.log("ERROR", f"  ❌ {resultado['mensagem']}")
                return resultado

            # === PASSO 6: Clicar em "Enviar" (bloqueio) ===
            self.log("INFO", f"  🔒 Executando bloqueio...")

            # ⚠️ AJUSTAR: seletor do botão de enviar/bloquear
            enviar_xpaths = [
                "//button[contains(text(), 'Enviar')]",
                "//button[contains(text(), 'Bloquear')]",
                "//input[@value='Enviar']",
                "//input[@value='Bloquear']",
                "//a[contains(text(), 'Enviar')]",
            ]

            enviado = False
            for xp in enviar_xpaths:
                try:
                    btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xp))
                    )
                    btn.click()
                    enviado = True
                    time.sleep(2)
                    break
                except Exception:
                    continue

            if enviado:
                resultado["status"] = "bloqueado"
                resultado["mensagem"] = "Serial bloqueado com sucesso"
                self.log("INFO", f"  ✅ {numero} → BLOQUEADO!")
            else:
                # Coleta texto da página como evidência
                try:
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text[:300]
                    resultado["resultado"] = body_text
                except Exception:
                    pass
                resultado["status"] = "sucesso"
                resultado["mensagem"] = "Processado (botão Enviar não localizado — ajuste o seletor)"
                self.log("WARNING", f"  ⚠️  {numero}: Botão 'Enviar' não encontrado")

            return resultado

        except StaleElementReferenceException:
            resultado["mensagem"] = "Elemento desapareceu durante o processamento (stale element)"
            self.log("WARNING", f"  ⚠️  {resultado['mensagem']}")
            return resultado

        except WebDriverException as e:
            resultado["mensagem"] = f"Erro do Chrome: {str(e)[:120]}"
            self.log("ERROR", f"  ❌ {resultado['mensagem']}")
            return resultado

        except Exception as e:
            resultado["mensagem"] = f"Erro inesperado: {str(e)[:120]}"
            self.log("ERROR", f"  ❌ {resultado['mensagem']}")
            return resultado
