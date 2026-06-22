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

    def _save_debug_html(self, name_prefix: str = "map_debug"):
        try:
            html = self.driver.page_source
            url = self.driver.current_url
            cookies = self.driver.get_cookies()
            fname = f"debug_{name_prefix}_{int(time.time())}.html"
            with open(fname, "w", encoding="utf-8") as f:
                f.write(f"<!-- URL: {url} -->\n<!-- COOKIES: {cookies} -->\n")
                f.write(html)
            self.log("INFO", f"  ✓ Debug HTML salvo: {fname}")
        except Exception as e:
            self.log("ERROR", f"  ❌ Falha ao salvar debug HTML: {e}")

    def _is_error_page(self) -> bool:
        """Verifica se a página atual é um erro 404 ou página não encontrada de forma robusta"""
        try:
            title = (self.driver.title or "").lower()
            if "404" in title or "not found" in title:
                return True
            body = self.driver.find_elements(By.TAG_NAME, "body")
            if body:
                body_text = body[0].text.lower()
                if "page not found" in body_text:
                    return True
            if len(self.driver.page_source) < 500:
                return True
        except Exception:
            pass
        return False

    # ─── Login ───────────────────────────────────────────────────────────────────

    def login(self) -> bool:
        """
        Realiza login no FullTrack.
        """
        try:
            login_url = self.config.get("login_url") or self.config.get("fulltrack_url", "")

            def wait_ready(timeout=10):
                try:
                    WebDriverWait(self.driver, timeout).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                    return True
                except TimeoutException:
                    return False

            self.log("INFO", f"🌐 Acessando: {login_url}")
            self.driver.get(login_url)
            wait_ready(10)
            time.sleep(2)

            # Verifica se há formulário de login na página
            login_selectors = [
                "input[type='email']",
                "input[type='text'][placeholder*='e-mail' i]",
                "input[type='text'][placeholder*='usuário' i]",
                "input[type='text'][placeholder*='login' i]",
                "input[name='email']",
                "input[name='login']",
                "input[name='usuario']",
                "input[name='user']",
                "input[id='email']",
                "input[id='login']",
                "input[id='usuario']",
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
                        "button[type='submit'], input[type='submit'], button.btn-login, button#login, button.login, button[name='login'], button[name='entrar'], input[type='button']"
                    )
                    login_btn.click()
                except NoSuchElementException:
                    password_field.send_keys(Keys.RETURN)

                wait_ready(15)
                time.sleep(2)
                self.log("INFO", "✅ Login realizado")
            else:
                self.log("INFO", "✅ Sem tela de login detectada (acesso direto ou sessão ativa)")

            return True

        except Exception as e:
            self.log("ERROR", f"❌ Erro no login: {e}")
            return False

    def open_map_via_menu(self) -> bool:
        self.log("INFO", "  🔧 Tentando abrir mapa via menu lateral...")
        # Primeiro, tente localizar diretamente o link do menu "Mapa Geral 3.0" (não precisa do botão hamburguer)
        direct_map_selectors = [
            (By.CSS_SELECTOR, "a.item-menu[href*='mapaGeral_v3']"),
            (By.CSS_SELECTOR, "a[href*='mapaGeral_v3']"),
            (By.XPATH, "//a[contains(normalize-space(), 'Mapa Geral') and contains(@href, 'mapaGeral_v3')]")
        ]

        for by, sel in direct_map_selectors:
            try:
                map_link = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((by, sel))
                )
                self.log("INFO", f"    ✓ Link de mapa direto encontrado: {sel}")
                try:
                    href = map_link.get_attribute('href')
                    if href:
                        self.driver.get(href)
                        time.sleep(2)
                        return True
                except Exception:
                    try:
                        map_link.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", map_link)
                    time.sleep(2)
                    return True
            except TimeoutException:
                continue

        menu_selectors = [
            (By.XPATH, "//nav//button[contains(@class, 'menu') or contains(@aria-label, 'menu') or contains(@aria-label, 'Menu')]"),
            (By.XPATH, "//header//button[contains(@class, 'toggle') or contains(@class, 'hamburger')]"),
            (By.CSS_SELECTOR, "header button.menu-toggle, header button.hamburger, nav button"),
            (By.XPATH, "//button[.//i[contains(@class, 'fa-bars')]]"),
            (By.CSS_SELECTOR, "button.menu-toggle, button.menu-btn, button.menu-button, .sidebar-toggle, .navbar-toggler, .btn-menu"),
            (By.CSS_SELECTOR, "i.fa-bars, i.fas.fa-bars, span.menu-icon, .menu-icon"),
            (By.XPATH, "//button[contains(@class, 'menu') or contains(@class, 'toggle') or contains(@aria-label, 'Menu') or contains(@aria-label, 'menu')]"),
            (By.XPATH, "//*[contains(@class, 'fa-bars') or contains(@class, 'menu-toggle') or contains(@class, 'sidebar-toggle')]")
        ]

        menu_button = None
        for by, sel in menu_selectors:
            try:
                menu_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((by, sel))
                )
                self.log("INFO", f"    ✓ Menu encontrado: {sel}")
                try:
                    menu_button.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", menu_button)
                time.sleep(2)
                break
            except TimeoutException:
                continue

        if not menu_button:
            self.log("WARNING", "    ⚠️ Botão de menu não encontrado")
            try:
                header_html = self.driver.find_element(By.TAG_NAME, "header").get_attribute("outerHTML")[:1000]
                self.log("DEBUG", f"  Header HTML: {header_html}")
            except Exception:
                pass
            # Mesmo sem botão, ainda podemos ter o link direto em algum lugar do DOM (tentar novamente buscando anchors)
            try:
                map_link = self.driver.find_element(By.CSS_SELECTOR, "a[href*='mapaGeral_v3']")
                href = map_link.get_attribute('href')
                if href:
                    self.log("INFO", f"    ✓ Link de mapa encontrado no DOM: {href}")
                    self.driver.get(href)
                    time.sleep(2)
                    return True
            except Exception:
                pass
            return False

        map_selectors = [
            (By.CSS_SELECTOR, "a[href*='mapaGeral_v3']"),
            (By.CSS_SELECTOR, "a[href*='mapaGeral_v3'] span, a[href*='mapaGeral_v3'] div"),
            (By.XPATH, "//a[contains(normalize-space(), 'Mapa Geral 3.0') and contains(@href, 'mapaGeral_v3')]") ,
            (By.XPATH, "//a[contains(normalize-space(), 'Mapa Geral') and contains(@href, 'mapaGeral_v3')]") ,
            (By.XPATH, "//a[contains(normalize-space(), 'Mapa Geral 3.0') or contains(normalize-space(), 'Mapa Geral')]") ,
            (By.XPATH, "//li[normalize-space() = 'Mapa Geral 3.0' or contains(normalize-space(), 'Mapa Geral')]/a"),
            (By.XPATH, "//div[contains(., 'Mapa Geral 3.0') and (contains(@class, 'menu') or contains(@class, 'sidebar'))]"),
        ]

        for by, sel in map_selectors:
            try:
                map_link = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((by, sel))
                )
                self.log("INFO", f"    ✓ Link de mapa encontrado: {sel}")
                # Set Referer header to improve server-side routing for SPA
                try:
                    referer = self.config.get('login_url') or self.config.get('fulltrack_url')
                    if referer:
                        self.driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', { 'headers': {'referer': referer} })
                except Exception:
                    pass

                href = None
                try:
                    href = map_link.get_attribute('href')
                except Exception:
                    href = None

                # Try opening in a new window (simulates user clicking a link with target=_blank)
                try:
                    if href:
                        self.driver.execute_script("window.open(arguments[0], '_blank');", href)
                    else:
                        try:
                            map_link.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", map_link)

                    time.sleep(1)
                    new_windows = [w for w in self.driver.window_handles if w != self.driver.current_window_handle]
                    if new_windows:
                        self.driver.switch_to.window(new_windows[-1])
                        self.log("INFO", "    ✓ Alternou para nova janela do mapa")
                    else:
                        # If no new window appeared, ensure we're on the href
                        if href:
                            self.driver.get(href)

                except Exception:
                    # fallback to click
                    try:
                        map_link.click()
                    except Exception:
                        try:
                            self.driver.execute_script("arguments[0].click();", map_link)
                        except Exception:
                            pass

                # Aguarda por indicadores do mapa (containers típicos) por até 20s
                try:
                    WebDriverWait(self.driver, 20).until(
                        lambda d: d.find_elements(By.CSS_SELECTOR, "div.leaflet-container, .ol-viewport, #map, .mapboxgl-canvas, .map-container")
                    )
                    self.log("INFO", "    ✓ Indicador de mapa detectado")
                    return True
                except TimeoutException:
                    time.sleep(2)
                    return True
            except TimeoutException:
                continue

        self.log("WARNING", "    ⚠️ Link de mapa não encontrado")
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
            self.log("INFO", "  🌐 Tentando abrir o mapa via menu primeiro...")
            opened = self.open_map_via_menu()
            if not opened:
                if not url:
                    resultado["mensagem"] = "Nenhuma URL de mapa configurada e o menu não foi encontrado"
                    self.log("ERROR", f"  ❌ {resultado['mensagem']}")
                    return resultado

                self.log("INFO", f"  🔗 Abrindo mapa diretamente: {url}")
                self.driver.get(url)
                try:
                    WebDriverWait(self.driver, 10).until(
                        lambda driver: driver.execute_script("return document.readyState") == "complete"
                    )
                    self.log("INFO", f"  ✓ Página carregada (readyState=complete)")
                except TimeoutException:
                    self.log("WARNING", "  ⚠️ Timeout esperando página carregar")
                time.sleep(3)

                body_html = self.driver.page_source.lower()
                if self._is_error_page():
                    self.log("WARNING", "  ⚠️ Falha ao abrir o mapa direto; tentando via menu")
                    if not self.open_map_via_menu():
                        resultado["mensagem"] = "URL não carregou corretamente — verifique a URL configurada ou o menu de navegação"
                        self.log("ERROR", f"  ❌ {resultado['mensagem']}")
                        self.log("ERROR", f"  HTML: {body_html[:300]}")
                        try:
                            self._save_debug_html('direct_fail')
                        except Exception:
                            pass
                        return resultado
                    try:
                        WebDriverWait(self.driver, 10).until(
                            lambda driver: driver.execute_script("return document.readyState") == "complete"
                        )
                    except TimeoutException:
                        self.log("WARNING", "  ⚠️ Timeout aguardando a página de mapa carregar após o menu")
                    time.sleep(3)
                    body_html = self.driver.page_source.lower()
                    if self._is_error_page():
                        resultado["mensagem"] = "Mapa aberto pelo menu, mas a página continua com erro"
                        self.log("ERROR", f"  ❌ {resultado['mensagem']}")
                        self.log("ERROR", f"  HTML: {body_html[:300]}")
                        try:
                            self._save_debug_html('menu_fail')
                        except Exception:
                            pass
                        return resultado
            else:
                try:
                    WebDriverWait(self.driver, 10).until(
                        lambda driver: driver.execute_script("return document.readyState") == "complete"
                    )
                except TimeoutException:
                    self.log("WARNING", "  ⚠️ Timeout aguardando a página de mapa carregar após menu")
                time.sleep(3)
                body_html = self.driver.page_source.lower()
                if self._is_error_page():
                    self.log("WARNING", "  ⚠️ O mapa foi aberto pelo menu, mas a página parece inválida")
                    if url:
                        self.log("INFO", f"  🔁 Tentando abrir URL direta do mapa como fallback: {url}")
                        self.driver.get(url)
                        try:
                            WebDriverWait(self.driver, 10).until(
                                lambda driver: driver.execute_script("return document.readyState") == "complete"
                            )
                        except TimeoutException:
                            self.log("WARNING", "  ⚠️ Timeout aguardando a página de mapa carregar após fallback")
                        time.sleep(3)
                        body_html = self.driver.page_source.lower()
                        if self._is_error_page():
                            resultado["mensagem"] = "Mapa aberto, mas a página continua com erro após fallback"
                            self.log("ERROR", f"  ❌ {resultado['mensagem']}")
                            self.log("ERROR", f"  HTML: {body_html[:300]}")
                            try:
                                self._save_debug_html('fallback_fail')
                            except Exception:
                                pass
                            return resultado
                    else:
                        resultado["mensagem"] = "Mapa aberto, mas a página parece inválida e nenhuma URL direta está configurada"
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
                "input[type='text'][placeholder*='buscar' i]",
                "input[type='text'][placeholder*='serial' i]",
                "input[type='text'][placeholder*='número' i]",
                "input[placeholder*='buscar' i]",
                "input[placeholder*='serial' i]",
                "input[placeholder*='número' i]",
                "input[name*='search' i]",
                "input[name*='serial' i]",
                "input[id*='search' i]",
                "input[id*='serial' i]",
                "input[class*='search' i]",
                "input[class*='serial' i]",
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
                # Fallback: procurar o primeiro input[type='text'] visível (muitos FT usam input sem id)
                try:
                    candidates = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='search']")
                    for c in candidates:
                        try:
                            if c.is_displayed() and c.is_enabled():
                                search_field = c
                                self.log("INFO", f"    ✓ Usando fallback input[type='text'] encontrado")
                                break
                        except Exception:
                            continue
                except Exception:
                    pass

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
            
            # Tenta seletores específicos primeiro - click no botão PAI, não no span
            comandos_selectors = [
                (By.XPATH, "//button[.//span[@data-i18n='commands_sent']]"),
                (By.CSS_SELECTOR, "span[data-i18n='commands_sent']"),
                (By.XPATH, "//span[@data-i18n='commands_sent']"),
                (By.XPATH, "//*[contains(text(), 'Comandos enviados')]"),
            ]
            
            comandos = None
            for by, sel in comandos_selectors:
                try:
                    self.log("INFO", f"    ↳ Tentando: {sel}")
                    el = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((by, sel))
                    )
                    # Se encontrou um span, sobe para o botão pai
                    if el.tag_name == "span":
                        try:
                            comandos = el.find_element(By.XPATH, "ancestor::button")
                            self.log("INFO", f"    ✓ Span encontrado, usando botão pai")
                        except Exception:
                            comandos = el
                    else:
                        comandos = el

                    # Tenta clicar no elemento encontrado
                    try:
                        comandos.click()
                    except Exception:
                        try:
                            self.driver.execute_script("arguments[0].click();", comandos)
                        except Exception:
                            raise

                    self.log("INFO", f"    ✓ 'Comandos enviados' clicado")
                    break
                except Exception:
                    self.log("INFO", f"    ✗ Não encontrado: {sel}")
                    continue
            
            if not comandos:
                resultado["mensagem"] = "'Comandos enviados' não encontrado — ajuste o seletor"
                self.log("ERROR", f"  ❌ {resultado['mensagem']}")
                return resultado
            
            time.sleep(2)
            
            # Aguarda pela h4 de confirmação
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h4[data-i18n='commands_detail']"))
                )
                self.log("INFO", f"  ✓ 'Comandos enviados' aberto (confirmado)")
            except TimeoutException:
                self.log("WARNING", f"  ⚠️ 'Comandos enviados' clicado mas confirmação não apareceu")

            # === PASSO 6: Clicar em "Enviar" (bloqueio) ===
            self.log("INFO", f"  🔒 Executando bloqueio...")

            # Tenta seletores específicos primeiro (CSS, depois XPATH)
            enviar_selectors = [
                (By.XPATH, "//div[contains(@class, 'ft-button-div') and normalize-space()='Enviar']"),
                (By.XPATH, "//div[@type='button' and contains(normalize-space(), 'Enviar') and contains(@class, 'ft-button-div') ]"),
                (By.CSS_SELECTOR, "div.ft-button-div"),
                (By.XPATH, "//button[contains(normalize-space(), 'Enviar') ]"),
                (By.XPATH, "//button[contains(., 'Enviar') ]"),
                (By.XPATH, "//button[contains(text(), 'Bloquear')]") ,
            ]

            enviado = False
            for by, sel in enviar_selectors:
                try:
                    self.log("INFO", f"    ↳ Tentando: {sel}")
                    btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by, sel))
                    )
                    self.log("INFO", f"    ✓ Encontrado com: {sel}")
                    try:
                        btn.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", btn)
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
