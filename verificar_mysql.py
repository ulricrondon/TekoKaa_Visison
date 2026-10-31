"""Prepara o MySQL e testa a persistência em uma tabela temporária isolada."""
import os
import re
from contextlib import contextmanager
from unittest.mock import patch
import mysql.connector
import database


def main():
    nome = os.getenv('MYSQL_DATABASE', 'teko_kaa')
    if not re.fullmatch(r'[A-Za-z0-9_]+', nome):
        raise ValueError('MYSQL_DATABASE deve conter apenas letras, números e sublinhado.')
    with mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', '127.0.0.1'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        connection_timeout=5, read_timeout=5, write_timeout=5,
    ) as banco:
        with banco.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE IF NOT EXISTS `{nome}` CHARACTER SET utf8mb4')
    database.inicializar_banco()
    print('Conexão validada; banco e tabela prontos.')
    with database.conexao() as banco:
        with banco.cursor() as cursor:
            cursor.execute('SHOW CREATE TABLE historico')
            ddl = cursor.fetchone()[1]
            cursor.execute(ddl.replace('CREATE TABLE', 'CREATE TEMPORARY TABLE', 1))
        @contextmanager
        def conexao_teste():
            yield banco
        snapshot = dict(monitoramento_ativo=True, analise_valida=True,
                        indice_saude_visual=80, area_verde=75, exg=0.5,
                        textura=2, status='SAUDÁVEL')
        with patch.object(database, 'conexao', conexao_teste):
            assert database.registrar_se_devido(snapshot)
            assert not database.registrar_se_devido(snapshot)
            assert database.listar_historico()[0]['indiceSaude'] == 80
            database.limpar_historico()
            assert database.listar_historico() == []
    print('Gravação, consulta, intervalo e exclusão validados em tabela temporária.')
    print('Histórico real preservado. Registros existentes:', len(database.listar_historico()))


if __name__ == '__main__':
    try:
        main()
    except mysql.connector.Error as erro:
        print(f'Falha MySQL (código {erro.errno}). Verifique serviço, usuário, senha e permissões no .env.')
        raise SystemExit(1)
