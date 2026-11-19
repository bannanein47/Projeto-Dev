"""Cria contas e itens de demonstração (pode rodar várias vezes sem duplicar).

Uso:  python seed.py
"""
from werkzeug.security import generate_password_hash

import models
from app import create_app

SENHA_DEMO = "Troquei@123"
USUARIOS = [
    ("Ana Souza", "ana@troquei.com"),
    ("Bruno Lima", "bruno@troquei.com"),
    ("Carla Mendes", "carla@troquei.com"),
]

# e-mail  →  [(título, categoria, conservação, descrição)]
ITENS = {
    "ana@troquei.com": [
        ("Coleção Harry Potter (7 livros)", "Livros", "Usado", "Capa mole, todos em bom estado."),
        ("Fone de ouvido Bluetooth", "Eletrônicos", "Seminovo", "Bateria dura umas 8 horas."),
    ],
    "bruno@troquei.com": [
        ("Jaqueta jeans tamanho M", "Roupas e acessórios", "Usado", "Quase sem uso."),
        ("Bola de futebol de campo", "Esportes e lazer", "Seminovo", "Oficial, tamanho 5."),
    ],
    "carla@troquei.com": [
        ("Jogo de tabuleiro Detetive", "Brinquedos e jogos", "Novo", "Lacrado, ganhei repetido."),
        ("Luminária de mesa", "Casa e decoração", "Usado", "Funciona perfeitamente."),
    ],
}

app = create_app()
with app.app_context():
    for nome, email in USUARIOS:
        if models.buscar_por_email(email):
            print(f"já existe: {email}")
            continue
        models.criar_usuario(nome, email, generate_password_hash(SENHA_DEMO))
        print(f"criado:   {email}")
    categorias = {c["nome"]: c["id"] for c in models.listar_categorias()}
    for email, itens in ITENS.items():
        dono = models.buscar_por_email(email)
        if models.listar_itens_do_usuario(dono["id"]):
            continue
        for titulo, categoria, conservacao, descricao in itens:
            models.criar_item(dono["id"], categorias[categoria], titulo, descricao, conservacao, None)
            print(f"item:     {titulo}  ({email})")
    print(f"\nSenha das contas de demonstração: {SENHA_DEMO}")
