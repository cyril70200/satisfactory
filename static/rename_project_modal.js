// rename_project_modal.js
(function() {
  var input = document.getElementById('projectNameInput');
  var submitBtn = document.getElementById('renameProjectSubmit');
  function updateButtonState(event) {
    console.log('[RenameProjectModal] Input changed:', event.target.value);
    submitBtn.disabled = !(input.value && input.value.trim().length > 0);
  }
  if (input && submitBtn) {
    input.value = "";
    submitBtn.disabled = true;
    console.log('[RenameProjectModal] Script loaded');
    input.addEventListener('input', updateButtonState);
    input.addEventListener('change', updateButtonState);
    console.log('[RenameProjectModal] Input and button initialized');
  }
})();