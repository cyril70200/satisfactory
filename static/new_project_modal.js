// new_project_modal.js
(function() {
  var form = document.getElementById('newProjectForm');
  if (form) {
    form.addEventListener('submit', function(e) {
      // Optionally, you can add validation or UI feedback here
      // The form will submit normally and redirect to /project/<uuid>
      // Modal will close automatically on redirect
    });
    // Optionally, clear the input when the modal is shown
    var input = document.getElementById('newProjectName');
    var modalEl = document.getElementById('newProjectModal');
    if (modalEl && input) {
      modalEl.addEventListener('show.bs.modal', function() {
        input.value = '';
      });
    }
  }
})();
