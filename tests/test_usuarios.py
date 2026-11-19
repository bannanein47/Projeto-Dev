"""Testes automáticos do módulo Usuários.

Rodar:  python -m unittest discover -v
Cobrem os "testes manuais obrigatórios" do guia + login, CAPTCHA, recuperação de senha e perfil.
"""
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as troquei  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
SENHA = "Senha123"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.app = troquei.create_app({
            "TESTING": True, "DATABASE": os.path.join(self.tmp, "t.db"),
            "UPLOAD_DIR": os.path.join(self.tmp, "up"), "SECRET_KEY": "teste",
        })
        self.c = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- ajudantes
    def csrf(self, url="/cadastro"):
        html = self.c.get(url).get_data(as_text=True)
        return re.search(r'name="_csrf" value="([^"]+)"', html).group(1)

    def captcha(self):
        self.c.get("/captcha.svg")
        with self.c.session_transaction() as s:
            return s["captcha"]["codigo"]

    def cadastrar(self, nome="Ana Souza", email="ana@x.com", senha=SENHA, confirma=None, captcha=None):
        t = self.csrf("/cadastro")
        return self.c.post("/cadastro", data={
            "_csrf": t, "nome": nome, "email": email, "senha": senha,
            "confirmar_senha": senha if confirma is None else confirma,
            "captcha": captcha or self.captcha()})

    def entrar(self, email="ana@x.com", senha=SENHA, captcha=None, extra=None):
        t = self.csrf("/entrar")
        d = {"_csrf": t, "email": email, "senha": senha, "captcha": captcha or self.captcha()}
        d.update(extra or {})
        return self.c.post("/entrar", data=d)

    def usuarios(self):
        con = sqlite3.connect(self.app.config["DATABASE"])
        con.row_factory = sqlite3.Row
        r = con.execute("SELECT * FROM users").fetchall()
        con.close()
        return r

    def criar_e_entrar(self):
        self.cadastrar()
        r = self.entrar()
        self.assertEqual(r.status_code, 302)


class TestCadastro(Base):
    def test_cadastro_valido_cria_conta(self):
        r = self.cadastrar()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(self.usuarios()), 1)

    def test_senha_nunca_fica_pura_no_banco(self):
        self.cadastrar()
        u = self.usuarios()[0]
        self.assertNotIn(SENHA, u["senha_hash"])
        self.assertTrue(u["senha_hash"].startswith(("scrypt:", "pbkdf2:")))

    def test_email_repetido_recusado(self):
        self.cadastrar()
        r = self.cadastrar(nome="Outra Pessoa")
        self.assertEqual(r.status_code, 400)
        self.assertIn("já está cadastrado", r.get_data(as_text=True))
        self.assertEqual(len(self.usuarios()), 1)

    def test_email_repetido_ignora_maiusculas(self):
        self.cadastrar(email="ana@x.com")
        r = self.cadastrar(email="  ANA@X.COM ")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(self.usuarios()), 1)

    def test_email_invalido(self):
        for e in ["semarroba", "a@b", "a b@c.com", ""]:
            r = self.cadastrar(email=e)
            self.assertEqual(r.status_code, 400, e)
        self.assertEqual(len(self.usuarios()), 0)

    def test_nome_vazio_ou_curto(self):
        for n in ["", "   ", "A", "x" * 101]:
            self.assertEqual(self.cadastrar(nome=n).status_code, 400, repr(n))
        self.assertEqual(len(self.usuarios()), 0)

    def test_senhas_diferentes(self):
        r = self.cadastrar(confirma="Outra1234")
        self.assertEqual(r.status_code, 400)
        self.assertIn("não são iguais", r.get_data(as_text=True))

    def test_senha_fraca(self):
        for s in ["Ab1", "somenteletras", "12345678"]:
            self.assertEqual(self.cadastrar(senha=s).status_code, 400, s)
        self.assertEqual(len(self.usuarios()), 0)

    def test_reenvio_do_formulario_nao_duplica(self):
        self.cadastrar()
        self.cadastrar()
        self.assertEqual(len(self.usuarios()), 1)

    def test_captcha_errado_bloqueia_cadastro(self):
        r = self.cadastrar(captcha="ZZZZZ")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(self.usuarios()), 0)

    def test_captcha_so_vale_uma_vez(self):
        t = self.csrf("/cadastro")
        cod = self.captcha()
        dados = {"_csrf": t, "nome": "Ana", "email": "a@x.com", "senha": SENHA,
                 "confirmar_senha": SENHA, "captcha": cod}
        self.assertEqual(self.c.post("/cadastro", data=dados).status_code, 302)
        dados["email"] = "b@x.com"
        self.assertEqual(self.c.post("/cadastro", data=dados).status_code, 400)  # mesmo código reutilizado

    def test_post_sem_csrf_recusado(self):
        r = self.c.post("/cadastro", data={"nome": "Ana"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(self.usuarios()), 0)

    def test_html_escapado(self):
        r = self.cadastrar(nome="<script>alert(1)</script>", email="semarroba")
        self.assertNotIn("<script>alert(1)</script>", r.get_data(as_text=True))


class TestLogin(Base):
    def test_login_correto_e_perfil(self):
        self.cadastrar()
        r = self.entrar()
        self.assertEqual(r.status_code, 302)
        self.assertIn("Ana Souza", self.c.get("/perfil").get_data(as_text=True))

    def test_senha_errada_mensagem_generica(self):
        self.cadastrar()
        r = self.entrar(senha="Errada123")
        self.assertEqual(r.status_code, 401)
        self.assertIn("E-mail ou senha incorretos", r.get_data(as_text=True))

    def test_email_inexistente_mesma_mensagem(self):
        r = self.entrar(email="nao@existe.com")
        self.assertEqual(r.status_code, 401)
        self.assertIn("E-mail ou senha incorretos", r.get_data(as_text=True))

    def test_captcha_errado_no_login(self):
        self.cadastrar()
        r = self.entrar(captcha="ZZZZZ")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.c.get("/perfil").status_code, 302)

    def test_bloqueio_apos_5_erros(self):
        self.cadastrar()
        for _ in range(5):
            self.assertEqual(self.entrar(senha="Errada123").status_code, 401)
        r = self.entrar()  # até a senha certa é recusada durante o bloqueio
        self.assertEqual(r.status_code, 429)
        self.assertIn("Muitas tentativas", r.get_data(as_text=True))

    def test_perfil_exige_login_e_volta_ao_destino(self):
        r = self.c.get("/perfil")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/entrar?next=", r.headers["Location"])

    def test_next_seguro_funciona_e_externo_e_ignorado(self):
        self.cadastrar()
        r = self.entrar(extra={"next": "/perfil/editar"})
        self.assertTrue(r.headers["Location"].endswith("/perfil/editar"))
        self.c.post("/sair", data={"_csrf": self.csrf("/")})
        for ruim in ["https://evil.com", "//evil.com", "/\\evil.com", "javascript:alert(1)"]:
            r = self.entrar(extra={"next": ruim})
            self.assertTrue(r.headers["Location"].endswith("/perfil"), ruim)
            self.c.post("/sair", data={"_csrf": self.csrf("/")})

    def test_logout_exige_post_e_encerra_sessao(self):
        self.criar_e_entrar()
        self.c.get("/sair")  # GET não sai
        self.assertEqual(self.c.get("/perfil").status_code, 200)
        self.c.post("/sair", data={"_csrf": self.csrf("/")})
        self.assertEqual(self.c.get("/perfil").status_code, 302)

    def test_logado_nao_ve_login_nem_cadastro(self):
        self.criar_e_entrar()
        self.assertEqual(self.c.get("/entrar").status_code, 302)
        self.assertEqual(self.c.get("/cadastro").status_code, 302)


class TestRecuperacao(Base):
    def pedir(self, email="ana@x.com"):
        t = self.csrf("/esqueci-senha")
        return self.c.post("/esqueci-senha", data={"_csrf": t, "email": email, "captcha": self.captcha()})

    def link(self):
        con = sqlite3.connect(self.app.config["DATABASE"])
        corpo = con.execute("SELECT corpo FROM emails_demo ORDER BY id DESC").fetchone()[0]
        con.close()
        return re.search(r"http://localhost(/redefinir-senha/\S+)", corpo).group(1)

    def redefinir(self, caminho, nova="NovaSenha9", confirma=None):
        t = self.csrf(caminho)
        return self.c.post(caminho, data={"_csrf": t, "senha": nova,
                                          "confirmar_senha": confirma or nova})

    def test_fluxo_completo(self):
        self.cadastrar()
        r = self.pedir()
        self.assertTrue(r.headers["Location"].endswith("/esqueci-senha/enviado"))
        caminho = self.link()
        self.assertEqual(self.redefinir(caminho).status_code, 302)
        self.assertEqual(self.entrar(senha=SENHA).status_code, 401)       # senha antiga morreu
        self.assertEqual(self.entrar(senha="NovaSenha9").status_code, 302)

    def test_link_so_funciona_uma_vez(self):
        self.cadastrar()
        self.pedir()
        caminho = self.link()
        self.assertEqual(self.redefinir(caminho).status_code, 302)
        self.assertEqual(self.c.get(caminho).status_code, 400)

    def test_resposta_igual_para_email_inexistente(self):
        self.cadastrar()
        a = self.pedir("ana@x.com")
        b = self.pedir("ninguem@x.com")
        self.assertEqual(a.status_code, b.status_code)
        self.assertEqual(a.headers["Location"], b.headers["Location"])
        con = sqlite3.connect(self.app.config["DATABASE"])
        self.assertEqual(con.execute("SELECT COUNT(*) FROM emails_demo").fetchone()[0], 1)
        con.close()

    def test_token_invalido_e_expirado(self):
        self.assertEqual(self.c.get("/redefinir-senha/lixo").status_code, 400)
        self.cadastrar()
        self.pedir()
        caminho = self.link()
        self.app.config["RESET_TOKEN_MAX_AGE"] = -1
        self.assertEqual(self.c.get(caminho).status_code, 400)

    def test_senha_fraca_ou_diferente_na_redefinicao(self):
        self.cadastrar()
        self.pedir()
        caminho = self.link()
        self.assertEqual(self.redefinir(caminho, nova="curta").status_code, 400)
        self.assertEqual(self.redefinir(caminho, nova="NovaSenha9", confirma="Outra1234").status_code, 400)
        self.assertEqual(self.redefinir(caminho).status_code, 302)

    def test_captcha_obrigatorio_na_recuperacao(self):
        t = self.csrf("/esqueci-senha")
        r = self.c.post("/esqueci-senha", data={"_csrf": t, "email": "a@x.com", "captcha": "ZZZZZ"})
        self.assertEqual(r.status_code, 400)


class TestPerfil(Base):
    def editar(self, nome="Ana Souza", local="Recife", foto=None, extra=None):
        import io
        t = self.csrf("/perfil/editar")
        d = {"_csrf": t, "nome": nome, "localizacao": local}
        if foto:
            d["foto"] = (io.BytesIO(foto[1]), foto[0])
        d.update(extra or {})
        return self.c.post("/perfil/editar", data=d, content_type="multipart/form-data")

    def test_editar_nome_e_local(self):
        self.criar_e_entrar()
        self.assertEqual(self.editar(nome="Ana Maria", local="Olinda").status_code, 302)
        u = self.usuarios()[0]
        self.assertEqual((u["nome"], u["localizacao"]), ("Ana Maria", "Olinda"))

    def test_nome_vazio_no_perfil(self):
        self.criar_e_entrar()
        self.assertEqual(self.editar(nome=" ").status_code, 400)

    def test_foto_valida_e_removida(self):
        self.criar_e_entrar()
        self.assertEqual(self.editar(foto=("eu.png", PNG)).status_code, 302)
        foto = self.usuarios()[0]["foto_perfil"]
        self.assertTrue(foto.startswith("avatars/"))
        self.assertTrue(os.path.isfile(os.path.join(self.app.config["UPLOAD_DIR"], os.path.basename(foto))))
        self.editar(extra={"remover_foto": "1"})
        self.assertIsNone(self.usuarios()[0]["foto_perfil"])
        self.assertEqual(os.listdir(self.app.config["UPLOAD_DIR"]), [])

    def test_arquivos_proibidos(self):
        self.criar_e_entrar()
        self.assertEqual(self.editar(foto=("x.php", b"<?php ?>")).status_code, 400)
        self.assertEqual(self.editar(foto=("x.png", b"isto nao e imagem")).status_code, 400)
        self.assertEqual(self.editar(foto=("x.png", PNG + b"0" * (2 * 1024 * 1024))).status_code, 400)
        self.assertEqual(os.listdir(self.app.config["UPLOAD_DIR"]), [])

    def test_alterar_senha(self):
        self.criar_e_entrar()
        t = self.csrf("/perfil/senha")
        r = self.c.post("/perfil/senha", data={"_csrf": t, "senha_atual": "errada1X",
                                               "senha": "Nova12345", "confirmar_senha": "Nova12345"})
        self.assertEqual(r.status_code, 400)
        r = self.c.post("/perfil/senha", data={"_csrf": t, "senha_atual": SENHA,
                                               "senha": "Nova12345", "confirmar_senha": "Nova12345"})
        self.assertEqual(r.status_code, 302)
        self.c.post("/sair", data={"_csrf": self.csrf("/")})
        self.assertEqual(self.entrar(senha=SENHA).status_code, 401)
        self.assertEqual(self.entrar(senha="Nova12345").status_code, 302)

    def test_paginas_privadas_exigem_login(self):
        for u in ["/perfil", "/perfil/editar", "/perfil/senha"]:
            self.assertEqual(self.c.get(u).status_code, 302, u)

    def test_cabecalhos_de_seguranca(self):
        r = self.c.get("/")
        self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])
        self.assertEqual(r.headers["X-Frame-Options"], "DENY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
