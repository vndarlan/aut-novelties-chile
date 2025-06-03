# 🇨🇱 Dropi Chile - Automação Background

Sistema de automação completamente redesenhado para rodar **100% em background** no Railway, executando a cada **6 horas** automaticamente.

## 🚀 Características Principais

- ✅ **Execução Automática**: Roda a cada 6 horas sem intervenção
- ✅ **100% Background**: Sem interface web, totalmente headless
- ✅ **Notificações Discord**: Status de início, fim e erros
- ✅ **Persistência**: Mantém logs no PostgreSQL existente
- ✅ **Monitoramento**: Script de health check integrado
- ✅ **Recovery**: Sistema robusto de recuperação de erros

## 📁 Estrutura dos Arquivos

```
projeto/
├── chile_background_bot.py     # Bot principal
├── db_connection.py           # Conexão com PostgreSQL (existente)
├── requirements.txt           # Dependências Python
├── Dockerfile                 # Container para Railway
├── monitor.py                 # Script de monitoramento
└── README.md                  # Este arquivo
```

## 🔧 Deploy no Railway

### 1. Preparação do Código

```bash
# Clone ou atualize o repositório
git clone [seu-repo]
cd [seu-projeto]

# Substitua o arquivo chile.py pelo chile_background_bot.py
mv chile.py chile_old.py  # backup
cp chile_background_bot.py chile_background_bot.py

# Atualize requirements.txt
cp requirements.txt requirements.txt
```

### 2. Configuração no Railway

1. **Acesse o Railway Dashboard**
2. **Vá para o seu projeto Dropi Chile**
3. **Configure as variáveis de ambiente:**

```env
RAILWAY_ENVIRONMENT=production
PYTHONUNBUFFERED=1
PYTHONPATH=/app
DATABASE_URL=[sua-url-postgresql]
```

4. **Atualize o comando de deploy:**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python chile_background_bot.py`

### 3. Deploy

```bash
# Commit e push das mudanças
git add .
git commit -m "Migrate to background automation with 6h scheduling"
git push origin main
```

O Railway automaticamente detectará as mudanças e fará o redeploy.

## 📊 Webhook Discord

O sistema enviará notificações para o Discord configurado:

```
https://discord.com/api/webhooks/1379273630290284606/h1I670CtBauZ0J7_Oq2K5pPJOIZEAHkfI_9-gexG4jmMI0g5bMxRODt85BEcMyX_vkN_
```

### Tipos de Notificação:

- 🚀 **Início**: Quando a automação inicia
- ✅ **Sucesso**: Relatório completo de execução
- ❌ **Erro**: Falhas com detalhes técnicos
- 🔍 **Monitor**: Status de saúde do sistema

## ⏰ Agendamento

O bot executa **automaticamente a cada 6 horas**:

- **00:00 UTC** (21:00 UTC-3)
- **06:00 UTC** (03:00 UTC-3) 
- **12:00 UTC** (09:00 UTC-3)
- **18:00 UTC** (15:00 UTC-3)

### Modificar Agendamento

Para alterar o intervalo, edite a linha no `chile_background_bot.py`:

```python
# De 6 horas para outro intervalo
schedule.every(6).hours.do(run_scheduled_automation)

# Exemplos:
schedule.every(4).hours.do(run_scheduled_automation)    # A cada 4 horas
schedule.every().day.at("09:00").do(run_scheduled_automation)  # Diário às 9h
schedule.every().hour.do(run_scheduled_automation)      # A cada hora
```

## 📈 Monitoramento

### Health Check Manual

```bash
# Via Railway CLI
railway run python monitor.py health

# Ou apenas status
railway run python monitor.py status
```

### Logs em Tempo Real

```bash
# Via Railway CLI
railway logs

# Ou filtrando por erros
railway logs | grep ERROR
```

### Verificar Banco de Dados

O sistema continua salvando no mesmo schema PostgreSQL:

```sql
-- Verificar execuções recentes
SELECT * FROM automation_executions 
WHERE country = 'chile' 
ORDER BY execution_date DESC 
LIMIT 10;
```

## 🛠️ Troubleshooting

### ❌ Bot não está executando

1. **Verificar logs do Railway:**
   ```bash
   railway logs --follow
   ```

2. **Verificar variáveis de ambiente:**
   - `DATABASE_URL` está configurada?
   - `RAILWAY_ENVIRONMENT` = "production"?

3. **Reiniciar o serviço:**
   ```bash
   railway up --detach
   ```

### ❌ Erros de Chrome/Selenium

O Dockerfile já inclui Chrome e ChromeDriver otimizados. Se houver problemas:

1. **Verificar se headless está ativo:**
   ```python
   # No código, sempre deve ter:
   chrome_options.add_argument("--headless=new")
   ```

2. **Verificar recursos do sistema:**
   ```bash
   railway run python monitor.py status
   ```

### ❌ Problemas de memória

1. **Monitorar uso:**
   ```bash
   railway metrics
   ```

2. **Otimizar configuração do Chrome:**
   ```python
   chrome_options.add_argument("--disable-dev-shm-usage")
   chrome_options.add_argument("--no-sandbox")
   ```

### ❌ Falhas de conexão com Dropi

O sistema tem recovery automático, mas se persistir:

1. **Verificar credenciais:**
   ```python
   self.email = "llegolatiendachile@gmail.com"
   self.password = "Chegou123!"
   ```

2. **Verificar URLs do Dropi:**
   - Site pode ter mudado estrutura
   - Verificar se `https://app.dropi.cl/dashboard/novelties` está acessível

## 🔄 Migração do Sistema Anterior

### O que mudou:

| Anterior (Streamlit) | Novo (Background) |
|---------------------|-------------------|
| Interface web manual | 100% automatizado |
| Execução sob demanda | A cada 6 horas |
| Logs na interface | Logs no arquivo + Discord |
| Requer intervenção | Completamente autônomo |

### Banco de dados:

- ✅ **Schema inalterado** - usa as mesmas tabelas
- ✅ **Queries inalteradas** - mesma estrutura de dados
- ✅ **Histórico preservado** - dados anteriores mantidos

## 📋 Checklist de Deploy

- [ ] Código atualizado no repositório
- [ ] `requirements.txt` atualizado
- [ ] Variáveis de ambiente configuradas no Railway
- [ ] Comando de start atualizado: `python chile_background_bot.py`
- [ ] Webhook Discord funcionando
- [ ] Conexão com PostgreSQL testada
- [ ] Primeiro deploy realizado
- [ ] Notificação de início recebida no Discord
- [ ] Logs sendo gerados corretamente

## 🎯 Próximos Passos

1. **Deploy e teste inicial**
2. **Monitorar primeira execução** (Discord + logs)
3. **Verificar dados no banco** após primeira execução
4. **Configurar alertas** se necessário
5. **Documentar** ajustes específicos do ambiente

---

## 📞 Suporte

Em caso de problemas:

1. **Verificar notificações Discord** para status atual
2. **Consultar logs** via `railway logs`
3. **Executar health check** com `monitor.py`
4. **Verificar banco de dados** para resultados

**Sistema projetado para ser completamente autônomo após o deploy inicial!** 🚀