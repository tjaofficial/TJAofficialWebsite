(() => {
  const addForm = document.querySelector(".add-item-form");
  if (!addForm) return;

  const kind = addForm.querySelector(`select[name="kind"]`);
  const imagesWrap = addForm.querySelector(`[data-field="images"]`);
  const urlWrap = addForm.querySelector(`[data-field="url"]`);

  const drop = document.getElementById("dropZone");
  const fileInput = addForm.querySelector(`input[name="images"]`);
  const fileList = document.getElementById("fileList");

  const applyKind = () => {
    const v = kind?.value || "photo";
    if (v === "photo") {
      imagesWrap?.classList.remove("is-hidden");
      urlWrap?.classList.add("is-hidden");
    } else {
      urlWrap?.classList.remove("is-hidden");
      imagesWrap?.classList.add("is-hidden");
    }
  };

  const renderFiles = () => {
    if (!fileList || !fileInput) return;
    fileList.innerHTML = "";
    const files = Array.from(fileInput.files || []);
    files.slice(0, 12).forEach(f => {
      const chip = document.createElement("div");
      chip.className = "filechip";
      chip.textContent = f.name;
      const size = document.createElement("span");
      size.textContent = `${Math.max(1, Math.round(f.size/1024))}kb`;
      chip.appendChild(size);
      fileList.appendChild(chip);
    });
    if (files.length > 12) {
      const more = document.createElement("div");
      more.className = "filechip";
      more.textContent = `+${files.length - 12} more`;
      fileList.appendChild(more);
    }
  };

  // Kind toggle
  kind?.addEventListener("change", applyKind);
  applyKind();

  // File list
  fileInput?.addEventListener("change", renderFiles);
  renderFiles();

  // Drag styles
  if (drop && fileInput) {
    ["dragenter","dragover"].forEach(evt => {
      drop.addEventListener(evt, (e) => {
        e.preventDefault();
        drop.classList.add("dragover");
      });
    });
    ["dragleave","drop"].forEach(evt => {
      drop.addEventListener(evt, (e) => {
        e.preventDefault();
        drop.classList.remove("dragover");
      });
    });
  }
})();
