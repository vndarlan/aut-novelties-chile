#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exemplo de db_connection.py para integração com PostgreSQL
(Use apenas se não tiver o arquivo original)
"""

import os
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def is_railway():
    """Verifica se está rodando no Railway"""
    return "RAILWAY_ENVIRONMENT" in os.environ

def get_database_url():
    """Obtém a URL do banco de dados"""
    if is_railway():
        # No Railway, a URL geralmente está em DATABASE_URL
        return os.getenv("DATABASE_URL")
    else:
        # Local - configure conforme necessário
        return os.getenv("LOCAL_DATABASE_URL", "postgresql://user:pass@localhost:5432/dbname")

def get_connection():
    """Cria conexão com o banco de dados"""
    try:
        database_url = get_database_url()
        if not database_url:
            raise Exception("URL do banco de dados não configurada")
        
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar com o banco de dados: {str(e)}")
        raise

def get_execution_history(start_date, end_date, country):
    """Obtém histórico de execuções do banco de dados"""
    try:
        conn = get_connection()
        
        query = """
        SELECT 
            execution_date,
            total_processed,
            successful,
            failed,
            execution_time
        FROM automation_executions 
        WHERE execution_date BETWEEN %s AND %s 
        AND country = %s
        ORDER BY execution_date DESC
        """
        
        df = pd.read_sql_query(query, conn, params=[start_date, end_date, country])
        conn.close()
        
        return df
    except Exception as e:
        logger.error(f"Erro ao obter histórico de execuções: {str(e)}")
        return pd.DataFrame()

def save_execution_result(country, total_processed, successful, failed, execution_time):
    """Salva resultado da execução no banco de dados"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Cria tabela se não existir
        create_table_query = """
        CREATE TABLE IF NOT EXISTS automation_executions (
            id SERIAL PRIMARY KEY,
            execution_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            country VARCHAR(50) NOT NULL,
            total_processed INTEGER NOT NULL,
            successful INTEGER NOT NULL,
            failed INTEGER NOT NULL,
            execution_time FLOAT NOT NULL
        );
        """
        
        cursor.execute(create_table_query)
        
        # Insere dados da execução
        insert_query = """
        INSERT INTO automation_executions 
        (country, total_processed, successful, failed, execution_time)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (country, total_processed, successful, failed, execution_time))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Resultado da execução salvo: {country} - {total_processed} processados")
        
    except Exception as e:
        logger.error(f"Erro ao salvar resultado da execução: {str(e)}")
        raise

def create_tables():
    """Cria tabelas necessárias no banco de dados"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Tabela principal de execuções
        create_executions_table = """
        CREATE TABLE IF NOT EXISTS automation_executions (
            id SERIAL PRIMARY KEY,
            execution_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            country VARCHAR(50) NOT NULL,
            total_processed INTEGER NOT NULL,
            successful INTEGER NOT NULL,
            failed INTEGER NOT NULL,
            execution_time FLOAT NOT NULL,
            notes TEXT
        );
        """
        
        # Tabela de logs de erro (opcional)
        create_error_logs_table = """
        CREATE TABLE IF NOT EXISTS automation_error_logs (
            id SERIAL PRIMARY KEY,
            execution_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            country VARCHAR(50) NOT NULL,
            novelty_id VARCHAR(100),
            error_message TEXT NOT NULL,
            error_type VARCHAR(100),
            stack_trace TEXT
        );
        """
        
        cursor.execute(create_executions_table)
        cursor.execute(create_error_logs_table)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("Tabelas criadas/verificadas com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {str(e)}")
        raise

if __name__ == "__main__":
    # Teste de conexão
    try:
        create_tables()
        print("✅ Conexão com banco de dados OK")
    except Exception as e:
        print(f"❌ Erro na conexão: {str(e)}")