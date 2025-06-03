#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORREÇÃO URGENTE para db_connection.py
Substitua a função get_execution_history() existente por esta versão corrigida
"""

import os
import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def is_railway():
    """Verifica se está rodando no Railway"""
    return "RAILWAY_ENVIRONMENT" in os.environ

def get_execution_history(start_date, end_date, country_filter):
    """
    VERSÃO CORRIGIDA - Obtém histórico de execuções do banco de dados
    Corrige o erro de sintaxe SQL com placeholders duplos
    """
    try:
        # Obtém URL do banco
        if is_railway():
            database_url = os.getenv("DATABASE_URL")
        else:
            database_url = os.getenv("LOCAL_DATABASE_URL", os.getenv("DATABASE_URL"))
        
        if not database_url:
            logger.error("URL do banco de dados não configurada")
            return pd.DataFrame()
        
        # Cria engine do SQLAlchemy
        engine = create_engine(database_url)
        
        # Query corrigida com placeholders simples
        base_query = """
            SELECT execution_date, total_processed, successful, failed, execution_time, source_country
            FROM execution_history
            WHERE execution_date BETWEEN %(start_date)s AND %(end_date)s
            AND source_country = %(country_filter)s 
            ORDER BY execution_date DESC
        """
        
        # Parâmetros
        params = {
            'start_date': start_date,
            'end_date': end_date, 
            'country_filter': country_filter
        }
        
        logger.info(f"Executando query para período: {start_date} até {end_date}, país: {country_filter}")
        
        # Executa query
        with engine.connect() as conn:
            df = pd.read_sql_query(text(base_query), conn, params=params)
        
        logger.info(f"Retornadas {len(df)} linhas do histórico")
        return df
        
    except Exception as e:
        logger.error(f"Erro ao buscar histórico de execução: {str(e)}")
        return pd.DataFrame()

def save_execution_result(country, total_processed, successful, failed, execution_time):
    """Salva resultado da execução no banco de dados"""
    try:
        # Obtém URL do banco
        if is_railway():
            database_url = os.getenv("DATABASE_URL")
        else:
            database_url = os.getenv("LOCAL_DATABASE_URL", os.getenv("DATABASE_URL"))
        
        if not database_url:
            logger.error("URL do banco de dados não configurada")
            return False
        
        # Conecta usando psycopg2 diretamente para inserção
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Query de inserção
        insert_query = """
        INSERT INTO execution_history 
        (execution_date, source_country, total_processed, successful, failed, execution_time)
        VALUES (CURRENT_TIMESTAMP, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (country, total_processed, successful, failed, execution_time))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Resultado da execução salvo: {country} - {total_processed} processados")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao salvar resultado da execução: {str(e)}")
        return False

# Função de compatibilidade (se necessário)
def get_connection():
    """Cria conexão direta com PostgreSQL"""
    try:
        if is_railway():
            database_url = os.getenv("DATABASE_URL")
        else:
            database_url = os.getenv("LOCAL_DATABASE_URL", os.getenv("DATABASE_URL"))
        
        if not database_url:
            raise Exception("URL do banco de dados não configurada")
        
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar com o banco de dados: {str(e)}")
        raise