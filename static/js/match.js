/* Troquei — página de match (rascunho).
   O que este arquivo faz, em 4 partes:
   1) mostra só as 3 primeiras cartas da pilha (a de cima + duas atrás)
   2) deixa arrastar a carta de cima (mouse ou dedo) — passou do limite = decisão
   3) botões Passar e Quero trocar e setas do teclado fazem a mesma decisão
   4) se o dono também curtiu um item seu (data-retribuiu="sim"), abre "É um match!"
   Nada aqui salva no banco ainda: é só a parte visual. */
(function () {
  "use strict";

  var baralho = document.getElementById("baralho");
  if (!baralho) return;                       // não estamos na página de match

  var cartas = Array.prototype.slice.call(baralho.querySelectorAll(".carta"));
  var oferta = document.getElementById("oferta");
  var status = document.getElementById("status-match");
  var contador = document.getElementById("contador");
  var dialogo = document.getElementById("dialogo-match");
  var btnPassar = document.getElementById("btn-passar");
  var btnCurtir = document.getElementById("btn-curtir");

  var LIMITE = 90;      // quantos pixels arrastar para valer como decisão
  var topo = 0;         // posição da carta de cima na lista

  // 1) Dá a cada carta uma "posição" (pos-0 = de cima, pos-1, pos-2 = atrás).
  //    O CSS cuida do tamanho e do deslocamento de cada posição.
  function atualizar() {
    cartas.forEach(function (carta, i) {
      var pos = i - topo;
      carta.classList.remove("pos-0", "pos-1", "pos-2", "pos-3", "pos-fora");
      carta.classList.add(pos < 0 ? "pos-fora" : "pos-" + Math.min(pos, 3));
      carta.setAttribute("aria-hidden", pos === 0 ? "false" : "true");
    });
    var restantes = cartas.length - topo;
    contador.textContent = restantes + (restantes === 1 ? " item para ver" : " itens para ver");
    btnPassar.disabled = btnCurtir.disabled = restantes === 0;
  }

  function avisar(texto) { status.textContent = texto; }   // texto lido por leitores de tela

  function soltarSelos(carta) {
    carta.querySelector(".selo-troco").style.opacity = "";
    carta.querySelector(".selo-passo").style.opacity = "";
  }

  // Carta volta ao lugar (soltou antes do limite)
  function voltar(carta) {
    carta.classList.remove("arrastando");
    carta.style.transform = "";
    soltarSelos(carta);
  }

  // 2) Decisão: direcao = 1 (curtir ♥) ou -1 (passar ✕)
  function decidir(direcao) {
    var carta = cartas[topo];
    if (!carta) return;

    // Para curtir, precisa dizer qual item MEU está sendo oferecido
    if (direcao === 1 && !oferta.value) {
      voltar(carta);
      avisar("Escolha qual item seu você quer oferecer antes de curtir.");
      oferta.focus();
      return;
    }

    carta.classList.remove("arrastando");
    carta.style.transform = "translateX(" + direcao * window.innerWidth + "px) rotate(" + direcao * 25 + "deg)";
    carta.style.opacity = "0";
    topo++;
    atualizar();
    setTimeout(function () { carta.hidden = true; }, 300);   // some depois de sair da tela

    if (direcao === 1) {
      avisar("Você curtiu: " + carta.dataset.titulo);
      if (carta.dataset.retribuiu === "sim") abrirMatch(carta);
    } else {
      avisar("Você passou: " + carta.dataset.titulo);
    }
  }

  // 4) Janela de match
  function abrirMatch(carta) {
    document.getElementById("match-dono").textContent = carta.dataset.dono;
    document.getElementById("match-meu").textContent = oferta.options[oferta.selectedIndex].text;
    document.getElementById("match-deles").textContent = carta.dataset.titulo;
    if (dialogo.showModal) dialogo.showModal();
  }
  document.getElementById("match-fechar").addEventListener("click", function () { dialogo.close(); });

  // 2) Arrastar com mouse ou dedo (pointer events funcionam nos dois)
  var arrastando = false, inicioX = 0, dx = 0;

  baralho.addEventListener("pointerdown", function (e) {
    var carta = cartas[topo];
    if (!carta || !carta.contains(e.target)) return;
    arrastando = true;
    inicioX = e.clientX;
    dx = 0;
    carta.classList.add("arrastando");
    carta.setPointerCapture(e.pointerId);     // continua recebendo o movimento mesmo fora da carta
  });

  baralho.addEventListener("pointermove", function (e) {
    if (!arrastando) return;
    var carta = cartas[topo];
    dx = e.clientX - inicioX;
    carta.style.transform = "translateX(" + dx + "px) rotate(" + dx / 15 + "deg)";
    // os selos TROCO!/PASSO ficam mais fortes quanto mais perto do limite
    carta.querySelector(".selo-troco").style.opacity = Math.min(Math.max(dx / LIMITE, 0), 1);
    carta.querySelector(".selo-passo").style.opacity = Math.min(Math.max(-dx / LIMITE, 0), 1);
  });

  function soltou() {
    if (!arrastando) return;
    arrastando = false;
    if (dx > LIMITE) decidir(1);
    else if (dx < -LIMITE) decidir(-1);
    else voltar(cartas[topo]);
  }
  baralho.addEventListener("pointerup", soltou);
  baralho.addEventListener("pointercancel", soltou);

  // 3) Botões e teclado
  btnPassar.addEventListener("click", function () { decidir(-1); });
  btnCurtir.addEventListener("click", function () { decidir(1); });
  document.addEventListener("keydown", function (e) {
    var campo = e.target.tagName;
    if (campo === "SELECT" || campo === "INPUT" || campo === "TEXTAREA" || dialogo.open) return;
    if (e.key === "ArrowRight") decidir(1);
    if (e.key === "ArrowLeft") decidir(-1);
  });

  // "Ver de novo": devolve todas as cartas à pilha
  document.getElementById("reiniciar").addEventListener("click", function () {
    cartas.forEach(function (c) { c.hidden = false; c.style.transform = ""; c.style.opacity = ""; soltarSelos(c); });
    topo = 0;
    avisar("");
    atualizar();
  });

  atualizar();
})();
