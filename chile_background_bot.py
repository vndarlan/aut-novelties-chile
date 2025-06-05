#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERSÃO CORRIGIDA - Dropi Chile Bot para Railway Cron Jobs
Executa UMA VEZ e termina (para ser usado com Railway Native Cron)
CORREÇÃO: Processamento dinâmico - resolve "Linha não encontrada na tabela"
"""

import time
import pandas as pd
import logging
import traceback
import os
import sys
import platform
import re
import datetime
import requests
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from io import StringIO

# Adiciona o diretório atual ao path para importar db_connection
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from db_connection import get_execution_history, is_railway, save_execution_result
except ImportError:
    print("❌ Erro ao importar db_connection. Verifique se o arquivo existe no diretório raiz.")
    sys.exit(1)

# Constantes
THIS_COUNTRY = "chile"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1379273630290284606/h1I670CtBauZ0J7_Oq2K5pPJOIZEAHkfI_9-gexG4jmMI0g5bMxRODt85BEcMyX_vkN_"

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("dropi_automation_cron")

class DroplAutomationBot:
    def __init__(self):
        self.driver = None
        self.execution_start_time = None
        self.processed_items = 0
        self.success_count = 0
        self.failed_count = 0
        self.failed_items = []
        self.closed_tabs = 0
        self.found_pagination = False
        self.rows = []
        self.total_items = 0
        
        # Credenciais fixas
        self.email = "llegolatiendachile@gmail.com"
        self.password = "Chegou123!"
        
    def send_discord_notification(self, message, is_error=False):
        """Envia notificação para o Discord via webhook"""
        try:
            color = 0xFF0000 if is_error else 0x00FF00  # Vermelho para erro, verde para sucesso
            
            embed = {
                "embeds": [{
                    "title": "🇨🇱 Dropi Chile Cron Job",
                    "description": message,
                    "color": color,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "footer": {
                        "text": "Railway Cron Automation"
                    }
                }]
            }
            
            response = requests.post(DISCORD_WEBHOOK_URL, json=embed, timeout=10)
            if response.status_code == 204:
                logger.info("✅ Notificação Discord enviada com sucesso")
            else:
                logger.warning(f"⚠️ Falha ao enviar notificação Discord: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Erro ao enviar notificação Discord: {str(e)}")

    def create_screenshots_folder(self):
        """Cria pasta de screenshots se não existir"""
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")
        return "screenshots"

    def setup_driver(self):
        """Configura o driver do Selenium"""
        logger.info("🔧 Iniciando configuração do driver Chrome...")
        
        chrome_options = Options()
        
        # Configura modo visual vs headless baseado no ambiente
        if is_railway():
            # Railway: sempre headless
            logger.info("🎭 Modo headless ativado (Railway)")
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
        else:
            # Local: modo visual para debug
            logger.info("👁️ Modo visual ativado (Local) - Chrome será aberto")
            # Não adiciona --headless para mostrar o navegador
        
        # Configurações comuns
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")
        
        try:
            if is_railway():
                # No Railway, usa o Chrome já instalado pelo Dockerfile
                logger.info("🚂 Inicializando o driver Chrome no Railway...")
                service = Service()
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # Localmente, usa o webdriver_manager
                logger.info("💻 Inicializando o driver Chrome localmente...")
                self.driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=chrome_options
                )
                
            logger.info("✅ Driver do Chrome iniciado com sucesso")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao configurar o driver Chrome: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def verify_credentials_and_urls(self):
        """Verifica se as credenciais e URLs estão corretas"""
        logger.info("🔐 Verificando credenciais e URLs...")
        
        logger.info(f"📧 Email: {self.email}")
        logger.info(f"🔑 Senha: {'*' * len(self.password)}")
        
        test_urls = [
            "https://app.dropi.cl",
            "https://app.dropi.cl/auth/login", 
            "https://app.dropi.cl/login",
            "https://dropi.cl/login",
            "https://app.dropi.co/auth/login",
            "https://panel.dropi.cl/login",
            "https://admin.dropi.cl/login"
        ]
        
        logger.info("🌐 URLs sendo testadas:")
        for url in test_urls:
            logger.info(f"  • {url}")
        
        return self.email, self.password, test_urls

    def login(self):
        """Função de login melhorada com debug detalhado"""
        try:
            self.driver.maximize_window()
            
            email, password, login_urls = self.verify_credentials_and_urls()
            
            logger.info("🚀 Iniciando processo de login...")
            
            successful_url = None
            
            for url in login_urls:
                try:
                    logger.info(f"🌐 Tentando URL: {url}")
                    self.driver.get(url)
                    time.sleep(3)
                    
                    current_url = self.driver.current_url
                    page_title = self.driver.title
                    logger.info(f"📍 URL carregada: {current_url}")
                    logger.info(f"📄 Título da página: {page_title}")
                    
                    if "login" in current_url.lower() or "auth" in current_url.lower():
                        successful_url = url
                        logger.info(f"✅ URL válida encontrada: {url}")
                        break
                    else:
                        logger.warning(f"❌ URL {url} redirecionou para: {current_url}")
                        
                except Exception as e:
                    logger.warning(f"❌ Erro ao tentar URL {url}: {str(e)}")
                    continue
            
            if not successful_url:
                logger.error("❌ Nenhuma URL de login válida encontrada")
                return False
            
            # Aguarda a página carregar completamente
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Captura screenshot para debug
            try:
                screenshot_path = os.path.join(self.create_screenshots_folder(), "login_page.png")
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"📸 Screenshot da página de login salvo: {screenshot_path}")
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível salvar screenshot: {str(e)}")
            
            # Procura por campos de email
            email_field = None
            email_selectors = [
                "//input[@type='email']",
                "//input[@name='email']",
                "//input[@id='email']", 
                "//input[contains(@placeholder, 'email')]",
                "//input[contains(@placeholder, 'Email')]",
                "//input[contains(@placeholder, 'correo')]",
                "//input[contains(@name, 'user')]",
                "//input[contains(@id, 'user')]"
            ]
            
            for selector in email_selectors:
                try:
                    email_elements = self.driver.find_elements(By.XPATH, selector)
                    for element in email_elements:
                        if element.is_displayed():
                            email_field = element
                            logger.info(f"✅ Campo de email encontrado com seletor: {selector}")
                            break
                    if email_field:
                        break
                except Exception as e:
                    logger.debug(f"Seletor {selector} falhou: {str(e)}")
            
            if not email_field:
                logger.error("❌ Campo de email não encontrado")
                return False
            
            # Procura por campos de senha
            password_field = None
            password_selectors = [
                "//input[@type='password']",
                "//input[@name='password']",
                "//input[@id='password']",
                "//input[contains(@placeholder, 'senha')]",
                "//input[contains(@placeholder, 'password')]",
                "//input[contains(@placeholder, 'contraseña')]"
            ]
            
            for selector in password_selectors:
                try:
                    password_elements = self.driver.find_elements(By.XPATH, selector)
                    for element in password_elements:
                        if element.is_displayed():
                            password_field = element
                            logger.info(f"✅ Campo de senha encontrado com seletor: {selector}")
                            break
                    if password_field:
                        break
                except Exception as e:
                    logger.debug(f"Seletor {selector} falhou: {str(e)}")
            
            if not password_field:
                logger.error("❌ Campo de senha não encontrado")
                return False
            
            # Preenche os campos
            logger.info("✏️ Preenchendo campos de login...")
            
            try:
                # Preenche email
                self.driver.execute_script("arguments[0].scrollIntoView(true);", email_field)
                time.sleep(0.5)
                email_field.clear()
                email_field.send_keys(email)
                logger.info(f"✅ Email preenchido: {email}")
                
            except Exception as e:
                logger.error(f"❌ Erro ao preencher email: {str(e)}")
                return False
            
            try:
                # Preenche senha
                self.driver.execute_script("arguments[0].scrollIntoView(true);", password_field)
                time.sleep(0.5)
                password_field.clear()
                password_field.send_keys(password)
                logger.info("✅ Senha preenchida")
                
            except Exception as e:
                logger.error(f"❌ Erro ao preencher senha: {str(e)}")
                return False
            
            # Procura e clica no botão de login
            logger.info("🔍 Procurando botão de login...")
            
            login_button = None
            login_selectors = [
                "//button[contains(text(), 'Iniciar Sesión')]",
                "//button[contains(text(), 'Iniciar Sesion')]", 
                "//button[contains(text(), 'Login')]",
                "//button[contains(text(), 'Entrar')]",
                "//button[contains(text(), 'Ingresar')]",
                "//input[@type='submit']",
                "//button[@type='submit']",
                "//button[contains(@class, 'login')]",
                "//button[contains(@class, 'btn-primary')]"
            ]
            
            for selector in login_selectors:
                try:
                    login_elements = self.driver.find_elements(By.XPATH, selector)
                    for element in login_elements:
                        if element.is_displayed():
                            login_button = element
                            logger.info(f"✅ Botão de login encontrado com seletor: {selector}")
                            break
                    if login_button:
                        break
                except Exception as e:
                    logger.debug(f"Seletor {selector} falhou: {str(e)}")
            
            if not login_button:
                logger.error("❌ Botão de login não encontrado")
                return False
            
            # Clica no botão de login
            logger.info("🎯 Tentando fazer login...")
            
            try:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
                time.sleep(1)
                
                try:
                    login_button.click()
                    logger.info("✅ Clique normal realizado")
                except Exception as e1:
                    logger.info(f"Clique normal falhou: {str(e1)}")
                    try:
                        self.driver.execute_script("arguments[0].click();", login_button)
                        logger.info("✅ Clique JavaScript realizado")
                    except Exception as e2:
                        logger.info(f"Clique JavaScript falhou: {str(e2)}")
                        try:
                            password_field.send_keys(Keys.ENTER)
                            logger.info("✅ Enter enviado")
                        except Exception as e3:
                            logger.error(f"Todos os métodos de clique falharam: {str(e3)}")
                            return False
            except Exception as e:
                logger.error(f"❌ Erro ao clicar no botão de login: {str(e)}")
                return False
            
            # Aguarda e verifica o resultado
            logger.info("🔍 Verificando resultado do login...")
            time.sleep(8)
            
            current_url = self.driver.current_url
            page_title = self.driver.title
            logger.info(f"📍 URL após login: {current_url}")
            logger.info(f"📄 Título após login: {page_title}")
            
            # Captura screenshot após login
            try:
                screenshot_path = os.path.join(self.create_screenshots_folder(), "after_login.png")
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"📸 Screenshot pós-login salvo: {screenshot_path}")
            except:
                pass
            
            # Verifica indicadores de sucesso/falha
            success_indicators = ["dashboard", "novelties", "orders", "panel"]
            failure_indicators = ["login", "auth", "error", "invalid"]
            
            url_lower = current_url.lower()
            
            # Verifica indicadores de sucesso
            for indicator in success_indicators:
                if indicator in url_lower:
                    logger.info(f"✅ LOGIN BEM-SUCEDIDO - Indicador de sucesso encontrado: {indicator}")
                    return True
            
            # Se não redirecionou da página de login, provavelmente falhou
            if "login" in url_lower or "auth" in url_lower:
                logger.error("❌ LOGIN FALHOU - Ainda na página de login")
                return False
            
            # Teste final: tenta navegar para o dashboard
            logger.info("🔍 Teste final: navegando para dashboard...")
            try:
                dashboard_urls = [
                    "https://app.dropi.cl/dashboard",
                    "https://app.dropi.cl/dashboard/novelties"
                ]
                
                for dashboard_url in dashboard_urls:
                    try:
                        self.driver.get(dashboard_url)
                        time.sleep(3)
                        final_url = self.driver.current_url
                        
                        if "login" not in final_url.lower():
                            logger.info(f"✅ LOGIN CONFIRMADO - Acesso autorizado ao dashboard: {final_url}")
                            return True
                        else:
                            logger.warning(f"❌ Redirecionado para login ao tentar acessar: {dashboard_url}")
                    except Exception as e:
                        logger.debug(f"Erro ao testar dashboard {dashboard_url}: {str(e)}")
                        continue
            except Exception as e:
                logger.error(f"Erro no teste final: {str(e)}")
            
            logger.error("❌ LOGIN FALHOU - Não foi possível confirmar autenticação")
            return False
            
        except Exception as e:
            logger.error(f"❌ ERRO GERAL NO LOGIN: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def verify_authentication(self):
        """Verifica se o usuário está autenticado"""
        try:
            current_url = self.driver.current_url
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            
            if ("login" in current_url or 
                "registro" in page_text or 
                "crear cuenta" in page_text or
                "registrarme" in page_text):
                return False
            
            return True
        except:
            return False

    def navigate_to_novelties(self):
        """Navega até a página de novelties"""
        try:
            logger.info("🧭 Navegando diretamente para a página de novelties...")
            self.driver.get("https://app.dropi.cl/dashboard/novelties")
            time.sleep(5)
            
            current_url = self.driver.current_url
            logger.info(f"📍 URL atual após navegação: {current_url}")
            
            if not self.verify_authentication():
                logger.error("❌ Não está autenticado - redirecionado para página de registro/login")
                return False
            
            logger.info("🔍 Verificando se a tabela de novelties foi carregada...")
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//table"))
                )
                logger.info("✅ Tabela de novelties encontrada!")
            except:
                logger.warning("⚠️ Não foi possível encontrar a tabela, mas continuando...")
            
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao navegar até Novelties: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def configure_entries_display(self):
        """Configura para exibir 1000 entradas"""
        try:
            current_url = self.driver.current_url
            if "novelties" not in current_url:
                logger.warning(f"⚠️ Não está na página de novelties. URL atual: {current_url}")
                self.driver.get("https://app.dropi.cl/dashboard/novelties")
                time.sleep(5)
            
            # Aguarda a página carregar completamente (especialmente importante localmente)
            logger.info("⏳ Aguardando página carregar completamente...")
            
            # Aguarda o elemento "Loading..." desaparecer
            try:
                WebDriverWait(self.driver, 30).until_not(
                    EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Loading ...")
                )
                logger.info("✅ Loading concluído")
            except TimeoutException:
                logger.warning("⚠️ Timeout esperando loading, mas continuando...")
            
            # Aguarda tabela aparecer
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//table"))
                )
                logger.info("✅ Tabela detectada")
            except TimeoutException:
                logger.warning("⚠️ Tabela não detectada ainda, tentando localizar...")
            
            # Rola até o final da página
            logger.info("📜 Rolando até o final da página para verificar opções de exibição...")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Procura pelo select
            logger.info("🔍 Procurando elemento select...")
            
            entries_found = False
            try:
                select_elements = self.driver.find_elements(By.XPATH, "//select[@name='select' and @id='select' and contains(@class, 'custom-select')]")
                
                if not select_elements:
                    select_elements = self.driver.find_elements(By.XPATH, "//select[contains(@class, 'custom-select') or contains(@class, 'form-control')]")
                
                if not select_elements:
                    select_elements = self.driver.find_elements(By.TAG_NAME, "select")
                
                if select_elements:
                    logger.info(f"✅ Elemento select encontrado: {len(select_elements)} elementos")
                    
                    select_element = select_elements[0]
                    select = Select(select_element)
                    
                    options_text = [o.text for o in select.options]
                    logger.info(f"📋 Opções disponíveis no select: {options_text}")
                    
                    try:
                        select.select_by_visible_text("1000")
                        logger.info("✅ Selecionado '1000' pelo texto visível")
                        entries_found = True
                    except Exception as e:
                        logger.info(f"❌ Erro ao selecionar por texto visível: {str(e)}")
                        
                        try:
                            for i, option in enumerate(select.options):
                                if "1000" in option.text or "1000" in option.get_attribute("value"):
                                    select.select_by_index(i)
                                    logger.info(f"✅ Selecionado '1000' pelo índice {i}")
                                    entries_found = True
                                    break
                        except Exception as e:
                            logger.info(f"❌ Erro ao selecionar por índice: {str(e)}")
                    
                    if entries_found:
                        logger.info("🎯 Configurado para exibir 1000 entradas")
                        self.found_pagination = True
                        time.sleep(8)  # Aguarda mais tempo para recarregar
                        
                        try:
                            WebDriverWait(self.driver, 30).until(
                                lambda d: len(d.find_elements(By.XPATH, "//table/tbody/tr")) > 0
                            )
                            logger.info("✅ Linhas da tabela carregadas com sucesso!")
                        except TimeoutException:
                            logger.warning("⏰ Timeout esperando pelas linhas da tabela")
                else:
                    logger.warning("⚠️ Não foi possível encontrar o elemento select")
            except Exception as e:
                logger.error(f"❌ Erro ao configurar quantidade de entradas: {str(e)}")
            
            # Volta para o topo da página
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao configurar exibição de entradas: {str(e)}")
            return False

    def extract_customer_info(self):
        """Extrai informações do cliente da página"""
        try:
            logger.info("📋 Extraindo informações do cliente...")
            
            customer_info = {
                "address": "",
                "name": "",
                "phone": ""
            }
            
            # Procura pelo cabeçalho "ORDERS TO:"
            try:
                header_info = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'ORDERS TO:')]")
                
                if header_info:
                    for element in header_info:
                        try:
                            parent = element.find_element(By.XPATH, "./..")
                            parent_text = parent.text
                            
                            lines = parent_text.split('\n')
                            if len(lines) > 1:
                                for i, line in enumerate(lines):
                                    if "ORDERS TO:" in line:
                                        if i + 1 < len(lines):
                                            customer_info["name"] = lines[i + 1]
                                        if i + 2 < len(lines):
                                            customer_info["address"] = lines[i + 2]
                                        break
                        except Exception as e:
                            logger.debug(f"Erro ao extrair de ORDERS TO:: {str(e)}")
            except Exception as e:
                logger.debug(f"Erro ao buscar ORDERS TO:: {str(e)}")
            
            # Procura pelo campo de telefone
            try:
                phone_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Telf.')]")
                for element in phone_elements:
                    element_text = element.text
                    if "Telf." in element_text:
                        phone_parts = element_text.split("Telf.")
                        if len(phone_parts) > 1:
                            customer_info["phone"] = phone_parts[1].strip()
                            break
            except Exception as e:
                logger.debug(f"Erro ao buscar telefone: {str(e)}")
            
            # Valores padrão para campos não encontrados
            if not customer_info["name"]:
                customer_info["name"] = "Nome do Cliente"
            
            if not customer_info["address"]:
                customer_info["address"] = "Endereço de Entrega"
            
            if not customer_info["phone"]:
                customer_info["phone"] = "Não informado"
                
            return customer_info
        except Exception as e:
            logger.error(f"❌ Erro ao extrair informações do cliente: {str(e)}")
            return {
                "address": "Endereço de Entrega",
                "name": "Nome do Cliente",
                "phone": "Não informado"
            }

    def parse_chilean_address(self, address):
        """Extrai componentes específicos de um endereço chileno"""
        try:
            logger.info(f"🏠 Analisando endereço chileno: {address}")
            
            components = {
                "calle": "",
                "numero": "",
                "comuna": "",
                "region": ""
            }
            
            # Extrai número
            numero_match = re.search(r'\d+', address)
            if numero_match:
                components["numero"] = numero_match.group(0)
            else:
                components["numero"] = "1"
            
            # Extrai calle
            dash_index = address.find('-')
            if dash_index != -1:
                components["calle"] = address[:dash_index].strip()
            else:
                if numero_match:
                    numero = components["numero"]
                    calle_index = address.find(numero)
                    if calle_index > 0:
                        components["calle"] = address[:calle_index].strip()
                else:
                    components["calle"] = address
            
            # Extrai comuna e região
            last_comma_index = address.rfind(',')
            
            if last_comma_index != -1:
                comuna_region_part = address[last_comma_index+1:].strip()
                
                if "BIO - BIO" in comuna_region_part.upper():
                    bio_index = comuna_region_part.upper().find("BIO - BIO")
                    dash_before_bio = comuna_region_part[:bio_index].rfind('-')
                    
                    if dash_before_bio != -1:
                        components["comuna"] = comuna_region_part[:dash_before_bio].strip()
                        components["region"] = "BIO - BIO"
                else:
                    last_hyphen_index = comuna_region_part.rfind('-')
                    
                    if last_hyphen_index != -1:
                        components["comuna"] = comuna_region_part[:last_hyphen_index].strip()
                        components["region"] = comuna_region_part[last_hyphen_index+1:].strip()
                    else:
                        components["comuna"] = comuna_region_part.strip()
            
            return components
        except Exception as e:
            logger.error(f"❌ Erro ao analisar endereço chileno: {str(e)}")
            return {
                "calle": "",
                "numero": "",
                "comuna": "",
                "region": ""
            }

    def generate_automatic_message(self, form_text):
        """Gera mensagens automáticas com base no texto da incidência"""
        try:
            form_text = form_text.upper().strip()
            logger.info(f"🤖 Analisando texto para mensagem automática: '{form_text[:100]}...'")
            
            if any(phrase in form_text for phrase in ["CLIENTE AUSENTE", "NADIE EN CASA"]):
                message = "Entramos en contacto con el cliente y él se disculpó y mencionó que estará en casa para recibir el producto en este próximo intento."
                logger.info("✅ Resposta selecionada: CLIENTE AUSENTE")
                return message
            
            if "PROBLEMA COBRO" in form_text:
                message = "En llamada telefónica, el cliente afirmó que estará con dinero suficiente para comprar el producto, por favor intenten nuevamente."
                logger.info("✅ Resposta selecionada: PROBLEMA COBRO")
                return message
            
            if any(phrase in form_text for phrase in ["DIRECCIÓN INCORRECTA", "DIRECCION INCORRECTA", "FALTAN DATOS", "INUBICABLE", "COMUNA ERRADA", "CAMBIO DE DOMICILIO"]):
                message = "En llamada telefónica, el cliente rectificó sus datos para que la entrega suceda de forma más asertiva."
                logger.info("✅ Resposta selecionada: PROBLEMA DE ENDEREÇO")
                return message
            
            if any(phrase in form_text for phrase in ["RECHAZA", "RECHAZADA"]):
                message = "En llamada telefónica, el cliente afirma que quiere el producto y mencionó que no fue buscado por la transportadora. Por lo tanto, por favor envíen el producto hasta el cliente."
                logger.info("✅ Resposta selecionada: RECHAZO DE ENTREGA")
                return message
            
            logger.warning("⚠️ Nenhuma condição conhecida encontrada na incidência")
            return ""
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar mensagem automática: {str(e)}")
            return ""

    def check_and_close_tabs(self):
        """Verifica se há novas guias abertas e as fecha"""
        try:
            handles = self.driver.window_handles
            
            if len(handles) > 1:
                current_handle = self.driver.current_window_handle
                
                for handle in handles:
                    if handle != current_handle:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                        self.closed_tabs += 1
                
                self.driver.switch_to.window(current_handle)
                logger.info(f"🗂️ Fechadas {len(handles) - 1} guias extras")
        except Exception as e:
            logger.error(f"❌ Erro ao verificar e fechar guias: {str(e)}")

    def get_available_novelty_rows(self):
        """
        Obtém todas as linhas que têm botão Save disponível
        """
        try:
            # Aguarda tabela estar presente
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//table"))
            )
            
            # Procura por linhas com botão Save
            rows_with_save = []
            
            # Múltiplos seletores para encontrar linhas
            row_selectors = [
                "//table/tbody/tr[.//button[contains(@class, 'btn-success')]]",
                "//table//tr[.//button[contains(text(), 'Save')]]",
                "//table//tr[.//button[contains(@class, 'btn-success') and contains(text(), 'Save')]]"
            ]
            
            for selector in row_selectors:
                try:
                    found_rows = self.driver.find_elements(By.XPATH, selector)
                    if found_rows:
                        rows_with_save = found_rows
                        logger.info(f"✅ Encontradas {len(found_rows)} linhas com botão Save usando: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Seletor falhou: {selector} - {str(e)}")
                    continue
            
            # Filtra apenas linhas visíveis
            visible_rows = []
            for row in rows_with_save:
                try:
                    if row.is_displayed():
                        # Verifica se realmente tem botão Save visível
                        save_buttons = row.find_elements(By.XPATH, ".//button[contains(@class, 'btn-success')]")
                        if save_buttons and any(btn.is_displayed() for btn in save_buttons):
                            visible_rows.append(row)
                except Exception as e:
                    logger.debug(f"Erro ao verificar visibilidade da linha: {str(e)}")
                    continue
            
            logger.info(f"📊 Linhas visíveis com botão Save: {len(visible_rows)}")
            return visible_rows
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter linhas disponíveis: {str(e)}")
            return []

    def process_single_novelty(self, row_element, iteration_number):
        """
        Processa uma única novelty
        Parâmetros:
        - row_element: elemento da linha da tabela
        - iteration_number: número da iteração para logs
        """
        try:
            logger.info(f"🎯 Processando novelty (iteração {iteration_number})")
            
            # Rola até a linha
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row_element)
            time.sleep(1)
            
            # Obtém ID da linha para logs
            try:
                row_cells = row_element.find_elements(By.TAG_NAME, "td")
                row_id = row_cells[0].text if row_cells else f"Iteração {iteration_number}"
            except:
                row_id = f"Iteração {iteration_number}"
            
            logger.info(f"📋 Processando: {row_id}")
            
            # Encontra botão Save na linha
            save_buttons = row_element.find_elements(By.XPATH, ".//button[contains(@class, 'btn-success')]")
            
            if not save_buttons:
                logger.error("❌ Botão Save não encontrado na linha")
                return False
            
            save_button = save_buttons[0]
            
            # Clica no Save
            try:
                self.driver.execute_script("arguments[0].click();", save_button)
                logger.info("✅ Botão Save clicado")
            except Exception as e:
                logger.error(f"❌ Erro ao clicar no Save: {str(e)}")
                return False
            
            # Aguarda modal aparecer
            time.sleep(5)
            
            # Verifica se modal apareceu
            modal_appeared = False
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'modal')]")),
                        EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Yes')]")),
                        EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Sim')]"))
                    )
                )
                modal_appeared = True
                logger.info("✅ Modal detectado")
            except TimeoutException:
                logger.error("❌ Modal não apareceu - item pode já estar processado")
                return False
            
            if not modal_appeared:
                return False
            
            # Clica em Yes/Sim
            yes_clicked = False
            for text in ["Yes", "Sim", "YES", "SIM"]:
                try:
                    yes_buttons = self.driver.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
                    for button in yes_buttons:
                        if button.is_displayed():
                            self.driver.execute_script("arguments[0].click();", button)
                            logger.info(f"✅ Clicado em '{text}'")
                            yes_clicked = True
                            break
                    if yes_clicked:
                        break
                except:
                    continue
            
            if not yes_clicked:
                logger.error("❌ Não foi possível clicar em Yes/Sim")
                return False
            
            time.sleep(5)
            
            # Extrai informações e preenche formulário
            customer_info = self.extract_customer_info()
            
            # Processa formulário
            form_success = self.fill_and_submit_form(customer_info)
            
            if form_success:
                # Aguarda finalização
                time.sleep(8)
                
                # Verifica se modal fechou (sucesso)
                modal_closed = True
                try:
                    modal_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'modal') and contains(@style, 'display: block')]")
                    if modal_elements:
                        modal_closed = False
                except:
                    pass
                
                # Fecha guias extras
                self.check_and_close_tabs()
                
                if modal_closed:
                    logger.info(f"✅ Novelty {row_id} processada com sucesso!")
                    return True
                else:
                    logger.warning(f"⚠️ Modal ainda aberto para {row_id}")
                    return False
            else:
                logger.error(f"❌ Falha no formulário para {row_id}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar novelty: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def fill_and_submit_form(self, customer_info):
        """
        Preenche e submete o formulário da novelty
        """
        try:
            # Analisa texto para mensagem automática
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                automatic_message = self.generate_automatic_message(page_text)
                if automatic_message:
                    customer_info["automatic_message"] = automatic_message
            except Exception as e:
                logger.debug(f"Erro ao analisar texto: {str(e)}")
            
            # Procura formulário
            form_modal = None
            try:
                form_modal = WebDriverWait(self.driver, 10).until(
                    EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'modal-body')]"))
                )
            except:
                try:
                    form_modal = self.driver.find_element(By.TAG_NAME, "body")
                except:
                    logger.error("❌ Formulário não encontrado")
                    return False
            
            if not form_modal:
                return False
            
            # Preenche campos
            address_components = self.parse_chilean_address(customer_info["address"])
            
            fields_to_fill = [
                (["Datos adicionales a la dirección", "Datos adicionales"], customer_info["address"]),
                (["Solución", "Solucion"], customer_info.get("automatic_message", customer_info["address"])),
                (["Calle"], address_components["calle"]),
                (["Numero", "Número"], address_components["numero"]),
                (["Comuna"], address_components["comuna"]),
                (["Region", "Región"], address_components["region"]),
                (["Nombre", "Nome"], customer_info["name"]),
                (["Celular", "Teléfono"], customer_info["phone"])
            ]
            
            fields_filled = 0
            for labels, value in fields_to_fill:
                if self.fill_field_by_label(form_modal, labels, value):
                    fields_filled += 1
            
            logger.info(f"✏️ Preenchidos {fields_filled} campos")
            
            if fields_filled > 0:
                # Salva formulário
                if self.click_save_button():
                    logger.info("✅ Formulário salvo")
                    return True
                else:
                    logger.error("❌ Falha ao salvar formulário")
                    return False
            else:
                logger.error("❌ Nenhum campo preenchido")
                return False
            
        except Exception as e:
            logger.error(f"❌ Erro no formulário: {str(e)}")
            return False

    def process_all_novelties(self):
        """
        NOVA VERSÃO: Processa novelties dinamicamente
        Sempre pega a primeira linha disponível com botão Save
        """
        try:
            logger.info(f"🔄 Iniciando processamento dinâmico de novelties...")
            
            max_iterations = 100  # Limite de segurança
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                
                logger.info(f"🔄 Iteração {iteration} - Buscando novelties disponíveis...")
                
                # Aguarda página estabilizar
                time.sleep(3)
                
                # Recarrega todas as linhas da tabela
                available_rows = self.get_available_novelty_rows()
                
                if not available_rows:
                    logger.info("✅ Nenhuma novelty disponível para processar - Finalizando")
                    break
                
                logger.info(f"📋 Encontradas {len(available_rows)} novelties disponíveis")
                
                # Sempre processa a PRIMEIRA linha disponível
                success = self.process_single_novelty(available_rows[0], iteration)
                
                if success:
                    self.success_count += 1
                    logger.info(f"✅ Novelty {iteration} processada com sucesso!")
                else:
                    self.failed_count += 1
                    self.failed_items.append({
                        "id": f"Iteração {iteration}",
                        "error": "Falha no processamento"
                    })
                    logger.error(f"❌ Falha ao processar novelty {iteration}")
                
                # Pausa entre processamentos
                time.sleep(2)
            
            if iteration >= max_iterations:
                logger.warning("⚠️ Limite máximo de iterações atingido")
            
            logger.info(f"🎯 Processamento concluído: {self.success_count} sucessos, {self.failed_count} falhas")
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento de novelties: {str(e)}")
            logger.error(traceback.format_exc())

    def fill_field_by_label(self, form_modal, label_texts, value):
        """Preenche um campo específico do formulário"""
        try:
            for label_text in label_texts:
                try:
                    # Procura por input com atributos relacionados ao label
                    input_selectors = [
                        f"//input[contains(@id, '{label_text.lower()}')]",
                        f"//input[contains(@name, '{label_text.lower()}')]",
                        f"//input[contains(@placeholder, '{label_text}')]",
                        f"//label[contains(text(), '{label_text}')]//following::input[1]",
                        f"//*[contains(text(), '{label_text}')]//following::input[1]"
                    ]
                    
                    for selector in input_selectors:
                        try:
                            input_fields = self.driver.find_elements(By.XPATH, selector)
                            for input_field in input_fields:
                                if input_field.is_displayed():
                                    # Preenche o campo
                                    self.driver.execute_script("arguments[0].scrollIntoView(true);", input_field)
                                    time.sleep(0.5)
                                    self.driver.execute_script("arguments[0].click();", input_field)
                                    self.driver.execute_script("arguments[0].value = '';", input_field)
                                    self.driver.execute_script(f"arguments[0].value = '{value}';", input_field)
                                    
                                    # Dispara eventos
                                    for event in ["input", "change", "blur"]:
                                        self.driver.execute_script(f"arguments[0].dispatchEvent(new Event('{event}'));", input_field)
                                    
                                    logger.info(f"✅ Campo '{label_text}' preenchido com sucesso")
                                    return True
                        except Exception as e:
                            continue
                except Exception as e:
                    continue
            
            return False
        except Exception as e:
            logger.error(f"❌ Erro ao preencher campo: {str(e)}")
            return False

    def click_save_button(self):
        """Clica no botão de salvar"""
        try:
            logger.info("💾 Tentando clicar no botão de salvar...")
            time.sleep(3)
            
            # Procura por botões de salvar
            save_patterns = [
                "SAVE SOLUCION", "Save Solucion", "SAVE", "Save", 
                "GUARDAR", "Guardar", "ENVIAR", "Enviar"
            ]
            
            for pattern in save_patterns:
                save_buttons = self.driver.find_elements(By.XPATH, f"//button[contains(text(), '{pattern}')]")
                for button in save_buttons:
                    if button.is_displayed():
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                            time.sleep(1)
                            self.driver.execute_script("arguments[0].click();", button)
                            logger.info(f"✅ Clicado no botão '{pattern}'")
                            time.sleep(2)
                            return True
                        except:
                            continue
            
            # Último recurso: Enter
            try:
                active_element = self.driver.switch_to.active_element
                active_element.send_keys(Keys.ENTER)
                logger.info("✅ Tecla Enter enviada")
                return True
            except:
                pass
            
            return False
        except Exception as e:
            logger.error(f"❌ Erro ao clicar no botão de salvar: {str(e)}")
            return False

    def run_automation(self):
        """
        VERSÃO CORRIGIDA - Executa automação com processamento dinâmico
        """
        try:
            self.execution_start_time = datetime.datetime.now()
            
            # Notificação inicial
            timezone_info = datetime.timezone(datetime.timedelta(hours=-3))
            start_time_local = self.execution_start_time.replace(tzinfo=timezone_info)
            start_message = f"🚀 **Cron Job iniciado** ({start_time_local.strftime('%H:%M')} UTC-3)\n\n📅 Próxima execução: em 6 horas\n🔧 Modo: Railway Native Cron (CORRIGIDO)"
            self.send_discord_notification(start_message)
            
            logger.info("=" * 50)
            logger.info("🚀 INICIANDO AUTOMAÇÃO CRON JOB (VERSÃO CORRIGIDA)")
            logger.info("=" * 50)
            
            # Setup do driver
            logger.info("🔧 PASSO 1: Configurando driver...")
            if not self.setup_driver():
                raise Exception("Falha ao configurar o driver Chrome")
            logger.info("✅ Driver configurado com sucesso")
            
            # Login
            logger.info("🔐 PASSO 2: Fazendo login...")
            if not self.login():
                raise Exception("Falha no login")
            logger.info("✅ Login realizado com sucesso")
            
            # Navegar para novelties
            logger.info("🧭 PASSO 3: Navegando para novelties...")
            if not self.navigate_to_novelties():
                raise Exception("Falha ao navegar até Novelties")
            logger.info("✅ Navegação para novelties concluída")
            
            # Configurar exibição
            logger.info("⚙️ PASSO 4: Configurando exibição de entradas...")
            if not self.configure_entries_display():
                raise Exception("Falha ao configurar exibição de entradas")
            logger.info("✅ Configuração de exibição concluída")
            
            # NOVO: Processamento dinâmico
            logger.info("🔄 PASSO 5: Processamento dinâmico de novelties...")
            self.process_all_novelties()
            
            logger.info("📊 PASSO 6: Processamento concluído")
            logger.info(f"✅ Sucessos: {self.success_count}, ❌ Falhas: {self.failed_count}")
            
            # Gerar relatório
            logger.info("📋 PASSO 7: Gerando relatório...")
            self.generate_report()
            
            # Salvar no banco de dados
            logger.info("💾 PASSO 8: Salvando no banco de dados...")
            self.save_to_database()
            
            # Notificação de sucesso
            execution_time = (datetime.datetime.now() - self.execution_start_time).total_seconds()
            
            if self.success_count > 0:
                success_message = f"""✅ **Cron Job concluído (CORRIGIDO)!**

📊 **Resultados:**
• ✅ Processadas: **{self.success_count}**
• ❌ Falhas: **{self.failed_count}**
• 📋 Total encontradas: **{self.success_count + self.failed_count}**
• 🗂️ Guias fechadas: **{self.closed_tabs}**
• ⏱️ Tempo: **{execution_time/60:.2f} min**

🛠️ **Correções aplicadas:**
• Processamento dinâmico (sem índices fixos)
• Sempre processa primeira linha disponível
• Elimina erro "Linha não encontrada"
• Detecção inteligente de novelties

🔧 **Detalhes:**
• 📄 Paginação: {'✅ Sim' if self.found_pagination else '❌ Não'}
• 📸 Screenshots: {len(os.listdir('screenshots')) if os.path.exists('screenshots') else 0}
• 🔄 **Próxima execução:** em 6 horas"""
            else:
                success_message = f"""⚠️ **Cron Job finalizado sem processamentos**

📊 **Estatísticas:**
• 📋 Novelties encontradas: **{self.success_count + self.failed_count}**
• ✅ Processadas: **{self.success_count}**
• ❌ Falhas: **{self.failed_count}**
• ⏱️ Tempo: **{execution_time/60:.2f} min**

❓ **Possíveis causas:**
• Todas já processadas anteriormente
• Erro na detecção dos botões Save
• Mudança na estrutura do site

🔄 **Próxima verificação:** em 6 horas"""

            if self.failed_count > 0:
                success_message += f"\n\n⚠️ **Falhas encontradas:**"
                for i, item in enumerate(self.failed_items[:3]):  # Mostra apenas as primeiras 3
                    success_message += f"\n• {item['id']}: {item['error'][:50]}..."
                
                if len(self.failed_items) > 3:
                    success_message += f"\n• ... e mais {len(self.failed_items) - 3} falhas"
            
            # Determina se é erro baseado nos resultados
            is_error = (self.success_count == 0 and (self.success_count + self.failed_count) > 0) or (self.failed_count > self.success_count)
            self.send_discord_notification(success_message, is_error=is_error)
            
            logger.info("=" * 50)
            logger.info("🎯 AUTOMAÇÃO CRON JOB CORRIGIDA CONCLUÍDA")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"❌ ERRO CRÍTICO na automação: {str(e)}")
            logger.error(f"Traceback completo: {traceback.format_exc()}")
            
            # Captura screenshot de erro se possível
            try:
                if self.driver:
                    error_screenshot = os.path.join(self.create_screenshots_folder(), "error.png")
                    self.driver.save_screenshot(error_screenshot)
                    logger.info(f"📸 Screenshot de erro salvo: {error_screenshot}")
            except:
                pass
            
            # Notificação de erro detalhada
            execution_time = (datetime.datetime.now() - self.execution_start_time).total_seconds() if self.execution_start_time else 0
            
            error_message = f"""❌ **ERRO CRÍTICO no Cron Job (CORRIGIDO)!**

🚨 **Erro:** {str(e)[:300]}

📊 **Progresso até o erro:**
• ✅ Processadas: {self.success_count}
• ❌ Falhas: {self.failed_count}
• 📋 Encontradas: {self.success_count + self.failed_count}
• ⏱️ Tempo até falha: {execution_time/60:.2f} min

🔧 **Para debug:**
• Verificar logs completos no Railway
• Verificar screenshots salvos
• Testar acesso manual ao Dropi

🔄 **Próxima tentativa:** em 6 horas"""

            self.send_discord_notification(error_message, is_error=True)
            
        finally:
            # Fecha o navegador
            if self.driver:
                try:
                    logger.info("🔒 Fechando navegador...")
                    self.driver.quit()
                    logger.info("✅ Navegador fechado com sucesso")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao fechar navegador: {str(e)}")
            
            # IMPORTANTE: Termina o processo para permitir próxima execução
            logger.info("🏁 Terminando processo...")
            sys.exit(0)

    def generate_report(self):
        """Gera relatório da execução"""
        report = {
            "total_processados": self.success_count,
            "total_falhas": self.failed_count,
            "itens_com_falha": self.failed_items,
            "guias_fechadas": self.closed_tabs,
            "encontrou_paginacao": self.found_pagination
        }
        
        logger.info("=" * 50)
        logger.info("📋 RELATÓRIO DE EXECUÇÃO")
        logger.info("=" * 50)
        logger.info(f"✅ Total de novelties processadas com sucesso: {report['total_processados']}")
        logger.info(f"❌ Total de novelties com falha: {report['total_falhas']}")
        logger.info(f"🗂️ Total de guias fechadas: {report['guias_fechadas']}")
        logger.info(f"📄 Encontrou paginação: {'Sim' if report['encontrou_paginacao'] else 'Não'}")
        
        if report['total_falhas'] > 0:
            logger.info("❌ Detalhes dos itens com falha:")
            for item in report['itens_com_falha']:
                logger.info(f"  • ID: {item['id']}, Erro: {item['error']}")
        
        logger.info("=" * 50)
        
        return report

    def save_to_database(self):
        """Salva os resultados no banco de dados"""
        try:
            execution_time = (datetime.datetime.now() - self.execution_start_time).total_seconds()
            
            save_execution_result(
                country=THIS_COUNTRY,
                total_processed=self.success_count,
                successful=self.success_count,
                failed=self.failed_count,
                execution_time=execution_time
            )
            
            logger.info("💾 Resultados salvos no banco de dados com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar no banco de dados: {str(e)}")

def main():
    """Função principal - EXECUÇÃO ÚNICA PARA CRON"""
    logger.info("=" * 60)
    logger.info("🚀 INICIANDO DROPI CHILE CRON JOB (VERSÃO CORRIGIDA)")
    logger.info("=" * 60)
    logger.info(f"🌍 Ambiente: {'Railway' if is_railway() else 'Local'}")
    logger.info(f"📅 Data/Hora: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🕐 Timezone: UTC (Railway) / Execução via Cron nativo")
    
    # Verifica se está pausado
    if os.getenv("BOT_PAUSED", "").lower() in ["true", "1", "yes"]:
        logger.info("🛑 BOT PAUSADO - Variável BOT_PAUSED detectada")
        logger.info("Para reativar: remova a variável BOT_PAUSED ou mude para 'false'")
        sys.exit(0)
    
    try:
        # Executa automação UMA VEZ e termina
        logger.info("🎯 Executando automação única (Cron Job) - VERSÃO CORRIGIDA...")
        
        bot = DroplAutomationBot()
        bot.run_automation()
        
        logger.info("✅ Cron Job finalizado com sucesso")
        
    except KeyboardInterrupt:
        logger.info("⚠️ Interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erro no processo principal: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        logger.info("=" * 60)
        logger.info("🏁 DROPI CHILE CRON JOB FINALIZADO (VERSÃO CORRIGIDA)")
        logger.info("🔄 Próxima execução: automática via Railway Cron")
        logger.info("=" * 60)
        sys.exit(0)

if __name__ == "__main__":
    main()