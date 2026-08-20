(function () {
  const documentPath = window.location.pathname.match(/\/mkdocs\/markdown\/[^/]+\/$/);
  const documentBody = document.querySelector('[role="main"].document, [role="main"] .document');

  if (!documentPath || !documentBody || window.history.length <= 1) {
    return;
  }

  const backButton = document.createElement("button");
  backButton.type = "button";
  backButton.className = "document-back-button";
  backButton.textContent = "Back";
  backButton.setAttribute("aria-label", "Go back to the previous page");
  backButton.addEventListener("click", function () {
    window.history.back();
  });
  documentBody.prepend(backButton);
}());