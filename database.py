"""Histórico persistente no MySQL, independente do navegador."""
import os
import threading
from contextlib import contextmanager
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name('.env'))
historico_lock = threading.Lock()


@contextmanager
def conexao():
    banco = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', '127.0.0.1'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database=os.getenv('MYSQL_DATABASE', 'teko_kaa'),
        connection_timeout=5, read_timeout=5, write_timeout=5,
        charset='utf8mb4',
    )
    try:
        yield banco
    finally:
        banco.close()


def inicializar_banco():
    with conexao() as banco, banco.cursor() as cursor:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico (
                id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                timestamp BIGINT NOT NULL,
                indice_saude DOUBLE NOT NULL,
                area_verde DOUBLE NOT NULL,
                exg DOUBLE NOT NULL,
                textura DOUBLE NOT NULL,
                status VARCHAR(80) NOT NULL,
                INDEX idx_historico_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        banco.commit()


def registrar_se_devido(snapshot):
    if (not snapshot.get('monitoramento_ativo') or not snapshot.get('analise_valida')
            or snapshot.get('status') not in ('SAUDÁVEL', 'ATENÇÃO', 'NÃO SAUDÁVEL')):
        return False
    with historico_lock, conexao() as banco, banco.cursor() as cursor:
        cursor.execute('SELECT CAST(UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3)) * 1000 AS UNSIGNED)')
        agora = int(cursor.fetchone()[0])
        cursor.execute('SELECT timestamp FROM historico ORDER BY timestamp DESC LIMIT 1')
        ultimo = cursor.fetchone()
        if ultimo and agora - int(ultimo[0]) < 60 * 60 * 1000:
            return False
        cursor.execute('''
            INSERT INTO historico
                (timestamp, indice_saude, area_verde, exg, textura, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (agora, float(snapshot['indice_saude_visual']),
              float(snapshot['area_verde']), float(snapshot['exg']),
              float(snapshot['textura']), snapshot['status']))
        banco.commit()
        return True


def listar_historico():
    with conexao() as banco, banco.cursor(dictionary=True) as cursor:
        cursor.execute('''
            SELECT id, timestamp, indice_saude AS indiceSaude,
                   area_verde AS areaVerde, exg, textura, status
            FROM historico ORDER BY timestamp DESC, id DESC
        ''')
        return cursor.fetchall()


def limpar_historico():
    with historico_lock, conexao() as banco, banco.cursor() as cursor:
        cursor.execute('DELETE FROM historico')
        banco.commit()


if __name__ == '__main__':
    inicializar_banco()
    print('Conexão MySQL validada; tabela de histórico pronta.')
