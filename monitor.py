#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Monitoramento para Dropi Chile Background Bot
Verifica status, logs e envia relatórios
"""

import os
import sys
import datetime
import requests
import json
import subprocess
import psutil
import logging
from pathlib import Path

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Discord webhook para notificações de monitoramento
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1379273630290284606/h1I670CtBauZ0J7_Oq2K5pPJOIZEAHkfI_9-gexG4jmMI0g5bMxRODt85BEcMyX_vkN_"

class DroplMonitor:
    def __init__(self):
        self.bot_process_name = "chile_background_bot.py"
        self.log_file = "automation.log"
        
    def send_discord_notification(self, message, is_error=False):
        """Envia notificação para Discord"""
        try:
            color = 0xFF0000 if is_error else 0x0099FF  # Vermelho para erro, azul para info
            
            embed = {
                "embeds": [{
                    "title": "🔍 Monitor Dropi Chile",
                    "description": message,
                    "color": color,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "footer": {
                        "text": "Railway Monitor"
                    }
                }]
            }
            
            response = requests.post(DISCORD_WEBHOOK_URL, json=embed, timeout=10)
            if response.status_code == 204:
                logger.info("Notificação de monitoramento enviada")
            else:
                logger.warning(f"Falha ao enviar notificação: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Erro ao enviar notificação: {str(e)}")
    
    def check_process_status(self):
        """Verifica se o processo do bot está rodando"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline'])
                        if self.bot_process_name in cmdline:
                            return {
                                "running": True,
                                "pid": proc.info['pid'],
                                "memory_mb": proc.memory_info().rss / 1024 / 1024,
                                "cpu_percent": proc.cpu_percent(),
                                "create_time": datetime.datetime.fromtimestamp(proc.create_time())
                            }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {"running": False}
        except Exception as e:
            logger.error(f"Erro ao verificar status do processo: {str(e)}")
            return {"running": False, "error": str(e)}
    
    def check_log_file(self):
        """Verifica logs recentes"""
        try:
            if not os.path.exists(self.log_file):
                return {"exists": False}
            
            # Obtém informações do arquivo
            stat = os.stat(self.log_file)
            last_modified = datetime.datetime.fromtimestamp(stat.st_mtime)
            file_size_mb = stat.st_size / 1024 / 1024
            
            # Lê últimas linhas do log
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                last_lines = lines[-10:] if len(lines) >= 10 else lines
            
            # Conta erros recentes (última hora)
            recent_errors = 0
            one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
            
            for line in last_lines:
                if "ERROR" in line or "ERRO" in line:
                    try:
                        # Tenta extrair timestamp da linha
                        if line.startswith("20"):  # Formato YYYY-MM-DD
                            timestamp_str = line[:19]  # YYYY-MM-DD HH:MM:SS
                            timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                            if timestamp > one_hour_ago:
                                recent_errors += 1
                    except:
                        recent_errors += 1  # Conta mesmo se não conseguir parsear timestamp
            
            return {
                "exists": True,
                "last_modified": last_modified,
                "size_mb": round(file_size_mb, 2),
                "recent_errors": recent_errors,
                "last_lines": [line.strip() for line in last_lines[-3:]]  # Últimas 3 linhas
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar log: {str(e)}")
            return {"exists": False, "error": str(e)}
    
    def check_system_resources(self):
        """Verifica recursos do sistema"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memória
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / 1024 / 1024 / 1024
            
            # Disco
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / 1024 / 1024 / 1024
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_available_gb": round(memory_available_gb, 2),
                "disk_percent": disk_percent,
                "disk_free_gb": round(disk_free_gb, 2)
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar recursos: {str(e)}")
            return {"error": str(e)}
    
    def check_database_connection(self):
        """Verifica conexão com banco de dados"""
        try:
            # Importa o módulo de conexão se existir
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            
            try:
                from db_connection import get_connection
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                conn.close()
                return {"connected": True}
            except ImportError:
                return {"connected": False, "error": "Módulo db_connection não encontrado"}
            
        except Exception as e:
            logger.error(f"Erro ao verificar banco de dados: {str(e)}")
            return {"connected": False, "error": str(e)}
    
    def generate_status_report(self):
        """Gera relatório completo de status"""
        logger.info("Gerando relatório de status...")
        
        # Coleta informações
        process_status = self.check_process_status()
        log_info = self.check_log_file()
        system_resources = self.check_system_resources()
        db_status = self.check_database_connection()
        
        # Monta relatório
        report = f"""📊 **Relatório de Status - {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}**

🤖 **Status do Bot:**
{'✅ Rodando' if process_status.get('running') else '❌ Parado'}"""
        
        if process_status.get('running'):
            uptime = datetime.datetime.now() - process_status.get('create_time', datetime.datetime.now())
            report += f"""
• PID: {process_status.get('pid')}
• Memória: {process_status.get('memory_mb', 0):.1f} MB
• CPU: {process_status.get('cpu_percent', 0):.1f}%
• Uptime: {str(uptime).split('.')[0]}"""
        
        report += f"""

📝 **Logs:**
{'✅ Arquivo existe' if log_info.get('exists') else '❌ Arquivo não encontrado'}"""
        
        if log_info.get('exists'):
            time_since_update = datetime.datetime.now() - log_info.get('last_modified', datetime.datetime.now())
            report += f"""
• Tamanho: {log_info.get('size_mb', 0)} MB
• Última atualização: {time_since_update.seconds // 60} min atrás
• Erros recentes: {log_info.get('recent_errors', 0)}"""
            
            if log_info.get('last_lines'):
                report += f"\n• Última linha: `{log_info['last_lines'][-1][:50]}...`"
        
        report += f"""

💾 **Recursos do Sistema:**"""
        
        if 'error' not in system_resources:
            report += f"""
• CPU: {system_resources.get('cpu_percent', 0):.1f}%
• Memória: {system_resources.get('memory_percent', 0):.1f}% (livre: {system_resources.get('memory_available_gb', 0)} GB)
• Disco: {system_resources.get('disk_percent', 0):.1f}% (livre: {system_resources.get('disk_free_gb', 0)} GB)"""
        else:
            report += f"\n❌ Erro ao obter recursos: {system_resources['error']}"
        
        report += f"""

🗄️ **Banco de Dados:**
{'✅ Conectado' if db_status.get('connected') else '❌ Desconectado'}"""
        
        if not db_status.get('connected') and db_status.get('error'):
            report += f"\n• Erro: {db_status['error'][:100]}"
        
        # Determina se há problemas críticos
        is_critical = (
            not process_status.get('running') or
            not log_info.get('exists') or
            log_info.get('recent_errors', 0) > 5 or
            not db_status.get('connected') or
            system_resources.get('memory_percent', 0) > 90 or
            system_resources.get('disk_percent', 0) > 90
        )
        
        return report, is_critical
    
    def run_health_check(self):
        """Executa verificação completa de saúde"""
        try:
            logger.info("Iniciando verificação de saúde...")
            
            report, is_critical = self.generate_status_report()
            
            # Envia notificação
            self.send_discord_notification(report, is_error=is_critical)
            
            if is_critical:
                logger.warning("⚠️ Problemas críticos detectados!")
            else:
                logger.info("✅ Sistema funcionando normalmente")
            
            return not is_critical
            
        except Exception as e:
            logger.error(f"Erro na verificação de saúde: {str(e)}")
            error_report = f"❌ **Erro no Monitor**\n\nFalha ao executar verificação de saúde:\n`{str(e)}`"
            self.send_discord_notification(error_report, is_error=True)
            return False

def main():
    """Função principal"""
    logger.info("=== INICIANDO MONITOR DROPI CHILE ===")
    
    monitor = DroplMonitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "status":
            # Apenas gera relatório
            report, is_critical = monitor.generate_status_report()
            print(report)
            return 0 if not is_critical else 1
            
        elif command == "health":
            # Executa verificação completa
            success = monitor.run_health_check()
            return 0 if success else 1
            
        else:
            print("Uso: python monitor.py [status|health]")
            return 1
    else:
        # Execução padrão - verificação completa
        success = monitor.run_health_check()
        return 0 if success else 1

if __name__ == "__main__":
    exit(main())