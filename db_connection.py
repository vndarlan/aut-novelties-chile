#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB Connection - Sistema Completo Atualizado
Compatível com Sistema Background e Streamlit
Corrige todos os erros de SQL e threading
"""

import os
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
import logging
from datetime import datetime
import traceback

# Configuração de logging
logger = logging.getLogger(__name__)

def is_railway():
    """Verifica se está rodando no Railway"""
    return "RAILWAY_ENVIRONMENT" in os.environ

def get_database_url():
    """Obtém a URL do banco de dados com fallbacks"""
    try:
        if is_railway():
            # No Railway, prioriza DATABASE_URL
            url = os.getenv("DATABASE_URL")
            if url:
                logger.info("Usando DATABASE_URL do Railway")
                return url
        
        # Fallbacks para desenvolvimento local
        fallbacks = [
            "DATABASE_URL",
            "LOCAL_DATABASE_URL", 
            "POSTGRES_URL",
            "DB_URL"
        ]
        
        for var_name in fallbacks:
            url = os.getenv(var_name)
            if url:
                logger.info(f"Usando {var_name} para conexão")
                return url
        
        # URL padrão para desenvolvimento (se nada configurado)
        default_url = "postgresql://user:pass@localhost:5432/dbname"
        logger.warning(f"Nenhuma URL configurada, usando padrão: {default_url}")
        return default_url
        
    except Exception as e:
        logger.error(f"Erro ao obter URL do banco: {str(e)}")
        raise

def get_connection():
    """Cria conexão direta com PostgreSQL usando psycopg2"""
    try:
        database_url = get_database_url()
        if not database_url:
            raise Exception("URL do banco de dados não configurada")
        
        conn = psycopg2.connect(database_url)
        logger.debug("Conexão PostgreSQL estabelecida com sucesso")
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar com o banco de dados: {str(e)}")
        raise

def get_sqlalchemy_engine():
    """Cria engine SQLAlchemy para pandas operations"""
    try:
        database_url = get_database_url()
        if not database_url:
            raise Exception("URL do banco de dados não configurada")
        
        engine = create_engine(database_url, echo=False)
        logger.debug("Engine SQLAlchemy criada com sucesso")
        return engine
    except Exception as e:
        logger.error(f"Erro ao criar engine SQLAlchemy: {str(e)}")
        raise

def create_tables():
    """Cria tabelas necessárias no banco de dados"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Tabela principal de execuções (com nome compatível)
        create_executions_table = """
        CREATE TABLE IF NOT EXISTS execution_history (
            id SERIAL PRIMARY KEY,
            execution_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_country VARCHAR(50) NOT NULL,
            total_processed INTEGER NOT NULL DEFAULT 0,
            successful INTEGER NOT NULL DEFAULT 0,
            failed INTEGER NOT NULL DEFAULT 0,
            execution_time FLOAT NOT NULL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Índices para performance
        create_indexes = """
        CREATE INDEX IF NOT EXISTS idx_execution_history_date 
        ON execution_history(execution_date);
        
        CREATE INDEX IF NOT EXISTS idx_execution_history_country 
        ON execution_history(source_country);
        
        CREATE INDEX IF NOT EXISTS idx_execution_history_date_country 
        ON execution_history(execution_date, source_country);
        """
        
        # Tabela de logs de erro detalhados (opcional)
        create_error_logs_table = """
        CREATE TABLE IF NOT EXISTS automation_error_logs (
            id SERIAL PRIMARY KEY,
            execution_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            country VARCHAR(50) NOT NULL,
            novelty_id VARCHAR(100),
            error_message TEXT NOT NULL,
            error_type VARCHAR(100),
            stack_trace TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        cursor.execute(create_executions_table)
        cursor.execute(create_indexes)
        cursor.execute(create_error_logs_table)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("Tabelas e índices criados/verificados com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def get_execution_history(start_date, end_date, country_filter):
    """
    Obtém histórico de execuções do banco de dados
    CORRIGIDO: Placeholders SQL simples para compatibilidade total
    """
    try:
        logger.info(f"Buscando histórico: {start_date} até {end_date}, país: {country_filter}")
        
        engine = get_sqlalchemy_engine()
        
        # Query SQL corrigida com placeholders simples
        base_query = """
            SELECT 
                execution_date,
                total_processed,
                successful,
                failed,
                execution_time,
                source_country,
                notes
            FROM execution_history
            WHERE execution_date BETWEEN %(start_date)s AND %(end_date)s
            AND source_country = %(country_filter)s 
            ORDER BY execution_date DESC
            LIMIT 1000
        """
        
        # Parâmetros seguros
        params = {
            'start_date': start_date,
            'end_date': end_date, 
            'country_filter': str(country_filter)
        }
        
        logger.debug(f"Executando query com parâmetros: {params}")
        
        # Executa query com engine
        with engine.connect() as conn:
            df = pd.read_sql_query(text(base_query), conn, params=params)
        
        logger.info(f"Histórico obtido: {len(df)} registros encontrados")
        
        # Se não encontrou dados, retorna DataFrame vazio com colunas esperadas
        if df.empty:
            logger.info("Nenhum registro encontrado para o período especificado")
            empty_df = pd.DataFrame(columns=[
                'execution_date', 'total_processed', 'successful', 
                'failed', 'execution_time', 'source_country', 'notes'
            ])
            return empty_df
        
        return df
        
    except Exception as e:
        logger.error(f"Erro ao buscar histórico de execução: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Retorna DataFrame vazio em caso de erro
        empty_df = pd.DataFrame(columns=[
            'execution_date', 'total_processed', 'successful', 
            'failed', 'execution_time', 'source_country', 'notes'
        ])
        return empty_df

def save_execution_result(country, total_processed, successful, failed, execution_time, notes=None):
    """
    Salva resultado da execução no banco de dados
    MELHORADO: Mais robusto com verificações e logs detalhados
    """
    try:
        logger.info(f"Salvando resultado: {country} - {total_processed} processados, {successful} sucessos, {failed} falhas")
        
        # Validações básicas
        if not country:
            raise ValueError("País é obrigatório")
        
        if total_processed < 0 or successful < 0 or failed < 0:
            raise ValueError("Valores não podem ser negativos")
        
        if execution_time < 0:
            raise ValueError("Tempo de execução não pode ser negativo")
        
        # Conecta e insere
        conn = get_connection()
        cursor = conn.cursor()
        
        # Query de inserção
        insert_query = """
        INSERT INTO execution_history 
        (execution_date, source_country, total_processed, successful, failed, execution_time, notes)
        VALUES (CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, %s)
        RETURNING id, execution_date
        """
        
        cursor.execute(insert_query, (
            str(country), 
            int(total_processed), 
            int(successful), 
            int(failed), 
            float(execution_time),
            notes
        ))
        
        # Obtém ID e data da inserção
        result = cursor.fetchone()
        execution_id, execution_date = result
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Resultado salvo com sucesso: ID {execution_id}, Data: {execution_date}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao salvar resultado da execução: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def save_error_log(country, novelty_id, error_message, error_type=None, stack_trace=None):
    """
    Salva log de erro detalhado no banco de dados
    NOVO: Para melhor debugging e monitoramento
    """
    try:
        logger.debug(f"Salvando log de erro: {country} - {novelty_id} - {error_type}")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO automation_error_logs 
        (country, novelty_id, error_message, error_type, stack_trace)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            str(country),
            str(novelty_id) if novelty_id else None,
            str(error_message)[:1000],  # Limita tamanho da mensagem
            str(error_type)[:100] if error_type else None,
            str(stack_trace)[:5000] if stack_trace else None  # Limita tamanho do stack trace
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.debug("Log de erro salvo com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao salvar log de erro: {str(e)}")
        return False

def get_latest_execution_stats(country, days=7):
    """
    Obtém estatísticas das últimas execuções
    NOVO: Para dashboards e monitoramento
    """
    try:
        engine = get_sqlalchemy_engine()
        
        query = """
        SELECT 
            DATE(execution_date) as execution_day,
            COUNT(*) as executions_count,
            SUM(total_processed) as total_processed,
            SUM(successful) as total_successful,
            SUM(failed) as total_failed,
            AVG(execution_time) as avg_execution_time,
            MAX(execution_date) as last_execution
        FROM execution_history 
        WHERE source_country = %(country)s 
        AND execution_date >= CURRENT_DATE - INTERVAL '%(days)s days'
        GROUP BY DATE(execution_date)
        ORDER BY execution_day DESC
        """
        
        params = {'country': str(country), 'days': int(days)}
        
        with engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn, params=params)
        
        logger.info(f"Estatísticas obtidas: {len(df)} dias de dados")
        return df
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        return pd.DataFrame()

def test_database_connection():
    """
    Testa conexão com o banco de dados
    NOVO: Para diagnósticos e health checks
    """
    try:
        logger.info("Testando conexão com banco de dados...")
        
        # Teste com psycopg2
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test, CURRENT_TIMESTAMP as now")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        logger.info(f"Conexão testada com sucesso: {result}")
        
        # Teste com SQLAlchemy
        engine = get_sqlalchemy_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
        
        logger.info(f"PostgreSQL version: {version[:50]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"Falha no teste de conexão: {str(e)}")
        return False

def cleanup_old_logs(days_to_keep=90):
    """
    Remove logs antigos para manter o banco limpo
    NOVO: Manutenção automática
    """
    try:
        logger.info(f"Limpando logs mais antigos que {days_to_keep} dias...")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Remove execuções antigas (mantém estatísticas principais)
        cleanup_executions = """
        DELETE FROM execution_history 
        WHERE execution_date < CURRENT_DATE - INTERVAL '%s days'
        AND id NOT IN (
            SELECT id FROM execution_history 
            WHERE execution_date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY execution_date DESC 
            LIMIT 1000
        )
        """
        
        # Remove logs de erro antigos
        cleanup_errors = """
        DELETE FROM automation_error_logs 
        WHERE execution_date < CURRENT_DATE - INTERVAL '%s days'
        """
        
        cursor.execute(cleanup_executions, (days_to_keep, days_to_keep))
        executions_deleted = cursor.rowcount
        
        cursor.execute(cleanup_errors, (days_to_keep,))
        errors_deleted = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Limpeza concluída: {executions_deleted} execuções e {errors_deleted} logs de erro removidos")
        return True
        
    except Exception as e:
        logger.error(f"Erro na limpeza de logs: {str(e)}")
        return False

# Aliases para compatibilidade com código antigo
def get_execution_history_legacy(start_date_str, end_date_str, country):
    """Alias para compatibilidade com versões antigas"""
    return get_execution_history(start_date_str, end_date_str, country)

# Inicialização automática
def initialize_database():
    """Inicializa o banco de dados automaticamente"""
    try:
        logger.info("Inicializando banco de dados...")
        
        # Testa conexão
        if not test_database_connection():
            raise Exception("Falha no teste de conexão")
        
        # Cria tabelas
        if not create_tables():
            raise Exception("Falha na criação de tabelas")
        
        logger.info("Banco de dados inicializado com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Falha na inicialização do banco: {str(e)}")
        return False

# Executa inicialização quando módulo é importado
if __name__ == "__main__":
    # Teste standalone
    logging.basicConfig(level=logging.INFO)
    
    print("=== TESTE DB CONNECTION ===")
    
    if initialize_database():
        print("✅ Banco inicializado com sucesso")
        
        # Teste de inserção
        if save_execution_result("teste", 10, 8, 2, 120.5, "Teste de inserção"):
            print("✅ Inserção testada com sucesso")
        
        # Teste de consulta
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        df = get_execution_history(start_date, end_date, "teste")
        print(f"✅ Consulta testada: {len(df)} registros")
        
    else:
        print("❌ Falha na inicialização")
else:
    # Inicialização silenciosa quando importado
    try:
        initialize_database()
    except:
        pass  # Falha silenciosa na importação