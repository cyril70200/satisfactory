// change_rate_modal.js
(function() {
  document.addEventListener('DOMContentLoaded', function() {
    document.body.addEventListener('click', function(e) {
      if (e.target.classList.contains('change-rate-btn')) {
        var modalEl = document.getElementById('changeRateModal');
        var form = modalEl.querySelector('form');
        var input = modalEl.querySelector('#changeRateInput');
        var itemUuid = e.target.getAttribute('data-uuid');
        var rate = e.target.getAttribute('data-rate');
        var projectId = document.querySelector('.text-muted.mb-2')?.textContent.trim();
        if (form && input && itemUuid && projectId) {
          form.action = '/project/' + encodeURIComponent(projectId) + '/item/' + encodeURIComponent(itemUuid) + '/change_rate';
          input.value = rate;
          var modal = new bootstrap.Modal(modalEl);
          modal.show();
        }
      }
    });
  });
})();
