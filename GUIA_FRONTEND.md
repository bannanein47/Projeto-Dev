# Guia do front-end (para a apresentação)

Tudo aqui foi feito só com **HTML + CSS + um pouco de JavaScript**. O backend (banco, regras, segurança) não mudou; só entrou **uma rota nova** (`/match`) e as **cores do CAPTCHA** passaram de azul para roxo/cinza.

## 1. A ideia visual

- **Branco, cinza-azulado e roxo**, com texto em cinza-azulado bem escuro para ficar legível.
- Formas arredondadas e botões em pílula: a sensação de app de match.
- **Sem emojis, corações ou imagens**: só texto, cores e formas feitas em CSS.
- O que é memorável: a **vitrine roxa do cadastro** (duas cartinhas inclinadas trocando de lugar) e a **pilha de cartas** do match.
- Fonte: pilha de fontes do sistema (sem baixar nada), porque a política de segurança do site só permite arquivos do próprio site.

## 2. Como o CSS está organizado (`static/css/style.css`)

| Parte | O que tem |
|---|---|
| 1) Cores e base | variáveis `--roxo`, `--roxo-vivo`, `--lilas-50`, `--tinta`, `--linha`… **Mudou a variável, mudou o site todo.** |
| 2) Topo e rodapé | menu, logo |
| 3) Botões e formulários | `.botao`, `.campo`, estados de foco e de erro |
| 4) Cadastro | `.duo`, `.vitrine`, `.mini-carta` |
| 5) Perfil e itens | cartões e grade dos módulos anteriores |
| 6) Match | `.baralho`, `.carta`, selos, botões, janela de match |

Por que não tem CSS no HTML? O servidor manda a política de segurança (CSP) `style-src 'self'`, que **bloqueia estilo dentro do HTML**. Então tudo vai no arquivo `.css`.

## 3. Cadastro (`templates/cadastro.html` + `main.js`)

- **Layout em duas colunas** com CSS Grid (`.duo`). No celular vira uma coluna e a vitrine encolhe para um banner.
- **Lista de requisitos da senha**: ✓ aparece enquanto a pessoa digita (8 caracteres, letra, número). O JS só liga/desliga a classe `.ok`.
- **Medidor de força**, **mostrar senha** e **confirmação em tempo real** (já existiam; só trocamos as cores).
- **Acessibilidade**: rótulos em todos os campos, foco visível em roxo, contraste do texto/botões acima de 4,5:1, e se o servidor devolver erro o **foco vai direto ao primeiro campo com problema**.
- Importante: a validação de verdade continua no servidor. O JS é só ajuda visual.

## 4. Match (`/match`: `templates/match.html`, `static/js/match.js`)

**É um rascunho:** as 3 cartas (“Item teste 1 a 3”) são dados de exemplo escritos no topo do `match.html` (lista `perfis`). Isso está escrito na própria tela. Na lista “Oferecer meu item” há a opção de exemplo `testeitem` e, depois dela, os itens reais de quem está logado.

Como funciona:

1. **O HTML** (`match.html`) usa um `for` do Jinja para criar uma `<article class="carta">` por item. Cada carta tem categoria, conservação, dono, local e “aceita em troca”.
2. **O CSS** empilha as cartas uma sobre a outra (`position:absolute`). A de cima é `.pos-0`; as de trás ficam menores e mais baixas (`.pos-1`, `.pos-2`). Isso dá o efeito de baralho.
3. **O JS** faz três coisas:
   - **arrastar** com *pointer events* (funciona com mouse e dedo); a carta gira conforme o arrasto e aparecem os selos TROCO! / PASSO;
   - passou de 90 px → decisão; senão a carta volta;
   - botões “Passar” e “Quero trocar” e as setas do teclado fazem a mesma coisa (teclado e leitor de tela).
4. **Match:** se a carta curtida tem `data-retribuiu="sim"`, abre um `<dialog>` “É um match!” mostrando o item seu e o item dele. (O `<dialog>` do HTML já cuida do foco e da tecla Esc.)
5. Para curtir é preciso escolher qual item seu está sendo oferecido; senão o site avisa.

### O que falta (diga com franqueza)
- Salvar curtidas no banco e buscar itens reais de outras pessoas.
- Detectar o match de verdade (as duas pessoas curtirem).
- Chat/combinar a troca (o botão está desativado com “em breve”).
- Fotos reais nas cartas (hoje há só um bloco colorido com “Foto do item”; um comentário no HTML mostra onde entra o `<img>`).

## 5. Perguntas que o professor pode fazer

- **“Isso é só IA?”** Cada arquivo é pequeno e legível, e cada pessoa deve saber explicar a parte que apresenta. Treinem com este guia e abram o código na hora.
- **“Por que o match é de mentira?”** É a entrega do front-end; o próximo módulo liga ao banco. Os dados de exemplo ficam em um único lugar (`perfis`) e saem dali.
- **“Como o arrastar funciona?”** `pointerdown` guarda o ponto inicial, `pointermove` move a carta (`translateX` + `rotate`), `pointerup` decide pelo limite de 90 px.
- **“Por que usar `<dialog>`?”** Já vem acessível pelo navegador (foco preso na janela, Esc fecha).
- **“Como garantem acessibilidade?”** Rótulos, foco visível, contraste, botões alternativos ao arrastar, avisos para leitor de tela (`aria-live`) e respeito a `prefers-reduced-motion` (sem animações para quem desativa).
- **“Funciona no celular?”** Sim: layout responsivo e arrasto por toque (`touch-action: pan-y` permite rolar a página na vertical).

## 6. Roteiro sugerido (≈ 3 min)

1. Abrir `/cadastro` no computador e depois em 360 px (F12): mostrar a vitrine virando banner.
2. Digitar uma senha e mostrar ✓, medidor e “Mostrar”. Errar o CAPTCHA e mostrar o foco indo ao campo com erro.
3. Entrar como `ana@troquei.com` (senha `Troquei@123`), abrir **Descobrir**, escolher `testeitem`, arrastar a 1ª carta para a direita (**match**) e a 2ª para a esquerda; a 3ª também dá match.
4. Abrir `static/js/match.js` e mostrar as 4 partes comentadas no topo.
