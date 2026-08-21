(function () {
  // The vendored sphinx_rtd_theme sticky-nav script can mis-measure sidebar
  // position on first paint (e.g. before web fonts finish loading), leaving
  // the left sidebar and search box positioned off-screen. Firing a resize
  // event after full load lets the theme's own (correct) logic recalculate.
  function resync() {
    window.dispatchEvent(new Event("resize"));
  }

  if (document.readyState === "complete") {
    resync();
  } else {
    window.addEventListener("load", resync);
  }

  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(resync);
  }
}());
