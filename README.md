# Troquei — Módulos 1 e 2: Usuários, Categorias e Itens

**Módulo 1:** cadastro, entrada, saída, esqueci a senha, CAPTCHA e perfil.
**Módulo 2:** 7 categorias prontas e gerenciamento de itens (anunciar, editar, retirar).
Roda local com Flask + SQLite.

## Como rodar (5 comandos)

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
python seed.py                 # cria 3 contas e 6 itens de demonstração
python app.py                  # abre em http://127.0.0.1:5000
```

Contas de demonstração (senha `Troquei@123`): `ana@troquei.com`, `bruno@troquei.com`, `carla@troquei.com`.

Testes automáticos (64): `python -m unittest discover -s tests -v`

## O que o módulo faz

| Tela | Rota | Regras |
|---|---|---|
| Cadastro | `/cadastro` | nome 2–100; e-mail válido e único (sem diferenciar maiúsculas); senha ≥ 8 com letra e número; confirmação; CAPTCHA |
| Entrar | `/entrar` | CAPTCHA; mensagem genérica de erro; bloqueio 5 min após 5 erros; "manter conectado" 7 dias; `next` só para caminhos internos |
| Sair | `/sair` (POST) | encerra a sessão |
| Esqueci a senha | `/esqueci-senha` | CAPTCHA; resposta igual exista ou não o e-mail; limite de 5 pedidos / 15 min |
| Nova senha | `/redefinir-senha/<token>` | link assinado, vale 1 h e **só 1 uso** (morre quando a senha muda) |
| Perfil | `/perfil` | só logado |
| Editar perfil | `/perfil/editar` | nome, localização, foto (PNG/JPG/WEBP até 2 MB, conferida pelo conteúdo, nome aleatório) |
| Alterar senha | `/perfil/senha` | exige senha atual |
| E-mails (demo) | `/emails-demo` | como não há servidor de e-mail, o link de redefinição aparece aqui e no terminal |

**Segurança:** senha só como hash (Werkzeug/scrypt) · token CSRF em todo POST · cabeçalhos CSP/anti-iframe · SQL com parâmetros · HTML escapado pelo Jinja · sessão renovada no login · CAPTCHA de uso único gerado no servidor (SVG, sem serviço externo).

## Módulo 2: Categorias e Itens

| Tela | Rota | Regras |
|---|---|---|
| Meus itens | `/itens` | só logado; mostra apenas os itens do próprio usuário |
| Novo item | `/itens/novo` | título 3–100; categoria da lista; conservação (Novo, Seminovo, Usado, Com defeitos); descrição até 1000 (opcional); foto PNG/JPG/WEBP até 2 MB (opcional) |
| Editar item | `/itens/<id>/editar` | **só o dono** (outro usuário recebe 403); dá para trocar ou remover a foto |
| Remover item | `/itens/<id>/remover` (POST) | só o dono; apaga o registro e o arquivo da foto; pede confirmação no navegador |

**Banco:** tabelas `categories` (preenchida sozinha com 7 categorias ao iniciar) e `items` (liga `users` e `categories` por chave estrangeira; ao apagar um usuário, seus itens somem junto). Estado do item: `disponivel` ou `trocado` (o `trocado` será usado quando existirem combinações).

**Decisão técnica:** continuamos com `sqlite3` puro (sem SQLAlchemy) para manter o projeto simples e já testado. As fotos de itens ficam em `static/uploads/items/`, com nome aleatório e conferência do conteúdo, reaproveitando o mesmo código das fotos de perfil.

## Front-end e rascunho do Match

Visual novo em **branco, cinza-azulado e roxo**, sem emojis (só HTML/CSS/JS, sem mexer nas regras do servidor) e a página `/match` (**Descobrir**): pilha de cartas para arrastar (Quero trocar / Passar) e janela “É um match!”. As cartas são **dados de exemplo** (rascunho); a ligação com o banco é o próximo módulo. Explicação completa e roteiro: **`GUIA_FRONTEND.md`**.

## Estrutura

```
app.py        rotas, validações, CAPTCHA, token, limites   (Fernando + Pedro)
models.py     tabelas users / emails_demo / categories / items (João)
seed.py       contas de demonstração
templates/    páginas Jinja                                (Arthur)
static/       css/style.css, js/main.js, js/match.js, uploads/avatars e uploads/items
tests/        testes automáticos                           (Matheus)
```

## Roteiro da apresentação (~6 min)

1. **Matheus** (30 s) — mostra o fluxo do guia: criar conta → entrar → perfil, e as regras.
2. **Arthur** (1 min) — abre `/cadastro` no celular (F12 → 360 px): rótulos, medidor de força, "Mostrar senha".
3. **Fernando** (1,5 min) — cadastra. Tenta e-mail repetido, senhas diferentes e CAPTCHA errado. Entra com a conta nova. Explica: navegador → rota → validação → banco → resposta.
4. **João** (1 min) — abre `instance/troquei.db` (DB Browser) ou roda `sqlite3 instance/troquei.db "select id,nome,email,senha_hash from users"`: mostra o hash, nunca a senha.
5. **Pedro** (1,5 min) — erra a senha 5× (bloqueio); "Esqueci a senha" → `/emails-demo` → abre o link → nova senha → tenta o link de novo (recusado) → mostra que `/perfil` sem login manda para o login.
6. **Matheus + Arthur** (1 min) — entram como Ana, publicam um item com foto, editam o título, trocam a categoria e removem. Mostram `/itens` vazio e cheio.
7. **Pedro** (30 s) — entra como Bruno e tenta abrir `/itens/1/editar` (item da Ana): recebe "Acesso negado".
8. **Todos** (30 s) — `python -m unittest discover -s tests -v` mostra 64 testes OK.

## Observações honestas (para dizer ao docente)

- E-mail é simulado (caixa de demonstração). Para e-mail real: defina `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`.
- O CAPTCHA é próprio, para funcionar sem internet. Em produção se usaria reCAPTCHA/hCaptcha.
- O limite de tentativas fica na memória (zera ao reiniciar o servidor).
- O acesso ao banco usa `sqlite3` direto; migrar para Flask-SQLAlchemy mantém as mesmas regras (só `models.py` muda).
- Ainda não existe vitrine: cada pessoa só vê os próprios itens. A vitrine, os likes e as combinações são o próximo módulo.
