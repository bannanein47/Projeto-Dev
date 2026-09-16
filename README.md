# Troquei

O **Troquei** é uma plataforma web de troca de bens entre pessoas. A ideia é simples: cada usuário anuncia aquilo que não lhe serve mais, conhece ofertas de seu interesse e, quando há vontade dos dois lados, pode conversar para combinar a troca.

> Projeto acadêmico de Desenvolvimento Web. As sprints serão semanais e analisadas pelo docente responsável.

## Objetivo

Dar um meio mais organizado, seguro e prático para que duas pessoas interessadas nos itens uma da outra possam realizar uma troca.

## Fluxo principal

1. A pessoa cria sua conta e preenche o perfil.
2. Publica um item que deseja trocar.
3. Encontra no feed itens de acordo com a categoria e a localização.
4. Demonstra interesse (*like*) ou recusa (*dislike*) cada oferta.
5. Há um *match* quando os dois usuários gostam dos itens um do outro.
6. Depois disso, abre-se um chat privado para que possam acertar os detalhes da troca.

## Funcionalidades previstas

- Cadastro e entrada de usuários;
- Perfil com foto e localização;
- Cadastro, edição e retirada de itens;
- Categorias e filtros por distância;
- Feed de ofertas e sistema de *swipe*;
- Likes, dislikes e *matches*;
- Chat entre usuários que deram *match*;
- Armazenamento de imagens e cuidado com os dados.

## Modelo de dados inicial

A primeira tarefa em andamento no Trello é a entidade `Users`, que guardará os dados básicos de cada pessoa:

| Campo | Descrição |
| --- | --- |
| `id` | Identificador único do usuário |
| `nome` | Nome do usuário |
| `email` | E-mail único utilizado no login |
| `senha_hash` | Senha protegida por hash |
| `latitude` / `longitude` | Localização aproximada para filtros de distância |
| `foto_perfil` | Imagem de perfil do usuário |

Mais adiante, serão criadas as entidades `Categories`, `Items`, `Swipes`, `Matches` e `Messages`.

## Organização e responsabilidades

| Área | Responsável | Parte principal |
| --- | --- | --- |
| Planejamento e regras de negócio | Matheus Pereira | Caminhos do usuário, regras de match e categorias |
| Banco de dados | João Victor | Modelagem, tabelas e relacionamentos |
| Back-end e APIs | Fernando Nunes | Login, lógica, rotas e ligação com o banco |
| Front-end | Arthur Castilho | Interface responsiva, telas e interações em JavaScript |
| Armazenamento e segurança | Pedro Vieira | Imagens, proteção de rotas e cuidado com os dados |

## Conhecimentos por área

- **Matheus:** requisitos, caminhos do usuário, regras do sistema e organização no Trello;
- **João Victor:** modelagem de tabelas, SQL, chaves e ligações entre os dados;
- **Fernando:** JavaScript no servidor, APIs, autenticação, banco de dados e segurança básica;
- **Arthur:** HTML bem estruturado, CSS responsivo, JavaScript no navegador e ligação com as APIs;
- **Pedro:** armazenamento de imagens, validação de dados, controle de acesso e proteção contra ataques comuns.

## Sprints semanais

Cada sprint deve ter um objetivo, tarefas divididas, algo que funcione de verdade e pendências anotadas no Trello. Ao fim da semana, o grupo deverá mostrar ao docente:

- o que foi feito;
- o que ainda está sendo feito;
- quais dificuldades apareceram;
- o que fica para a próxima sprint.

## Tecnologias escolhidas

- Front-end: HTML5, CSS3 e JavaScript puro;
- Back-end: Python 3 com Flask;
- Templates: Jinja, servido pelo próprio Flask;
- Banco local: SQLite;
- Banco compartilhado e de produção: PostgreSQL no Supabase;
- Integração com o banco: Flask-SQLAlchemy;
- Proteção de senhas: Werkzeug;
- Imagens, em etapa posterior: Cloudinary;
- Deploy final: Render.

O projeto será mantido em uma única aplicação Flask para tornar o desenvolvimento e o deploy mais simples. Tecnologias mais complexas, como JWT e WebSockets, somente serão acrescentadas depois que as funções essenciais estiverem prontas.

O planejamento detalhado de estudo e execução encontra-se em `PLANO_PROJETO.md`.

## Status atual

**Sprint inicial:** entendimento das necessidades do sistema e modelagem da entidade `Users`.

---

Este README será atualizado a cada sprint, conforme o projeto for tomando forma.
