// navbar.js
// Handles navbar button actions (New, Open, Save Project)
document.addEventListener('DOMContentLoaded', function() {
  var newProjectBtn = document.getElementById('newProjectBtn');
  if (newProjectBtn) {
    newProjectBtn.addEventListener('click', function(e) {
      e.preventDefault();
      console.log('[DEBUG] New Project button clicked');
      var modalEl = document.getElementById('newProjectModal');
      if (modalEl) {
        console.log('[DEBUG] newProjectModal element found');
        setTimeout(function() {
          var modal = new bootstrap.Modal(modalEl);
          modal.show();
          console.log('[DEBUG] modal.show() called after delay');
        }, 100);
      } else {
        console.log('[DEBUG] newProjectModal element NOT found');
      }
    });
  }
  var openProjectBtn = document.getElementById('openProjectBtn');
  if (openProjectBtn) {
    openProjectBtn.addEventListener('click', function(e) {
      e.preventDefault();
      var modal = new bootstrap.Modal(document.getElementById('openProjectModal'));
      modal.show();
    });
  }
  var saveProjectBtn = document.getElementById('saveProjectBtn');
  if (saveProjectBtn) {
    saveProjectBtn.addEventListener('click', function(e) {
      e.preventDefault();
      // Save project logic: get current project_id from DOM
      var projectIdEl = document.getElementById('projectNameDisplay');
      var projectId = null;
      if (projectIdEl) {
        // Try to get project_id from a data attribute or from a hidden element
        var uuidEl = document.querySelector('.text-muted.mb-2');
        if (uuidEl) {
          projectId = uuidEl.textContent.trim();
        }
      }
      if (projectId) {
        window.location.href = '/save_project?project_id=' + encodeURIComponent(projectId);
      } else {
        alert('No project selected to save.');
      }
    });
  }
  var addItemBtn = document.getElementById('addItemSidebarBtn');
  if (addItemBtn) {
    addItemBtn.addEventListener('click', function(e) {
      e.preventDefault();
      var modalEl = document.getElementById('addItemModal');
      if (modalEl) {
        var modal = new bootstrap.Modal(modalEl);
        modal.show();
      }
    });
  }
});
