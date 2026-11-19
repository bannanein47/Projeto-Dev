/* Troquei — interações do navegador (a validação de verdade fica no servidor). */
(function () {
  "use strict";

  // Mostrar/ocultar senha
  document.querySelectorAll("[data-toggle-senha]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var campo = document.getElementById(btn.dataset.toggleSenha);
      var mostrar = campo.type === "password";
      campo.type = mostrar ? "text" : "password";
      btn.textContent = mostrar ? "Ocultar" : "Mostrar";
      btn.setAttribute("aria-label", mostrar ? "Ocultar senha" : "Mostrar senha");
    });
  });

  // Medidor de força da senha
  var senha = document.querySelector("[data-forca]");
  var caixa = document.getElementById("forca");
  if (senha && caixa) {
    var barra = document.getElementById("forca-barra");
    var texto = document.getElementById("forca-texto");
    senha.addEventListener("input", function () {
      var v = senha.value, pontos = 0;
      if (v.length >= 8) pontos++;
      if (v.length >= 12) pontos++;
      if (/[a-z]/.test(v) && /[A-Z]/.test(v)) pontos++;
      if (/\d/.test(v)) pontos++;
      if (/[^A-Za-z0-9]/.test(v)) pontos++;
      var niveis = [["Muito fraca", "#c4203f"], ["Fraca", "#c4203f"], ["Razoável", "#e39a00"],
                    ["Boa", "#5aa83c"], ["Forte", "#12805c"], ["Excelente", "#12805c"]];
      caixa.hidden = v.length === 0;
      barra.style.width = Math.max(8, pontos / 5 * 100) + "%";
      barra.style.background = niveis[pontos][1];
      texto.textContent = niveis[pontos][0];

      // Lista de requisitos: marca ✓ (classe .ok) em cada regra cumprida
      var cumpre = { tamanho: v.length >= 8, letra: /[A-Za-z]/.test(v), numero: /\d/.test(v) };
      document.querySelectorAll("#requisitos [data-req]").forEach(function (li) {
        li.classList.toggle("ok", cumpre[li.dataset.req]);
      });
    });
  }

  // Confirmação de senha em tempo real
  var confirma = document.querySelector("[data-confirma]");
  if (confirma) {
    var original = document.getElementById(confirma.dataset.confirma);
    var aviso = document.createElement("p");
    aviso.className = "ajuda";
    aviso.setAttribute("aria-live", "polite");
    confirma.closest(".campo").appendChild(aviso);
    var conferir = function () {
      if (!confirma.value) { aviso.textContent = ""; return; }
      var igual = confirma.value === original.value;
      aviso.textContent = igual ? "✓ As senhas são iguais." : "As senhas ainda não são iguais.";
    };
    confirma.addEventListener("input", conferir);
    original.addEventListener("input", conferir);
  }

  // Novo código CAPTCHA
  document.querySelectorAll("[data-captcha-refresh]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var img = document.getElementById("captcha-img");
      var campo = document.getElementById("captcha");
      img.src = "/captcha.svg?v=" + Date.now();
      campo.value = "";
      campo.focus();
    });
  });

  // Prévia e limite da foto
  var arquivo = document.querySelector("input[type=file][data-previa]");
  if (arquivo) {
    arquivo.addEventListener("change", function () {
      var f = arquivo.files[0];
      var previa = document.getElementById(arquivo.dataset.previa);
      var inicial = document.getElementById("foto-inicial");
      if (!f) return;
      if (f.size > 2 * 1024 * 1024) {
        alert("A foto pode ter no máximo 2 MB.");
        arquivo.value = "";
        return;
      }
      previa.src = URL.createObjectURL(f);
      previa.hidden = false;
      if (inicial) inicial.hidden = true;
    });
  }

  // Pede confirmação antes de ações sem volta (ex.: remover item)
  document.querySelectorAll("form[data-confirma-envio]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.dataset.confirmaEnvio)) e.preventDefault();
    });
  });

  // Evita envio duplo
  document.querySelectorAll("form[data-protege]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var botao = form.querySelector("button[type=submit]");
      if (!botao) return;
      setTimeout(function () { botao.disabled = true; botao.textContent = "Aguarde…"; }, 0);
    });
  });

  // Voltar pelo navegador não deixa o botão travado
  window.addEventListener("pageshow", function (e) { if (e.persisted) location.reload(); });

  // Acessibilidade: depois de um erro do servidor, leva o foco ao 1º campo com problema
  var primeiroErro = document.querySelector("[aria-invalid=true]");
  if (primeiroErro) primeiroErro.focus();

  // Fechar avisos
  document.querySelectorAll(".aviso-fechar").forEach(function (b) {
    b.addEventListener("click", function () { b.closest(".aviso").remove(); });
  });
})();
