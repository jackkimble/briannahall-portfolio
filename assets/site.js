(function () {
  "use strict";

  /* Menu on small screens */
  var toggle = document.getElementById("menu-toggle");
  var nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.textContent = open ? "Close" : "Menu";
    });
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a")) {
        nav.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.textContent = "Menu";
      }
    });
  }

  /* Quiet looping videos: play while on screen, never when the visitor prefers less motion */
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var loops = document.querySelectorAll("video[data-autoplay]");
  loops.forEach(function (v) {
    v.muted = true;
    if (reduce) { v.controls = true; return; }
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting) { var p = v.play(); if (p && p.catch) p.catch(function () { v.controls = true; }); }
          else { v.pause(); }
        });
      }, { threshold: 0.25 }).observe(v);
    } else {
      v.autoplay = true;
    }
  });

  /* Photo viewer */
  var box = document.getElementById("lightbox");
  if (!box) return;
  var imgEl = box.querySelector(".lightbox__img");
  var capEl = box.querySelector(".lightbox__caption");
  var countEl = box.querySelector(".lightbox__count");
  var items = [], index = 0, lastFocus = null;

  function show(i) {
    index = (i + items.length) % items.length;
    var a = items[index];
    var img = a.querySelector("img");
    imgEl.src = a.getAttribute("href");
    imgEl.alt = img ? img.alt : "";
    var cap = a.getAttribute("data-caption") || "";
    capEl.textContent = cap;
    capEl.hidden = !cap;
    countEl.textContent = items.length > 1 ? (index + 1) + " / " + items.length : "";
    box.querySelectorAll("[data-lb=prev],[data-lb=next]").forEach(function (b) { b.hidden = items.length < 2; });
  }
  function open(link) {
    var scope = link.closest("[data-gallery]") || link.closest(".story") || document;
    items = Array.prototype.slice.call(scope.querySelectorAll("a[data-lightbox]"));
    lastFocus = link;
    box.hidden = false;
    document.documentElement.classList.add("has-lightbox");
    show(items.indexOf(link));
    box.querySelector("[data-lb=close]").focus();
  }
  function close() {
    box.hidden = true;
    imgEl.removeAttribute("src");
    document.documentElement.classList.remove("has-lightbox");
    if (lastFocus) lastFocus.focus();
  }

  document.addEventListener("click", function (e) {
    var link = e.target.closest("a[data-lightbox]");
    if (link && !e.metaKey && !e.ctrlKey && !e.shiftKey) { e.preventDefault(); open(link); }
  });
  box.addEventListener("click", function (e) {
    var b = e.target.closest("[data-lb]");
    if (b) {
      var act = b.getAttribute("data-lb");
      if (act === "close") close(); else show(index + (act === "next" ? 1 : -1));
    } else if (e.target === box || e.target.classList.contains("lightbox__stage")) {
      close();
    }
  });
  document.addEventListener("keydown", function (e) {
    if (box.hidden) return;
    if (e.key === "Escape") close();
    else if (e.key === "ArrowRight") show(index + 1);
    else if (e.key === "ArrowLeft") show(index - 1);
    else if (e.key === "Tab") {
      var f = Array.prototype.slice.call(box.querySelectorAll("button:not([hidden])"));
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });
  var startX = null;
  box.addEventListener("touchstart", function (e) { startX = e.touches[0].clientX; }, { passive: true });
  box.addEventListener("touchend", function (e) {
    if (startX === null) return;
    var dx = e.changedTouches[0].clientX - startX;
    if (Math.abs(dx) > 50 && items.length > 1) show(index + (dx < 0 ? 1 : -1));
    startX = null;
  });
})();
