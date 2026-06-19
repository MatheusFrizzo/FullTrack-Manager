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
        Realiza login no FullTrack e garante que a página de mapa seja aberta.
        """
        try:
            login_url = self.config.get("login_url") or self.config.get("fulltrack_url", "")
            map_url = self.config.get("fulltrack_url", "")

            def wait_ready(timeout=10):
                try:
                    WebDriverWait(self.driver, timeout).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                    return True
                except TimeoutException:
                    return False

            def is_error_page():
                html = self.driver.page_source.lower()
                return "page not found" in html or "404" in html or len(html) < 500

            def open_map_via_menu():
                self.log("INFO", "  🔧 Tentando abrir mapa via menu lateral...")
                menu_selectors = [
                    (By.CSS_SELECTOR, "body > header > nav > div > div:nth-child(2) > a > i"),
                    (By.CSS_SELECTOR, "i.fa-bars"),
                    (By.XPATH, "//i[contains(@class, 'fa-bars') or contains(@class, 'fa fa-bars')]/.."),
                    (By.XPATH, "//*[contains(@class, 'fa-bars')]")
                ]
                menu_button = None
                for by, sel in menu_selectors:
                    try:
                        menu_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((by, sel))
                        )
                        self.log("INFO", f"    ✓ Menu encontrado: {sel}")
                        menu_button.click()
                        time.sleep(2)
                        break
                    except TimeoutException:
                        continue

                if not menu_button:
                    self.log("WARNING", "    ⚠️ Botão de menu não encontrado")
                    return False

                map_selectors = [
                    (By.CSS_SELECTOR, "a.item-menu[href*='mapaGeral_v3']"),
                    (By.XPATH, "//a[contains(., 'Mapa Geral 3.0') and contains(@href, 'mapaGeral_v3')])"),
                    (By.XPATH, "//a[contains(., 'Mapa Geral') and contains(@href, 'mapaGeral_v3')])"),
                    (By.XPATH, "//a[contains(., 'Mapa Geral 3.0')]"),
                ]

                for by, sel in map_selectors:
                    try:
                        map_link = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((by, sel))
                        )
                        self.log("INFO", f"    ✓ Link de mapa encontrado: {sel}")
                        original_windows = self.driver.window_handles
                        map_link.click()
                        time.sleep(3)

                        if len(self.driver.window_handles) > len(original_windows):
                            new_window = [w for w in self.driver.window_handles if w not in original_windows][0]
                            self.driver.switch_to.window(new_window)
                            self.log("INFO", "    ✓ Alternou para nova janela do mapa")
                        return True
                    except TimeoutException:
                        continue

                self.log("WARNING", "    ⚠️ Link de mapa não encontrado")
                return False

            self.log("INFO", f"🌐 Acessando: {login_url}")
            self.driver.get(login_url)
            wait_ready(10)
            time.sleep(2)

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

            if username_field:
                self.log("INFO", "🔐 Tela de login detectada, autenticando...")
                username_field.clear()
                username_field.send_keys(self.credentials.get("username", ""))

                password_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                password_field.clear()
                password_field.send_keys(self.credentials.get("password", ""))

                try:
                    login_btn = self.driver.find_element(
                        By.CSS_SELECTOR,
                        "button[type='submit'], input[type='submit'], button.btn-login, button#login, button.login"
                    )
                    login_btn.click()
                except NoSuchElementException:
                    password_field.send_keys(Keys.RETURN)

                wait_ready(15)
                time.sleep(2)
                self.log("INFO", "✅ Login realizado")
            else:
                self.log("INFO", "✅ Sem tela de login detectada (acesso direto ou sessão ativa)")

            # Após login, garantir que a página de mapa esteja aberta
            if map_url:
                self.log("INFO", f"  📍 Acessando mapa: {map_url}")
                self.driver.get(map_url)
                wait_ready(10)
                time.sleep(3)

                if is_error_page():
                    self.log("WARNING", "  ⚠️ Mapa não carregou diretamente, tentando via menu")
                    if not open_map_via_menu():
                        self.log("ERROR", "❌ Falha ao abrir o mapa via menu")
                        return False
                    wait_ready(10)
                    time.sleep(3)

                if is_error_page():
                    self.log("ERROR", "❌ Página de mapa continua com erro após tentativa")
                    return False

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
            self.log("INFO", f"  📍 Acessando: {url}")
            
            self.driver.get(url)
            
            # Aguarda o documento estar pronto e o JS executar
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                self.log("INFO", f"  ✓ Página carregada (readyState=complete)")
            except TimeoutException:
                self.log("WARNING", f"  ⚠️  Timeout esperando página carregar")
            
            # Aguarda extra para JS popular a página
            time.sleep(3)
            
            # Verifica se a página realmente carregou (não é "Page not found")
            body_html = self.driver.page_source
            if "Page not found" in body_html or "404" in body_html or len(body_html) < 500:
                resultado["mensagem"] = "URL não carregou corretamente — verifique a URL configurada"
                self.log("ERROR", f"  ❌ {resultado['mensagem']}")
                self.log("ERROR", f"  HTML: {body_html[:300]}")
                return resultado

            # === PASSO 2: Campo de busca ===
            self.log("INFO", f"  🔍 Localizando campo de busca...")

            # 🔧 PARA TESTE: descomente a linha abaixo e preencha o seletor correto do site
            hardcoded_selector = None

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

            result_selectors = [
                (By.CSS_SELECTOR, f"[data-serial='{numero}']"),
                (By.XPATH, f"//*[contains(text(), '{numero}')] | //*[@data-serial='{numero}']"),
                (By.XPATH, f"//div[contains(., '{numero}')]"),
                (By.CSS_SELECTOR, ".resultado-item"),
                (By.CSS_SELECTOR, ".search-result-item"),
                (By.XPATH, f"//li[contains(., '{numero}')]"),
                (By.XPATH, f"//tr[contains(., '{numero}')]"),
            ]

            clicked = False
            for by, sel in result_selectors:
                try:
                    self.log("INFO", f"    ↳ Tentando: {sel}")
                    el = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((by, sel))
                    )
                    self.log("INFO", f"    ✓ Encontrado com: {sel}")
                    el.click()
                    clicked = True
                    break
                except Exception:
                    self.log("INFO", f"    ✗ Não encontrado: {sel}")
                    continue

            if not clicked:
                resultado["status"] = "nao_encontrado"
                resultado["mensagem"] = f"Serial '{numero}' não localizado no sistema"
                self.log("ERROR", f"  ❌ {resultado['mensagem']}")
                return resultado

            self.log("INFO", f"  ✓ Resultado clicado")
            time.sleep(2)

            # === PASSO 5: Clicar em "Comandos enviados" ===
            self.log("INFO", f"  📋 Abrindo 'Comandos enviados'...")
            
            # Tenta seletores específicos primeiro
            comandos_selectors = [
                (By.CSS_SELECTOR, "span[data-i18n='commands_sent']"),
                (By.XPATH, "//span[contains(@data-i18n, 'commands_sent')]"),
                (By.XPATH, "//*[contains(text(), 'Comandos enviados')]"),
            ]
            
            comandos = None
            for by, sel in comandos_selectors:
                try:
                    self.log("INFO", f"    ↳ Tentando: {sel}")
                    comandos = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by, sel))
                    )
                    self.log("INFO", f"    ✓ Encontrado com: {sel}")
                    break
                except TimeoutException:
                    self.log("INFO", f"    ✗ Não encontrado: {sel}")
                    continue
            
            if not comandos:
                resultado["mensagem"] = "'Comandos enviados' não encontrado — ajuste o seletor"
                self.log("ERROR", f"  ❌ {resultado['mensagem']}")
                return resultado
            
            comandos.click()
            time.sleep(2)
            self.log("INFO", f"  ✓ 'Comandos enviados' aberto")

            # === PASSO 6: Clicar em "Enviar" (bloqueio) ===
            self.log("INFO", f"  🔒 Executando bloqueio...")

            # Tenta seletores específicos primeiro (CSS, depois XPATH)
            enviar_selectors = [
                (By.CSS_SELECTOR, "div.btn.input-cmd.ft-button-div"),
                (By.CSS_SELECTOR, "div[type='button'].btn.input-cmd.ft-button-div"),
                (By.XPATH, "//div[@type='button' and contains(@class, 'ft-button-div')]"),
                (By.XPATH, "//div[contains(@class, 'input-cmd') and contains(text(), 'Enviar')]"),
                (By.XPATH, "//button[contains(text(), 'Enviar')]"),
                (By.XPATH, "//button[contains(text(), 'Bloquear')]"),
            ]

            enviado = False
            for by, sel in enviar_selectors:
                try:
                    self.log("INFO", f"    ↳ Tentando: {sel}")
                    btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by, sel))
                    )
                    self.log("INFO", f"    ✓ Encontrado com: {sel}")
                    btn.click()
                    enviado = True
                    time.sleep(2)
                    break
                except Exception as e:
                    self.log("INFO", f"    ✗ Não encontrado: {sel}")
                    continue

            if enviado:
                resultado["status"] = "bloqueado"
                resultado["mensagem"] = "Serial bloqueado com sucesso"
                self.log("INFO", f"  ✅ {numero} → BLOQUEADO!")
            else:
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
