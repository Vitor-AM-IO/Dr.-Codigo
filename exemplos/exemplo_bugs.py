# Arquivo de teste do Dr. Código — cheio de problemas de propósito.
# Rode:  code-doctor exemplo_bugs.py --diff
# Aplique:  code-doctor exemplo_bugs.py --apply

import os


def calcular_media(numeros):
    # BUG: quebra com lista vazia (divisão por zero)
    return sum(numeros) / len(numeros)


def buscar_usuario(user_id):
    # BUG: SQL injection — concatena entrada direta na query
    query = "SELECT * FROM usuarios WHERE id = " + user_id
    return query


def ler_config(caminho):
    # BUG: arquivo aberto e nunca fechado (vazamento de recurso)
    f = open(caminho)
    dados = f.read()
    return dados


def dividir(a, b):
    # BUG: sem tratar b == 0
    return a / b


senha_admin = "123456"  # BUG: senha fixa (hardcoded) no código


def processar(itens):
    total = 0
    for i in range(len(itens)):   # pouco idiomático
        total = total + itens[i]
    return total


def get_env(nome):
    # BUG: pode retornar None e ninguém trata
    return os.environ[nome]  # KeyError se não existir
