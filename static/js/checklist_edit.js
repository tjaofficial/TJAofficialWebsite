(() => {
  const rowsWrap = document.getElementById('rows');
  const addBtn = document.getElementById('addRow');
  if (!rowsWrap || !addBtn) return;

  function wireRow(row){
    const rm = row.querySelector('.rm');
    rm?.addEventListener('click', ()=> row.remove());
    row.addEventListener('dragstart', e => { row.classList.add('drag'); e.dataTransfer.effectAllowed = 'move'; });
    row.addEventListener('dragend',   () => { row.classList.remove('drag'); renumber(); });
    row.addEventListener('dragover', e => {
      e.preventDefault();
      const dragging = rowsWrap.querySelector('.drag');
      if (!dragging || dragging === row) return;
      const rect = row.getBoundingClientRect();
      const before = (e.clientY - rect.top) < rect.height/2;
      rowsWrap.insertBefore(dragging, before ? row : row.nextSibling);
    });
  }

  function renumber(){
    rowsWrap.querySelectorAll('.row').forEach((r, i)=>{
      const orderIn = r.querySelector('.order-in');
      if (orderIn) orderIn.value = String(i);
    });
  }

  // existing rows
  rowsWrap.querySelectorAll('.row').forEach(wireRow);

  addBtn.addEventListener('click', ()=>{
    const div = document.createElement('div');
    div.className = 'row';
    div.draggable = true;
    div.innerHTML = `
      <input type="hidden" name="id[]" value="">
      <input type="hidden" name="order[]" value="0" class="order-in">
      <label class="field grow">
        <span class="label">Title</span>
        <input type="text" name="title[]" value="">
      </label>
      <label class="chk"><input type="checkbox" name="required[]" value="1" checked><span>Required</span></label>
      <button class="btn ghost rm" type="button">Remove</button>
    `;
    rowsWrap.appendChild(div);
    wireRow(div);
    renumber();
  });

  // initial numbering safety
  renumber();
})();
