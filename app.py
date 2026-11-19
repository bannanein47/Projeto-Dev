"""Troquei — Módulo 1: Usuários (cadastro, entrada, saída, senha e perfil)
 e Módulo 2: Categorias e Itens (anunciar, editar e retirar objetos para troca).

Executar:  python app.py   →   http://127.0.0.1:5000
"""
import hashlib
import hmac
import os
import random
import re
import secrets
import smtplib
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from functools import wraps
from urllib.parse import urlparse

from flask import (Flask, Response, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

import models

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
SENHA_MIN, SENHA_MAX = 8, 128
FOTO_MAX_BYTES = 2 * 1024 * 1024
FOTO_EXTENSOES = {"png", "jpg", "jpeg", "webp"}
ITEM_TITULO_MIN, ITEM_TITULO_MAX, ITEM_DESC_MAX = 3, 100, 1000
CONSERVACOES = ["Novo", "Seminovo", "Usado", "Com defeitos"]
# pasta dentro de static/uploads  →  chave da configuração com o caminho no disco
PASTAS_FOTO = {"avatars": "UPLOAD_DIR", "items": "ITEM_UPLOAD_DIR"}
CAPTCHA_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem 0/O, 1/I para não confundir
CAPTCHA_TAMANHO = 5
CAPTCHA_VALIDADE = 300  # segundos

# Hash usado para gastar o mesmo tempo quando o e-mail não existe
# (evita descobrir e-mails cadastrados pelo tempo de resposta).
HASH_FALSO = generate_password_hash("senha-falsa-para-igualar-tempo")


# ====================================================================== fábrica
def create_app(test_config=None):
    app = Flask(__name__)
    instance = os.path.join(BASE_DIR, "instance")
    os.makedirs(instance, exist_ok=True)

    app.config.update(
        DATABASE=os.path.join(instance, "troquei.db"),
        UPLOAD_DIR=os.path.join(BASE_DIR, "static", "uploads", "avatars"),
        MAX_CONTENT_LENGTH=3 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        DEMO_MODE=True,            # mostra a caixa de e-mails de demonstração
        RATE_LIMIT=True,           # bloqueio por excesso de tentativas
        LOGIN_MAX_TENTATIVAS=5,
        LOGIN_JANELA=300,          # segundos
        RESET_MAX_PEDIDOS=5,
        RESET_JANELA=900,
        RESET_TOKEN_MAX_AGE=3600,  # link de redefinição vale 1 hora
    )
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = _chave_secreta(instance)

    app.config.setdefault(
        "ITEM_UPLOAD_DIR", os.path.join(os.path.dirname(app.config["UPLOAD_DIR"]), "items"))
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    os.makedirs(app.config["ITEM_UPLOAD_DIR"], exist_ok=True)
    app.extensions["falhas"] = {}
    models.init_db(app)
    app.teardown_appcontext(models.close_db)

    registrar_hooks(app)
    registrar_rotas(app)
    registrar_erros(app)
    return app


def _chave_secreta(instance):
    """Gera uma chave aleatória na primeira execução e a reutiliza depois."""
    caminho = os.path.join(instance, "secret.key")
    if not os.path.exists(caminho):
        with open(caminho, "w") as f:
            f.write(secrets.token_hex(32))
    with open(caminho) as f:
        return f.read().strip()


# ===================================================================== utilidades
def normalizar_email(valor):
    return (valor or "").strip().lower()


def normalizar_nome(valor):
    return re.sub(r"\s+", " ", (valor or "").strip())


def validar_senha(senha, confirmacao=None):
    """Retorna mensagem de erro (str) ou None."""
    if len(senha) < SENHA_MIN:
        return f"A senha precisa ter pelo menos {SENHA_MIN} caracteres."
    if len(senha) > SENHA_MAX:
        return f"A senha pode ter no máximo {SENHA_MAX} caracteres."
    if not re.search(r"[A-Za-z]", senha) or not re.search(r"\d", senha):
        return "Use pelo menos uma letra e um número."
    if confirmacao is not None and senha != confirmacao:
        return "As senhas não são iguais."
    return None


def destino_seguro(alvo):
    """Aceita só caminhos internos (evita redirecionar para outro site)."""
    if not alvo or not alvo.startswith("/") or alvo.startswith("//") or "\\" in alvo:
        return None
    p = urlparse(alvo)
    if p.scheme or p.netloc:
        return None
    return alvo


def ip_cliente():
    return request.remote_addr or "0.0.0.0"


# --- limite de tentativas (em memória; zera ao reiniciar o servidor)
def _falhas_recentes(chave, janela):
    agora = time.time()
    lista = [t for t in current_falhas().get(chave, []) if agora - t < janela]
    current_falhas()[chave] = lista
    return lista


def current_falhas():
    from flask import current_app
    return current_app.extensions["falhas"]


def segundos_bloqueado(chave, maximo, janela):
    from flask import current_app
    if not current_app.config["RATE_LIMIT"]:
        return 0
    lista = _falhas_recentes(chave, janela)
    if len(lista) >= maximo:
        return max(1, int(janela - (time.time() - lista[0])))
    return 0


def registrar_falha(chave, janela):
    _falhas_recentes(chave, janela)
    current_falhas().setdefault(chave, []).append(time.time())


def limpar_falhas(chave):
    current_falhas().pop(chave, None)


def minutos(segundos):
    m = (segundos + 59) // 60
    return f"{m} minuto" + ("s" if m != 1 else "")


# --- CAPTCHA (gerado no servidor, sem serviços externos)
def novo_captcha():
    codigo = "".join(random.SystemRandom().choice(CAPTCHA_ALFABETO) for _ in range(CAPTCHA_TAMANHO))
    session["captcha"] = {"codigo": codigo, "ate": time.time() + CAPTCHA_VALIDADE}
    return codigo


def conferir_captcha(resposta):
    """Uso único: o código é descartado a cada conferência."""
    dados = session.pop("captcha", None)
    if not dados or time.time() > dados["ate"]:
        return False
    resposta = (resposta or "").strip().upper().replace(" ", "")
    return hmac.compare_digest(resposta, dados["codigo"])


def captcha_svg(codigo):
    rnd = random.SystemRandom()
    w, h = 190, 64
    cores = ["#43299a", "#5b3fc4", "#2d3550", "#6d7a96", "#1f2433"]
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'viewBox="0 0 {w} {h}" role="img" aria-label="Código de verificação">',
         f'<rect width="{w}" height="{h}" rx="10" fill="#f1eefb"/>']
    for _ in range(7):
        p.append(f'<line x1="{rnd.randint(0, w)}" y1="{rnd.randint(0, h)}" '
                 f'x2="{rnd.randint(0, w)}" y2="{rnd.randint(0, h)}" '
                 f'stroke="{rnd.choice(cores)}" stroke-opacity=".35" stroke-width="{rnd.randint(1, 2)}"/>')
    for i, c in enumerate(codigo):
        x = 24 + i * 32 + rnd.randint(-3, 3)
        y = 43 + rnd.randint(-6, 6)
        p.append(f'<text x="{x}" y="{y}" font-size="{rnd.randint(28, 35)}" font-weight="700" '
                 f'font-family="Verdana,Arial,sans-serif" text-anchor="middle" fill="{rnd.choice(cores)}" '
                 f'transform="rotate({rnd.randint(-24, 24)} {x} {y})">{c}</text>')
    for _ in range(3):
        p.append(f'<path d="M0 {rnd.randint(8, h-8)} Q {w//2} {rnd.randint(0, h)} {w} {rnd.randint(8, h-8)}" '
                 f'fill="none" stroke="{rnd.choice(cores)}" stroke-opacity=".5" stroke-width="2"/>')
    p.append("</svg>")
    return "".join(p)


# --- token de redefinição de senha
def _serializador():
    from flask import current_app
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="redefinir-senha")


def _impressao(senha_hash):
    return hashlib.sha256(senha_hash.encode()).hexdigest()[:16]


def gerar_token_reset(usuario):
    # A "impressão" da senha atual faz o link morrer assim que a senha muda (uso único).
    return _serializador().dumps({"uid": usuario["id"], "fp": _impressao(usuario["senha_hash"])})


def validar_token_reset(token):
    """Retorna o usuário se o token for válido; senão None."""
    from flask import current_app
    try:
        dados = _serializador().loads(token, max_age=current_app.config["RESET_TOKEN_MAX_AGE"])
    except (BadSignature, SignatureExpired):
        return None
    usuario = models.buscar_por_id(dados.get("uid"))
    if not usuario or not hmac.compare_digest(dados.get("fp", ""), _impressao(usuario["senha_hash"])):
        return None
    return usuario


# --- envio de e-mail (SMTP se configurado; senão, caixa de demonstração)
def enviar_email(para, assunto, corpo):
    host = os.environ.get("SMTP_HOST")
    if host:
        try:
            msg = EmailMessage()
            msg["From"] = os.environ.get("SMTP_FROM", "troquei@localhost")
            msg["To"], msg["Subject"] = para, assunto
            msg.set_content(corpo)
            with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=10) as s:
                s.starttls()
                if os.environ.get("SMTP_USER"):
                    s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASS", ""))
                s.send_message(msg)
            return
        except Exception as exc:  # cai para a caixa de demonstração
            print(f"[troquei] SMTP falhou ({exc}); usando caixa de demonstração.")
    models.guardar_email_demo(para, assunto, corpo)
    from flask import current_app
    if not current_app.config.get("TESTING"):
        print(f"\n[troquei] E-mail para {para}: {assunto}\n{corpo}\n")


# --- fotos (perfil e itens)
def tipo_da_imagem(cabecalho):
    if cabecalho.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if cabecalho.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if cabecalho[:4] == b"RIFF" and cabecalho[8:12] == b"WEBP":
        return "webp"
    return None


def salvar_foto(arquivo, user_id, pasta="avatars"):
    """Valida e grava a imagem. Retorna (caminho_relativo, erro).

    `pasta` é "avatars" (foto de perfil) ou "items" (foto de item).
    """
    nome_original = (arquivo.filename or "").lower()
    ext = nome_original.rsplit(".", 1)[-1] if "." in nome_original else ""
    if ext not in FOTO_EXTENSOES:
        return None, "Envie uma imagem PNG, JPG ou WEBP."
    dados = arquivo.read(FOTO_MAX_BYTES + 1)
    if len(dados) > FOTO_MAX_BYTES:
        return None, "A foto pode ter no máximo 2 MB."
    tipo = tipo_da_imagem(dados[:16])
    if not tipo:
        return None, "O arquivo não parece uma imagem válida."
    from flask import current_app
    destino = current_app.config[PASTAS_FOTO[pasta]]
    os.makedirs(destino, exist_ok=True)
    nome = f"{pasta[0]}{user_id}_{secrets.token_hex(8)}.{tipo}"   # nome aleatório
    with open(os.path.join(destino, nome), "wb") as f:
        f.write(dados)
    return f"{pasta}/{nome}", None


def apagar_foto(caminho):
    """Apaga o arquivo de um caminho como "avatars/u1_ab12.png" ou "items/i1_cd34.jpg"."""
    if not caminho:
        return
    from flask import current_app
    pasta, _, nome = caminho.partition("/")
    if pasta not in PASTAS_FOTO:
        return
    arq = os.path.join(current_app.config[PASTAS_FOTO[pasta]], os.path.basename(nome))
    if os.path.isfile(arq):
        os.remove(arq)


# --- itens
def validar_item(form):
    """Lê o formulário de item. Retorna (valores, erros)."""
    titulo = normalizar_nome(form.get("titulo"))
    descricao = (form.get("descricao") or "").strip()
    conservacao = form.get("conservacao", "")
    cat_txt = form.get("category_id", "")
    valores = {"titulo": titulo, "descricao": descricao, "conservacao": conservacao,
               "category_id": cat_txt}
    erros = {}
    if not ITEM_TITULO_MIN <= len(titulo) <= ITEM_TITULO_MAX:
        erros["titulo"] = f"Dê um título ao item ({ITEM_TITULO_MIN} a {ITEM_TITULO_MAX} caracteres)."
    if len(descricao) > ITEM_DESC_MAX:
        erros["descricao"] = f"A descrição pode ter no máximo {ITEM_DESC_MAX} caracteres."
    if not (cat_txt.isdigit() and models.buscar_categoria(int(cat_txt))):
        erros["category_id"] = "Escolha uma categoria da lista."
    if conservacao not in CONSERVACOES:
        erros["conservacao"] = "Escolha o estado de conservação."
    return valores, erros


# ================================================================== proteções
def login_required(view):
    @wraps(view)
    def envolto(*args, **kwargs):
        if g.user is None:
            flash("Entre na sua conta para continuar.", "info")
            return redirect(url_for("login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)
    return envolto


def somente_visitante(view):
    @wraps(view)
    def envolto(*args, **kwargs):
        if g.user is not None:
            return redirect(url_for("perfil"))
        return view(*args, **kwargs)
    return envolto


def registrar_hooks(app):
    @app.before_request
    def carregar_usuario_e_csrf():
        g.user = None
        uid = session.get("uid")
        if uid is not None:
            g.user = models.buscar_por_id(uid)
            if g.user is None:
                session.pop("uid", None)
        if request.method == "POST":
            enviado = request.form.get("_csrf", "")
            esperado = session.get("csrf", "")
            if not esperado or not hmac.compare_digest(enviado, esperado):
                return render_template("erro.html", titulo="Formulário expirado",
                                       mensagem="Sua sessão expirou ou o formulário é inválido. "
                                                "Volte, recarregue a página e tente de novo."), 400

    @app.context_processor
    def contexto():
        def csrf_token():
            if "csrf" not in session:
                session["csrf"] = secrets.token_hex(16)
            return session["csrf"]
        return {"csrf_token": csrf_token, "usuario": g.get("user"),
                "demo_mode": app.config["DEMO_MODE"], "captcha_v": secrets.token_hex(4),
                "ano": datetime.now().year}

    @app.template_filter("data")
    def filtro_data(valor):
        if not valor:
            return "—"
        try:
            return datetime.strptime(valor, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y às %H:%M")
        except ValueError:
            return valor

    @app.after_request
    def cabecalhos(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; frame-ancestors 'none'; form-action 'self'")
        if not request.path.startswith("/static/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp


# ======================================================================= rotas
def registrar_rotas(app):

    @app.route("/")
    def index():
        return render_template("index.html")

    # ---------------------------------------------- match (rascunho do front-end)
    @app.route("/match")
    @login_required
    def match():
        # Por enquanto as cartas são dados de exemplo dentro do template.
        # Só enviamos os itens de quem está logado, para escolher o que oferecer.
        return render_template("match.html", meus_itens=models.listar_itens_do_usuario(g.user["id"]))

    # ------------------------------------------------------------- CAPTCHA
    @app.route("/captcha.svg")
    def captcha_imagem():
        resp = Response(captcha_svg(novo_captcha()), mimetype="image/svg+xml")
        resp.headers["Cache-Control"] = "no-store, max-age=0"
        return resp

    # ------------------------------------------------------------- cadastro
    @app.route("/cadastro", methods=["GET", "POST"])
    @somente_visitante
    def cadastro():
        if request.method == "GET":
            return render_template("cadastro.html", erros={}, valores={})

        nome = normalizar_nome(request.form.get("nome"))
        email = normalizar_email(request.form.get("email"))
        senha = request.form.get("senha", "")
        confirma = request.form.get("confirmar_senha", "")
        valores = {"nome": nome, "email": email}
        erros = {}

        if len(nome) < 2 or len(nome) > 100:
            erros["nome"] = "Informe seu nome (2 a 100 caracteres)."
        if not email:
            erros["email"] = "Informe seu e-mail."
        elif len(email) > 254 or not EMAIL_RE.match(email):
            erros["email"] = "Digite um e-mail válido, como nome@exemplo.com."
        msg = validar_senha(senha)
        if msg:
            erros["senha"] = msg
        elif senha != confirma:
            erros["confirmar_senha"] = "As senhas não são iguais."
        if not conferir_captcha(request.form.get("captcha")):
            erros["captcha"] = "Código incorreto ou expirado. Tente o novo código."

        if not erros:
            try:
                models.criar_usuario(nome, email, generate_password_hash(senha))
            except models.EmailJaExiste:
                erros["email"] = "Este e-mail já está cadastrado. Tente entrar ou recuperar a senha."
            else:
                flash("Conta criada com sucesso! Agora é só entrar.", "sucesso")
                return redirect(url_for("login"))
        return render_template("cadastro.html", erros=erros, valores=valores), 400

    # ---------------------------------------------------------------- login
    @app.route("/entrar", methods=["GET", "POST"])
    @somente_visitante
    def login():
        proximo = destino_seguro(request.values.get("next"))
        if request.method == "GET":
            return render_template("login.html", erros={}, valores={}, proximo=proximo)

        email = normalizar_email(request.form.get("email"))
        senha = request.form.get("senha", "")
        valores = {"email": email}
        chave = f"login:{ip_cliente()}:{email}"
        cfg = app.config

        espera = segundos_bloqueado(chave, cfg["LOGIN_MAX_TENTATIVAS"], cfg["LOGIN_JANELA"])
        if espera:
            session.pop("captcha", None)
            return render_template("login.html", valores=valores, proximo=proximo,
                                   erros={"geral": f"Muitas tentativas. Aguarde {minutos(espera)} "
                                                   "ou use “Esqueci a senha”."}), 429

        if not conferir_captcha(request.form.get("captcha")):
            return render_template("login.html", valores=valores, proximo=proximo,
                                   erros={"captcha": "Código incorreto ou expirado. Tente o novo código."}), 400

        usuario = models.buscar_por_email(email)
        confere = check_password_hash(usuario["senha_hash"] if usuario else HASH_FALSO, senha)
        if not usuario or not confere:
            registrar_falha(chave, cfg["LOGIN_JANELA"])
            return render_template("login.html", valores=valores, proximo=proximo,
                                   erros={"geral": "E-mail ou senha incorretos."}), 401

        limpar_falhas(chave)
        lembrar = request.form.get("lembrar") == "1"
        session.clear()  # evita fixação de sessão
        session["uid"] = usuario["id"]
        session.permanent = lembrar
        models.registrar_login(usuario["id"])
        flash(f"Bem-vindo(a) de volta, {usuario['nome'].split()[0]}!", "sucesso")
        return redirect(proximo or url_for("perfil"))

    # ---------------------------------------------------------------- sair
    @app.route("/sair", methods=["GET", "POST"])
    def sair():
        if request.method == "POST":
            session.clear()
            flash("Você saiu da conta.", "info")
        return redirect(url_for("index"))

    # ------------------------------------------------------ esqueci a senha
    @app.route("/esqueci-senha", methods=["GET", "POST"])
    @somente_visitante
    def esqueci_senha():
        if request.method == "GET":
            return render_template("esqueci_senha.html", erros={}, valores={})

        email = normalizar_email(request.form.get("email"))
        valores = {"email": email}
        chave = f"reset:{ip_cliente()}"
        cfg = app.config

        espera = segundos_bloqueado(chave, cfg["RESET_MAX_PEDIDOS"], cfg["RESET_JANELA"])
        if espera:
            session.pop("captcha", None)
            return render_template("esqueci_senha.html", valores=valores,
                                   erros={"geral": f"Muitos pedidos. Aguarde {minutos(espera)}."}), 429
        if not conferir_captcha(request.form.get("captcha")):
            return render_template("esqueci_senha.html", valores=valores,
                                   erros={"captcha": "Código incorreto ou expirado. Tente o novo código."}), 400
        if not email or not EMAIL_RE.match(email):
            return render_template("esqueci_senha.html", valores=valores,
                                   erros={"email": "Digite um e-mail válido."}), 400

        registrar_falha(chave, cfg["RESET_JANELA"])  # conta cada pedido
        usuario = models.buscar_por_email(email)
        if usuario:
            link = url_for("redefinir_senha", token=gerar_token_reset(usuario), _external=True)
            enviar_email(
                email, "Troquei — redefinição de senha",
                f"Olá, {usuario['nome'].split()[0]}!\n\n"
                f"Recebemos um pedido para redefinir sua senha. Use o link abaixo "
                f"(vale por 1 hora e só pode ser usado uma vez):\n\n{link}\n\n"
                "Se não foi você, ignore esta mensagem.")
        # Resposta idêntica exista ou não a conta (não revela quem está cadastrado).
        return redirect(url_for("esqueci_enviado"))

    @app.route("/esqueci-senha/enviado")
    def esqueci_enviado():
        return render_template("esqueci_enviado.html")

    @app.route("/redefinir-senha/<token>", methods=["GET", "POST"])
    def redefinir_senha(token):
        usuario = validar_token_reset(token)
        if usuario is None:
            return render_template("link_invalido.html"), 400
        if request.method == "GET":
            return render_template("redefinir_senha.html", token=token, erros={})

        senha = request.form.get("senha", "")
        msg = validar_senha(senha, request.form.get("confirmar_senha", ""))
        if msg:
            campo = "confirmar_senha" if "iguais" in msg else "senha"
            return render_template("redefinir_senha.html", token=token, erros={campo: msg}), 400

        models.atualizar_senha(usuario["id"], generate_password_hash(senha))
        limpar_falhas(f"login:{ip_cliente()}:{usuario['email']}")
        session.clear()
        flash("Senha redefinida! Entre com a nova senha.", "sucesso")
        return redirect(url_for("login"))

    # --------------------------------------------------------------- perfil
    @app.route("/perfil")
    @login_required
    def perfil():
        return render_template("perfil.html", itens=models.listar_itens_do_usuario(g.user["id"]))

    @app.route("/perfil/editar", methods=["GET", "POST"])
    @login_required
    def editar_perfil():
        if request.method == "GET":
            return render_template("editar_perfil.html", erros={}, valores={
                "nome": g.user["nome"], "localizacao": g.user["localizacao"] or ""})

        nome = normalizar_nome(request.form.get("nome"))
        local = normalizar_nome(request.form.get("localizacao"))
        valores = {"nome": nome, "localizacao": local}
        erros = {}
        if len(nome) < 2 or len(nome) > 100:
            erros["nome"] = "Informe seu nome (2 a 100 caracteres)."
        if len(local) > 100:
            erros["localizacao"] = "A localização pode ter no máximo 100 caracteres."

        foto = g.user["foto_perfil"]
        nova = request.files.get("foto")
        foto_nova = None
        if nova and nova.filename:
            foto_nova, erro = salvar_foto(nova, g.user["id"])
            if erro:
                erros["foto"] = erro
        if erros:
            return render_template("editar_perfil.html", erros=erros, valores=valores), 400

        if foto_nova:
            apagar_foto(foto)
            foto = foto_nova
        elif request.form.get("remover_foto") == "1":
            apagar_foto(foto)
            foto = None
        models.atualizar_perfil(g.user["id"], nome, local or None, foto)
        flash("Perfil atualizado.", "sucesso")
        return redirect(url_for("perfil"))

    @app.route("/perfil/senha", methods=["GET", "POST"])
    @login_required
    def alterar_senha():
        if request.method == "GET":
            return render_template("alterar_senha.html", erros={})

        atual = request.form.get("senha_atual", "")
        nova = request.form.get("senha", "")
        erros = {}
        if not check_password_hash(g.user["senha_hash"], atual):
            erros["senha_atual"] = "A senha atual está incorreta."
        else:
            msg = validar_senha(nova, request.form.get("confirmar_senha", ""))
            if msg:
                erros["confirmar_senha" if "iguais" in msg else "senha"] = msg
            elif nova == atual:
                erros["senha"] = "A nova senha precisa ser diferente da atual."
        if erros:
            return render_template("alterar_senha.html", erros=erros), 400

        models.atualizar_senha(g.user["id"], generate_password_hash(nova))
        flash("Senha alterada com sucesso.", "sucesso")
        return redirect(url_for("perfil"))

    # ---------------------------------------------------------------- itens
    def item_do_dono(item_id):
        """Busca o item e garante que pertence a quem está logado."""
        item = models.buscar_item(item_id)
        if item is None:
            abort(404)
        if item["user_id"] != g.user["id"]:
            abort(403)
        return item

    def tela_item(item, valores, erros, status=200):
        cat_opcoes = [(c["id"], c["nome"]) for c in models.listar_categorias()]
        cons_opcoes = [(c, c) for c in CONSERVACOES]
        return render_template("item_form.html", item=item, valores=valores, erros=erros,
                               cat_opcoes=cat_opcoes, cons_opcoes=cons_opcoes), status

    @app.route("/itens")
    @login_required
    def meus_itens():
        return render_template("itens.html", itens=models.listar_itens_do_usuario(g.user["id"]))

    @app.route("/itens/novo", methods=["GET", "POST"])
    @login_required
    def novo_item():
        if request.method == "GET":
            return tela_item(None, {"conservacao": "Usado"}, {})

        valores, erros = validar_item(request.form)
        foto = None
        enviada = request.files.get("foto")
        if enviada and enviada.filename:
            foto, erro = salvar_foto(enviada, g.user["id"], "items")
            if erro:
                erros["foto"] = erro
        if erros:
            apagar_foto(foto)
            return tela_item(None, valores, erros, 400)

        models.criar_item(g.user["id"], int(valores["category_id"]), valores["titulo"],
                          valores["descricao"] or None, valores["conservacao"], foto)
        flash("Item publicado.", "sucesso")
        return redirect(url_for("meus_itens"))

    @app.route("/itens/<int:item_id>/editar", methods=["GET", "POST"])
    @login_required
    def editar_item(item_id):
        item = item_do_dono(item_id)
        if request.method == "GET":
            return tela_item(item, {
                "titulo": item["titulo"], "descricao": item["descricao"] or "",
                "conservacao": item["conservacao"], "category_id": str(item["category_id"])}, {})

        valores, erros = validar_item(request.form)
        foto = item["foto"]
        foto_nova = None
        enviada = request.files.get("foto")
        if enviada and enviada.filename:
            foto_nova, erro = salvar_foto(enviada, g.user["id"], "items")
            if erro:
                erros["foto"] = erro
        if erros:
            apagar_foto(foto_nova)
            return tela_item(item, valores, erros, 400)

        if foto_nova:
            apagar_foto(foto)
            foto = foto_nova
        elif request.form.get("remover_foto") == "1":
            apagar_foto(foto)
            foto = None
        models.atualizar_item(item_id, int(valores["category_id"]), valores["titulo"],
                              valores["descricao"] or None, valores["conservacao"], foto)
        flash("Item atualizado.", "sucesso")
        return redirect(url_for("meus_itens"))

    @app.route("/itens/<int:item_id>/remover", methods=["POST"])
    @login_required
    def remover_item(item_id):
        item = item_do_dono(item_id)
        apagar_foto(item["foto"])
        models.remover_item(item_id)
        flash("Item removido.", "sucesso")
        return redirect(url_for("meus_itens"))

    # ------------------------------------------- caixa de e-mails (somente demo)
    @app.route("/emails-demo")
    def emails_demo():
        if not app.config["DEMO_MODE"]:
            abort(404)
        emails = []
        for e in models.listar_emails_demo():
            achado = re.search(r"https?://\S+", e["corpo"])
            emails.append({**dict(e), "link": achado.group(0) if achado else None})
        return render_template("emails_demo.html", emails=emails)


# ===================================================================== erros
def registrar_erros(app):
    def pagina(titulo, mensagem, codigo):
        return render_template("erro.html", titulo=titulo, mensagem=mensagem), codigo

    @app.errorhandler(404)
    def _404(_e):
        return pagina("Página não encontrada", "O endereço não existe ou foi movido.", 404)

    @app.errorhandler(403)
    def _403(_e):
        return pagina("Acesso negado", "Você não tem permissão para ver esta página.", 403)

    @app.errorhandler(413)
    def _413(_e):
        return pagina("Arquivo grande demais", "O envio ultrapassou o limite de 3 MB.", 413)

    @app.errorhandler(500)
    def _500(_e):
        return pagina("Algo deu errado", "Tente novamente em instantes.", 500)


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
