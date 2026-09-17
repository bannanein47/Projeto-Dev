# Troquei

O **Troquei** é um projeto acadêmico do IFPE para criação de um site de troca de objetos entre pessoas. A proposta é permitir que cada usuário crie uma conta, cadastre itens que deseja trocar, veja itens de outras pessoas e demonstre interesse neles.

Quando existe interesse recíproco entre **dois itens específicos**, o sistema cria uma combinação (*match*). A partir dela, os participantes podem conversar para acertar os detalhes da troca e, depois, marcá-la como concluída.

O objetivo desta versão não é lançar um produto público ou comercial. O foco é construir um fluxo menor, mas completo, que funcione localmente, possa ser testado pelo grupo e seja compreendido e explicado por todos durante as avaliações.

## Marcos do projeto

- **Primeira apresentação:** 7 de outubro de 2026.
- **Objetivo da primeira apresentação:** cadastro, entrada, categorias e gerenciamento de itens funcionando localmente.
- **Entrega final:** última semana de novembro de 2026.
- **Objetivo final:** demonstrar o fluxo completo, com dados salvos, testes realizados e cada integrante capaz de explicar sua parte.

## Fluxo principal do usuário

1. **Criar conta** — nome, e-mail e senha.
2. **Entrar** — a sessão identifica o usuário.
3. **Cadastrar item** — foto, categoria e descrição.
4. **Ver a vitrine** — visualizar itens disponíveis de outras pessoas.
5. **Avaliar** — marcar “gostei” ou “não gostei”.
6. **Combinar** — o sistema detecta interesse recíproco entre dois itens.
7. **Conversar** — os participantes trocam mensagens dentro da combinação.
8. **Concluir** — a troca é encerrada e os itens deixam de aparecer na vitrine.

## Escopo desta versão

### Entra no projeto

- cadastro, entrada, saída e perfil;
- categorias e gerenciamento de itens;
- vitrine com filtros;
- decisões de gostei e não gostei;
- combinações por interesse recíproco;
- mensagens simples entre os participantes de uma combinação;
- proteção de senha;
- validação de dados e controle básico de acesso;
- upload/localização de imagens dentro da estrutura do projeto;
- dados preparados para demonstração e testes.

### Fica para uma versão futura

- aplicativo móvel;
- publicação do sistema na internet;
- mapas e cálculo de distância real;
- biometria ou verificação documental;
- chat em tempo real e notificações;
- pagamentos;
- inteligência artificial integrada ao produto;
- estrutura de segurança de nível empresarial.

## Tecnologias

| Ferramenta | Uso no projeto | Responsáveis principais |
| --- | --- | --- |
| Python 3 | Regras do sistema | Fernando e João |
| Flask | Servidor local e rotas | Fernando |
| HTML5 | Estrutura das páginas | Arthur |
| CSS3 | Aparência e responsividade | Arthur |
| JavaScript | Interações pequenas no navegador | Arthur |
| Jinja | Inserção dos dados do Flask nas páginas | Fernando e Arthur |
| SQLite | Banco de dados em arquivo local | João e Fernando |
| Flask-SQLAlchemy | Modelos e consultas ao banco | João e Fernando |
| Werkzeug | Proteção das senhas | Fernando e Pedro |
| GitHub | Versionamento e compartilhamento do código | Todos |
| Trello | Organização das tarefas e evidências | Todos |

A aplicação será executada **localmente**. Nesta versão não é necessário contratar hospedagem, domínio ou serviços externos para o funcionamento principal.

## Caminho de uma ação no sistema

```text
Navegador
   ↓
Flask
   ↓
Validação das regras
   ↓
SQLAlchemy
   ↓
SQLite
   ↓
Jinja
   ↓
Página devolvida ao navegador
```

## Estrutura inicial do projeto

```text
Troquei/
├── app.py
├── models.py
├── seed.py
├── templates/
├── static/
│   ├── css/
│   ├── js/
│   └── uploads/
└── instance/
    └── troquei.db
```

- `app.py`: inicia o Flask e concentra o ponto de entrada da aplicação.
- `models.py`: armazena os modelos do banco.
- `templates/`: páginas renderizadas com Jinja.
- `static/css/`: estilos da interface.
- `static/js/`: interações no navegador.
- `static/uploads/`: imagens enviadas para o projeto.
- `instance/troquei.db`: banco SQLite local.
- `seed.py`: prepara dados de demonstração.

## Banco de dados

O modelo atual possui **seis entidades principais**.

| Entidade | Campos principais |
| --- | --- |
| `Users` | `id`, `nome`, `email`, `senha_hash`, localização opcional, `foto_perfil` |
| `Categories` | `id`, `nome`, `icone` |
| `Items` | `id`, `user_id`, `category_id`, título, descrição, foto, conservação, estado |
| `Swipes` | `id`, `user_id`, `target_item_id`, ação, `criado_em` |
| `Matches` | `id`, `item_a_id`, `item_b_id`, estado, `criado_em` |
| `Messages` | `id`, `match_id`, `sender_id`, conteúdo, `criado_em`, lida |

### Relações principais

```text
Usuário ── publica ──> Itens
Categoria ── organiza ──> Itens
Usuário ── realiza ──> Avaliações
Itens ── formam ──> Combinação
Combinação ── possui ──> Mensagens
```

## Primeiro cartão: `Users`

O primeiro foco do desenvolvimento é a entidade de usuários, porque ela serve de base para login, propriedade dos itens, avaliações e mensagens.

### Campos previstos

| Campo | Regra |
| --- | --- |
| `id` | automático e único |
| `nome` | entre 2 e 100 caracteres |
| `email` | obrigatório e único |
| `senha_hash` | nunca deve guardar a senha pura |
| `latitude` / `longitude` | opcionais no protótipo |
| `foto_perfil` | caminho da imagem ou imagem padrão |

### Fluxo do cadastro

```text
Preencher → Validar → Consultar e-mail → Proteger senha → Salvar → Responder
```

### Critérios para considerar o cartão concluído

- aplicação abre sem erro;
- tabela de usuários existe;
- cadastro válido cria uma conta;
- e-mail repetido é recusado;
- senha pura não aparece no banco;
- pelo menos dois integrantes conseguem executar o projeto.

### Testes manuais obrigatórios

- cadastro válido;
- e-mail repetido;
- e-mail inválido;
- nome vazio;
- senhas diferentes;
- senha abaixo do mínimo;
- conferência do hash armazenado no banco;
- atualização da página sem criação de duplicata.

## Regra de combinação (*match*)

A combinação acontece entre **dois itens específicos**, e não apenas entre duas pessoas.

Exemplo:

```text
Ana gosta de um item de Bruno
              +
Bruno gosta de um item disponível de Ana
              =
        Combinação ativa
```

Antes de criar uma combinação, o sistema deve verificar se:

- o item avaliado pertence a outra pessoa;
- o usuário ainda não avaliou aquele item;
- os dois itens continuam disponíveis;
- existe interesse recíproco;
- o mesmo par de itens ainda não possui uma combinação.

Quando a troca é concluída:

- a combinação recebe o estado `concluido`;
- os dois itens recebem o estado `trocado`;
- os itens deixam de aparecer na vitrine;
- o histórico continua disponível aos participantes.

## Organização da equipe

| Integrante | Área principal |
| --- | --- |
| Matheus Pereira | Planejamento e regras de negócio |
| João Victor | Banco de dados e modelagem |
| Fernando Nunes | Back-end / servidor |
| Arthur Castilho | Front-end / interface |
| Pedro Vieira | Segurança básica e armazenamento |

A divisão indica o foco principal de cada pessoa, mas o projeto deve continuar integrado. As partes não devem ser desenvolvidas como sistemas separados.

## Cronograma

As entregas são semanais. Ao final de cada semana deve existir algo pequeno, funcional e demonstrável.

| Semana | Período | Foco | Entrega esperada |
| ---: | --- | --- | --- |
| 1 | 17–23 de setembro | Base e usuários | Flask abre e a tabela de usuários pode ser criada |
| 2 | 24–30 de setembro | Conta e categorias | Usuário cria conta, entra, vê o perfil e sai |
| 3 | 1–7 de outubro | Itens e primeira avaliação | Demonstração parcial completa em 7 de outubro |
| 4 | 8–14 de outubro | Correções e vitrine | Vitrine funciona com e sem dados |
| 5 | 15–21 de outubro | Filtros e clareza | Categoria escolhida altera a vitrine |
| 6 | 22–28 de outubro | Gostei e não gostei | Decisão permanece salva após reabrir o sistema |
| 7 | 29 de outubro–4 de novembro | Combinações | Duas contas enxergam a mesma combinação |
| 8 | 5–11 de novembro | Mensagens | Participantes enviam e leem mensagens ao atualizar |
| 9 | 12–18 de novembro | Fotos e proteção | Arquivo inválido é recusado e item trocado sai da vitrine |
| 10 | 19–25 de novembro | Integração e testes | Fluxo completo funciona em dois computadores |
| 11 | 26–30 de novembro | Ensaio e entrega | Apresentação completa com cópia e plano alternativo |

## Método de trabalho

O grupo deve aprender apenas o necessário para a tarefa atual e aplicar o conteúdo logo em seguida:

```text
Escolher → Compreender → Reproduzir → Aplicar → Testar e explicar
```

A proposta é evitar código que funcione sem que ninguém saiba explicar. Antes de aplicar algo diretamente no Troquei, a pessoa deve entender o conceito, reproduzir um exemplo menor e só então levar a solução ao projeto.

## Organização no Trello

Fluxo sugerido dos cartões:

```text
Ideias futuras
    ↓
Lista de tarefas
    ↓
Semana atual
    ↓
Em andamento
    ↓
Revisão e teste
    ↓
Concluído
```

### Regras de trabalho

- **Regra dos 40 minutos:** se não houver progresso, registrar o que foi tentado, copiar o erro, reduzir o problema e pedir ajuda com contexto.
- **Uma tarefa por vez:** cada pessoa mantém apenas um cartão principal em “Em andamento”.
- **Integração frequente:** interface e servidor devem ser integrados pelo menos duas vezes por semana.

### Um cartão só está concluído quando possui

- código integrado;
- teste executado;
- captura de tela ou vídeo curto como evidência;
- registro de versão identificável;
- explicação de quem realizou a tarefa;
- critérios de conclusão marcados.

## Definição de pronto da entrega final

### Conta e itens

- [ ] Cadastro, entrada e saída funcionam.
- [ ] Senha está protegida.
- [ ] Dono consegue criar, editar e excluir seus itens.
- [ ] Fotos válidas aparecem corretamente.

### Troca

- [ ] Vitrine e filtros funcionam.
- [ ] Decisões de gostei/não gostei ficam salvas.
- [ ] Interesse cruzado cria uma combinação.
- [ ] Participantes conseguem trocar mensagens.

### Apresentação

- [ ] Projeto testado em dois computadores.
- [ ] Contas e itens de teste preparados.
- [ ] Cópia de segurança pronta.
- [ ] Cada integrante consegue explicar sua parte.

> O projeto está pronto quando o grupo consegue **executar, demonstrar, testar e explicar**. Muitas telas não substituem um fluxo menor que funciona de ponta a ponta.

## Guia de estudo e planejamento

O arquivo `GUIA_TROQUEI.html` concentra o plano visual do projeto, incluindo mapas mentais, cronograma, trilhas de estudo, guias em português, responsabilidades e critérios de entrega.

---

Este README deve ser atualizado conforme o projeto avance e decisões do grupo forem alteradas.
