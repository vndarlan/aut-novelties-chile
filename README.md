# 🇨🇱 Dropi Chile - Automação Railway Cron

Sistema de automação para processamento de novelties do Dropi Chile usando **Railway Native Cron Jobs**.

## 🚀 Características

- ✅ **Railway Native Cron**: Execução a cada 6 horas via cron nativo
- ✅ **Modo Visual Local**: Chrome visível para debug local
- ✅ **Headless Railway**: Execução otimizada em produção
- ✅ **Notificações Discord**: Status completo de cada execução
- ✅ **Banco PostgreSQL**: Histórico persistente de execuções
- ✅ **Loading Detection**: Aguarda página carregar completamente
- ✅ **Recovery Automático**: Processa novelties em múltiplas execuções

## 📁 Estrutura

```
projeto/
├── chile_background_bot.py     # Bot principal (execução única)
├── db_connection.py           # Conexão PostgreSQL
├── monitor.py                 # Health check
├── Dockerfile                # Container Railway
├── requirements.txt           # Dependências
└── README.md                  # Documentação
```

## 🔧 Setup Railway

### 1. Configurar Cron Schedule
1. **Railway Dashboard** → **Projeto** → **Settings**
2. **Cron Schedule**: `0 */6 * * *`
3. **Start Command**: `python chile_background_bot.py`

### 2. Variáveis de Ambiente
```env
RAILWAY_ENVIRONMENT=production
DATABASE_URL=[postgresql-url]
PYTHONUNBUFFERED=1
```

### 3. Deploy
```bash
git add .
git commit -m "Deploy Railway cron automation"
git push origin main
```

## ⏰ Horários de Execução

**Cron**: `0 */6 * * *`
- **00:00 UTC** (21:00 Chile)
- **06:00 UTC** (03:00 Chile)
- **12:00 UTC** (09:00 Chile)
- **18:00 UTC** (15:00 Chile)

## 💻 Desenvolvimento Local

### Modo Visual
- **Local**: Chrome abre visualmente para debug
- **Railway**: Continua headless

### Teste
```bash
python chile_background_bot.py  # Execução manual
```

## 📊 Discord Notifications

Webhook configurado para notificar:
- 🚀 Início da execução
- ✅ Sucesso com estatísticas
- ❌ Erros com detalhes
- ⚠️ Avisos (sem novelties)

## 🔄 Funcionamento

### Fluxo Normal
1. Login automático no Dropi
2. Navega para novelties
3. Aguarda loading completar
4. Configura visualização (1000 entradas)
5. Processa cada novelty disponível
6. Salva resultados no banco
7. Notifica Discord
8. Termina processo (`sys.exit(0)`)

### Processamento Inteligente
- **Cliente Ausente**: "Entramos en contacto..."
- **Problema Cobrança**: "Cliente afirmó que estará con dinero..."
- **Endereço Incorreto**: "Cliente rectificó sus datos..."
- **Rejeição**: "Cliente afirma que quiere el producto..."

## 🐛 Troubleshooting

### ❌ "Nenhuma novelty encontrada"
- Sistema aguarda "Loading..." desaparecer
- Verifica múltiplos seletores de tabela
- Captura screenshot para debug

### ❌ "Linha não encontrada na tabela" 
- Normal - elementos podem sumir após processamento
- Sistema continua com próxima linha
- Não indica falha real

### ❌ Cron não executa
```bash
# Verificar configuração
railway logs --follow

# Forçar execução manual
railway run python chile_background_bot.py
```

### ❌ Login falha
- Verificar credenciais no código
- Confirmar acesso ao site Dropi
- Verificar screenshots salvos

## 📈 Monitoramento

### Health Check
```bash
python monitor.py health  # Verificação completa
```

### Logs
```bash
railway logs | grep ERROR  # Apenas erros
railway logs --follow     # Tempo real
```

### Banco de Dados
```sql
SELECT * FROM execution_history 
WHERE source_country = 'chile' 
ORDER BY execution_date DESC 
LIMIT 10;
```

## 🎯 Vantagens vs Versão Anterior

| Anterior | Atual |
|----------|-------|
| Schedule library + while loop | Railway Native Cron |
| Processo sempre rodando | Execução sob demanda |
| Memory leaks possíveis | Processo limpo |
| Logs confusos | Logs por execução |
| Difícil debug | Chrome visual local |

## 📋 Próximos Passos

1. ✅ Configurar cron schedule no Railway
2. ✅ Fazer deploy do código atualizado  
3. ✅ Verificar primeira execução via logs
4. ✅ Confirmar notificação Discord
5. ✅ Monitorar execuções seguintes

**Sistema otimizado para produção Railway com debug local facilitado!** 🚀