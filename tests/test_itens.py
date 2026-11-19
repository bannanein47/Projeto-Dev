"""Testes automáticos do módulo 2: Categorias e Itens.

Rodar:  python -m unittest discover -s tests -v
"""
import os
import re
import sqlite3
import unittest

from test_usuarios import PNG, Base  # reaproveita ajudantes (cadastro, login, CSRF)


class BaseItens(Base):
    def consulta(self, sql, args=()):
        con = sqlite3.connect(self.app.config["DATABASE"])
        con.row_factory = sqlite3.Row
        r = con.execute(sql, args).fetchall()
        con.close()
        return r

    def dados_item(self, **extra):
        d = {"titulo": "Violão acústico", "category_id": "1", "conservacao": "Usado",
             "descricao": "Cordas de nylon."}
        d.update(extra)
        return d

    def publicar(self, url="/itens/novo", **extra):
        arquivo = extra.pop("arquivo", None)
        d = {"_csrf": self.csrf("/itens/novo"), **self.dados_item(**extra)}
        if arquivo:
            d["foto"] = arquivo
        return self.c.post(url, data=d, content_type="multipart/form-data")

    def sair_e_entrar_como(self, email):
        t = self.csrf("/perfil")
        self.c.post("/sair", data={"_csrf": t})
        self.cadastrar(nome="Outra Pessoa", email=email)
        self.assertEqual(self.entrar(email=email).status_code, 302)


class TestCategorias(BaseItens):
    def test_categorias_padrao_existem(self):
        nomes = [c["nome"] for c in self.consulta("SELECT nome FROM categories")]
        self.assertEqual(len(nomes), 7)
        self.assertIn("Livros", nomes)

    def test_iniciar_de_novo_nao_duplica_categorias(self):
        import app as troquei
        troquei.create_app({"DATABASE": self.app.config["DATABASE"],
                            "UPLOAD_DIR": self.app.config["UPLOAD_DIR"], "SECRET_KEY": "x"})
        self.assertEqual(len(self.consulta("SELECT id FROM categories")), 7)


class TestItens(BaseItens):
    def setUp(self):
        super().setUp()
        self.criar_e_entrar()

    def test_paginas_de_itens_exigem_login(self):
        self.c.post("/sair", data={"_csrf": self.csrf("/perfil")})
        for url in ("/itens", "/itens/novo", "/itens/1/editar"):
            r = self.c.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn("/entrar", r.headers["Location"])

    def test_lista_vazia_convida_a_publicar(self):
        self.assertIn("ainda não anunciou", self.c.get("/itens").get_data(as_text=True))

    def test_publicar_item_valido(self):
        r = self.publicar()
        self.assertEqual(r.status_code, 302)
        itens = self.consulta("SELECT * FROM items")
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["estado"], "disponivel")
        self.assertIn("Violão acústico", self.c.get("/itens").get_data(as_text=True))

    def test_item_fica_ligado_ao_dono(self):
        self.publicar()
        dono = self.consulta("SELECT id FROM users")[0]["id"]
        self.assertEqual(self.consulta("SELECT user_id FROM items")[0]["user_id"], dono)

    def test_titulo_curto_ou_vazio(self):
        for titulo in ("", "ab", "   "):
            self.assertEqual(self.publicar(titulo=titulo).status_code, 400, repr(titulo))
        self.assertEqual(len(self.consulta("SELECT id FROM items")), 0)

    def test_titulo_longo(self):
        self.assertEqual(self.publicar(titulo="x" * 101).status_code, 400)

    def test_descricao_longa_demais(self):
        self.assertEqual(self.publicar(descricao="x" * 1001).status_code, 400)

    def test_categoria_invalida(self):
        for valor in ("", "999", "abc", "-1"):
            self.assertEqual(self.publicar(category_id=valor).status_code, 400, valor)

    def test_conservacao_invalida(self):
        self.assertEqual(self.publicar(conservacao="Perfeito").status_code, 400)

    def test_erro_mantem_o_que_foi_digitado(self):
        r = self.publicar(titulo="Bike", category_id="999")
        self.assertIn('value="Bike"', r.get_data(as_text=True))

    def test_descricao_e_opcional(self):
        self.assertEqual(self.publicar(descricao="").status_code, 302)

    def test_post_sem_csrf_recusado(self):
        r = self.c.post("/itens/novo", data=self.dados_item())
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(self.consulta("SELECT id FROM items")), 0)

    def test_html_escapado(self):
        self.publicar(titulo="<script>alert(1)</script>")
        html = self.c.get("/itens").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    # ---------------------------------------------------------------- foto
    def test_foto_valida_e_gravada(self):
        import io
        self.publicar(arquivo=(io.BytesIO(PNG), "bike.png"))
        foto = self.consulta("SELECT foto FROM items")[0]["foto"]
        self.assertTrue(foto.startswith("items/"))
        self.assertTrue(os.path.isfile(os.path.join(self.app.config["ITEM_UPLOAD_DIR"], foto.split("/")[1])))

    def test_arquivo_falso_recusado(self):
        import io
        r = self.publicar(arquivo=(io.BytesIO(b"<?php echo 1; ?>"), "x.png"))
        self.assertEqual(r.status_code, 400)
        r = self.publicar(arquivo=(io.BytesIO(PNG), "x.exe"))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(self.consulta("SELECT id FROM items")), 0)
        self.assertEqual(os.listdir(self.app.config["ITEM_UPLOAD_DIR"]), [])

    # -------------------------------------------------------------- editar
    def test_editar_item_proprio(self):
        self.publicar()
        r = self.c.post("/itens/1/editar", data={
            "_csrf": self.csrf("/itens/1/editar"),
            **self.dados_item(titulo="Violão clássico", category_id="5", conservacao="Seminovo")},
            content_type="multipart/form-data")
        self.assertEqual(r.status_code, 302)
        i = self.consulta("SELECT * FROM items")[0]
        self.assertEqual((i["titulo"], i["category_id"], i["conservacao"]),
                         ("Violão clássico", 5, "Seminovo"))

    def test_formulario_de_edicao_vem_preenchido(self):
        self.publicar()
        html = self.c.get("/itens/1/editar").get_data(as_text=True)
        self.assertIn('value="Violão acústico"', html)

    def test_editar_com_erro_nao_altera(self):
        self.publicar()
        r = self.c.post("/itens/1/editar", data={
            "_csrf": self.csrf("/itens/1/editar"), **self.dados_item(titulo="a")},
            content_type="multipart/form-data")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.consulta("SELECT titulo FROM items")[0]["titulo"], "Violão acústico")

    def test_trocar_e_remover_foto(self):
        import io
        pasta = self.app.config["ITEM_UPLOAD_DIR"]
        self.publicar(arquivo=(io.BytesIO(PNG), "a.png"))
        primeira = os.listdir(pasta)
        self.assertEqual(len(primeira), 1)
        self.c.post("/itens/1/editar", data={
            "_csrf": self.csrf("/itens/1/editar"), **self.dados_item(), "foto": (io.BytesIO(PNG), "b.png")},
            content_type="multipart/form-data")
        segunda = os.listdir(pasta)
        self.assertEqual(len(segunda), 1)
        self.assertNotEqual(primeira, segunda)           # a antiga foi apagada
        self.c.post("/itens/1/editar", data={
            "_csrf": self.csrf("/itens/1/editar"), **self.dados_item(), "remover_foto": "1"},
            content_type="multipart/form-data")
        self.assertEqual(os.listdir(pasta), [])
        self.assertIsNone(self.consulta("SELECT foto FROM items")[0]["foto"])

    def test_item_inexistente_da_404(self):
        self.assertEqual(self.c.get("/itens/99/editar").status_code, 404)

    # ------------------------------------------------------------- remover
    def test_remover_item(self):
        import io
        self.publicar(arquivo=(io.BytesIO(PNG), "a.png"))
        r = self.c.post("/itens/1/remover", data={"_csrf": self.csrf("/itens")})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(self.consulta("SELECT id FROM items")), 0)
        self.assertEqual(os.listdir(self.app.config["ITEM_UPLOAD_DIR"]), [])

    def test_remover_exige_post(self):
        self.publicar()
        self.assertEqual(self.c.get("/itens/1/remover").status_code, 405)
        self.assertEqual(len(self.consulta("SELECT id FROM items")), 1)

    def test_remover_sem_csrf_recusado(self):
        self.publicar()
        self.assertEqual(self.c.post("/itens/1/remover").status_code, 400)
        self.assertEqual(len(self.consulta("SELECT id FROM items")), 1)

    # ------------------------------------------------ acesso entre usuários
    def test_outro_usuario_nao_edita_nem_remove(self):
        self.publicar()
        self.sair_e_entrar_como("outra@x.com")
        self.assertEqual(self.c.get("/itens/1/editar").status_code, 403)
        r = self.c.post("/itens/1/editar", data={
            "_csrf": self.csrf("/itens"), **self.dados_item(titulo="Invadido")},
            content_type="multipart/form-data")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.c.post("/itens/1/remover", data={"_csrf": self.csrf("/itens")}).status_code, 403)
        i = self.consulta("SELECT titulo FROM items")
        self.assertEqual([x["titulo"] for x in i], ["Violão acústico"])

    def test_lista_mostra_so_os_meus_itens(self):
        self.publicar()
        self.sair_e_entrar_como("outra@x.com")
        self.assertNotIn("Violão acústico", self.c.get("/itens").get_data(as_text=True))

    def test_perfil_resume_os_itens(self):
        self.publicar()
        html = self.c.get("/perfil").get_data(as_text=True)
        self.assertIn("Você tem 1 item anunciado", html)

    def test_excluir_usuario_apaga_seus_itens(self):
        self.publicar()
        con = sqlite3.connect(self.app.config["DATABASE"])
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("DELETE FROM users")
        con.commit()
        self.assertEqual(con.execute("SELECT COUNT(*) FROM items").fetchone()[0], 0)
        con.close()


if __name__ == "__main__":
    unittest.main()
