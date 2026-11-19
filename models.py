"""Acesso ao banco SQLite do módulo Usuários (responsável: João + Fernando).

Todas as consultas usam parâmetros (?) para evitar SQL injection.
"""
import os
import sqlite3
from datetime import datetime

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT NOT NULL CHECK (length(nome) BETWEEN 2 AND 100),
    email        TEXT NOT NULL UNIQUE,
    senha_hash   TEXT NOT NULL,
    localizacao  TEXT,
    foto_perfil  TEXT,
    criado_em    TEXT NOT NULL,
    ultimo_login TEXT
);

-- Módulo 2: categorias fixas e itens anunciados para troca
CREATE TABLE IF NOT EXISTS categories (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome  TEXT NOT NULL UNIQUE,
    icone TEXT NOT NULL DEFAULT '📦'
);

CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    titulo      TEXT NOT NULL CHECK (length(titulo) BETWEEN 3 AND 100),
    descricao   TEXT,
    conservacao TEXT NOT NULL,
    foto        TEXT,
    estado      TEXT NOT NULL DEFAULT 'disponivel' CHECK (estado IN ('disponivel', 'trocado')),
    criado_em   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_user ON items(user_id);

-- Caixa de e-mails de demonstração (substitui o envio real de e-mail)
CREATE TABLE IF NOT EXISTS emails_demo (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    para      TEXT NOT NULL,
    assunto   TEXT NOT NULL,
    corpo     TEXT NOT NULL,
    criado_em TEXT NOT NULL
);
"""


CATEGORIAS_PADRAO = [
    ("Livros", "📚"), ("Roupas e acessórios", "👕"), ("Eletrônicos", "🎧"),
    ("Casa e decoração", "🏠"), ("Esportes e lazer", "⚽"),
    ("Brinquedos e jogos", "🧩"), ("Outros", "📦"),
]


class EmailJaExiste(Exception):
    """Já existe uma conta com este e-mail."""


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_erro=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Cria as tabelas se ainda não existirem."""
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    con = sqlite3.connect(app.config["DATABASE"])
    con.executescript(SCHEMA)
    con.executemany("INSERT OR IGNORE INTO categories (nome, icone) VALUES (?, ?)", CATEGORIAS_PADRAO)
    con.commit()
    con.close()


# ----------------------------------------------------------------- usuários
def buscar_por_id(user_id):
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def buscar_por_email(email):
    return get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def criar_usuario(nome, email, senha_hash):
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users (nome, email, senha_hash, criado_em) VALUES (?, ?, ?, ?)",
            (nome, email, senha_hash, agora()),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        raise EmailJaExiste(email)
    return cur.lastrowid


def atualizar_perfil(user_id, nome, localizacao, foto_perfil):
    db = get_db()
    db.execute(
        "UPDATE users SET nome = ?, localizacao = ?, foto_perfil = ? WHERE id = ?",
        (nome, localizacao, foto_perfil, user_id),
    )
    db.commit()


def atualizar_senha(user_id, senha_hash):
    db = get_db()
    db.execute("UPDATE users SET senha_hash = ? WHERE id = ?", (senha_hash, user_id))
    db.commit()


def registrar_login(user_id):
    db = get_db()
    db.execute("UPDATE users SET ultimo_login = ? WHERE id = ?", (agora(), user_id))
    db.commit()


# -------------------------------------------------------- e-mails de demonstração
def guardar_email_demo(para, assunto, corpo):
    db = get_db()
    db.execute(
        "INSERT INTO emails_demo (para, assunto, corpo, criado_em) VALUES (?, ?, ?, ?)",
        (para, assunto, corpo, agora()),
    )
    db.commit()


def listar_emails_demo(limite=20):
    return get_db().execute(
        "SELECT * FROM emails_demo ORDER BY id DESC LIMIT ?", (limite,)
    ).fetchall()


# ---------------------------------------------------------------- categorias
def listar_categorias():
    return get_db().execute("SELECT * FROM categories ORDER BY id").fetchall()


def buscar_categoria(category_id):
    return get_db().execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()


# --------------------------------------------------------------------- itens
_ITEM_SQL = """
    SELECT i.*, c.nome AS categoria_nome, c.icone AS categoria_icone
    FROM items i JOIN categories c ON c.id = i.category_id
"""


def criar_item(user_id, category_id, titulo, descricao, conservacao, foto):
    db = get_db()
    cur = db.execute(
        "INSERT INTO items (user_id, category_id, titulo, descricao, conservacao, foto, criado_em) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, category_id, titulo, descricao, conservacao, foto, agora()),
    )
    db.commit()
    return cur.lastrowid


def buscar_item(item_id):
    return get_db().execute(_ITEM_SQL + " WHERE i.id = ?", (item_id,)).fetchone()


def listar_itens_do_usuario(user_id):
    return get_db().execute(
        _ITEM_SQL + " WHERE i.user_id = ? ORDER BY i.id DESC", (user_id,)
    ).fetchall()


def atualizar_item(item_id, category_id, titulo, descricao, conservacao, foto):
    db = get_db()
    db.execute(
        "UPDATE items SET category_id = ?, titulo = ?, descricao = ?, conservacao = ?, foto = ? "
        "WHERE id = ?",
        (category_id, titulo, descricao, conservacao, foto, item_id),
    )
    db.commit()


def remover_item(item_id):
    db = get_db()
    db.execute("DELETE FROM items WHERE id = ?", (item_id,))
    db.commit()
