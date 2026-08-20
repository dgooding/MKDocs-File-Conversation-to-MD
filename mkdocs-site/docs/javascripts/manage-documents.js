(function () {
  const isMarkdownPage = window.location.pathname.endsWith("/markdown/") || window.location.pathname.endsWith("/markdown");
  const isBackupPage = window.location.pathname.endsWith("/backups/") || window.location.pathname.endsWith("/backups");
  if (!isMarkdownPage && !isBackupPage) {
    return;
  }

  const list = document.querySelector('[role="main"].document ul, [role="main"] .document ul');
  if (!list) {
    return;
  }

  const links = Array.from(list.querySelectorAll("a")).filter((link) => {
    const href = link.getAttribute("href") || "";
    return href && !href.startsWith("#") && href !== "./" && !link.classList.contains("paired-original");
  });
  if (!links.length) {
    return;
  }

  const toolbar = document.createElement("div");
  toolbar.className = "document-manager";
  toolbar.innerHTML = '<strong>Documents</strong><button type="button" class="select-all">Select all</button><button type="button" class="delete-selected" disabled>Delete selected</button><span>0 selected</span>';
  const selectAllButton = toolbar.querySelector(".select-all");
  const deleteSelectedButton = toolbar.querySelector(".delete-selected");
  const message = toolbar.querySelector("span");
  const checks = [];

  const updateSelection = () => {
    const selectedCount = checks.filter((candidate) => candidate.checked).length;
    message.textContent = `${selectedCount} selected`;
    deleteSelectedButton.disabled = selectedCount === 0;
    selectAllButton.textContent = selectedCount === checks.length ? "Clear all" : "Select all";
  };

  links.forEach((link) => {
    const item = link.closest("li");
    if (!item) return;
    const check = document.createElement("input");
    check.type = "checkbox";
    check.className = "document-select";
    const slug = decodeURIComponent(link.getAttribute("href").split("/").filter(Boolean).pop());
    check.value = isBackupPage ? slug : (slug.endsWith(".md") ? slug : `${slug}.md`);
    check.setAttribute("aria-label", `Select ${link.textContent}`);
    item.className = "document-list-item";
    item.replaceChildren(check);
    const details = document.createElement("div");
    details.className = "document-details";
    const title = link.textContent;
    const actions = document.createElement("div");
    actions.className = "document-actions";
    link.className = "document-title";
    const viewLink = link.cloneNode(true);
    viewLink.textContent = "View Markdown";
    viewLink.className = "converted-link";
    actions.append(viewLink);
    details.append(link);
    link.textContent = title;
    details.append(actions);
    item.append(details);
    item.prepend(check);
    checks.push(check);
    check.addEventListener("change", () => {
      updateSelection();
    });
  });

  selectAllButton.addEventListener("click", () => {
    const shouldSelect = checks.some((check) => !check.checked);
    checks.forEach((check) => { check.checked = shouldSelect; });
    updateSelection();
  });

  deleteSelectedButton.addEventListener("click", async () => {
    const filenames = checks.filter((check) => check.checked).map((check) => check.value);
    if (!filenames.length || !window.confirm(`Delete ${filenames.length} selected document${filenames.length === 1 ? "" : "s"}?`)) {
      return;
    }
    deleteSelectedButton.disabled = true;
    selectAllButton.disabled = true;
    message.textContent = "Deleting...";
    try {
      const response = await fetch("/api/published/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filenames }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Delete failed.");
      window.location.reload();
    } catch (error) {
      message.textContent = error instanceof Error ? error.message : "Delete failed.";
      selectAllButton.disabled = false;
      updateSelection();
    }
  });

  list.before(toolbar);
  list.className = "document-list";

  if (isMarkdownPage) {
    fetch("../backups/")
      .then((response) => response.text())
      .then((html) => {
        const backupDocument = new DOMParser().parseFromString(html, "text/html");
        const backups = new Map(Array.from(backupDocument.querySelectorAll('a[href$=".pdf"], a[href$=".docx"]')).map((link) => {
          const href = link.getAttribute("href");
          return [href.split("/").pop().replace(/\.(pdf|docx)$/i, ""), href];
        }));
        links.forEach((link) => {
          const item = link.closest("li");
          const slug = decodeURIComponent(link.getAttribute("href").split("/").filter(Boolean).pop()).replace(/\.md$/i, "");
          const backupHref = backups.get(slug);
              if (!item || !backupHref) return;
              const details = item.querySelector(".document-details");
              const actions = item.querySelector(".document-actions");
              const meta = document.createElement("span");
              meta.className = "document-meta";
              meta.textContent = "Searchable Markdown";
          const backupLink = document.createElement("a");
          backupLink.className = "paired-original";
          backupLink.href = `../backups/${backupHref.split("/").pop()}`;
          backupLink.textContent = "Original file";
              actions.append(backupLink);
              details.insertBefore(meta, actions);
        });
      })
      .catch(() => {});
  }
}());