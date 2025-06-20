// open_project_modal.js
(function() {
  function filterProjects() {
    var searchBox = document.getElementById('projectSearchBox');
    var projectList = document.getElementById('projectList');
    if (!searchBox || !projectList) {
      console.log('[DEBUG] filterProjects: searchBox or projectList not found');
      return;
    }
    var filter = searchBox.value.trim().toLowerCase();
    console.log('[DEBUG] Filtering projects with:', filter);
    Array.from(projectList.children).forEach(function(li) {
      var name = (li.getAttribute('data-name') || '').trim().toLowerCase();
      var match = name.includes(filter);
      li.hidden = !match;
      console.log('[DEBUG] Project:', name, 'Visible:', match);
    });
  }
  document.addEventListener('DOMContentLoaded', function() {
    var searchBox = document.getElementById('projectSearchBox');
    if (searchBox) {
      searchBox.addEventListener('input', function() {
        console.log('[DEBUG] Input event on projectSearchBox');
        filterProjects();
      });
    } else {
      console.log('[DEBUG] projectSearchBox not found on DOMContentLoaded');
    }
    var projectList = document.getElementById('projectList');
    if (projectList) {
      projectList.addEventListener('click', function(e) {
        if (e.target.classList.contains('open-project-btn')) {
          var projectId = e.target.getAttribute('data-id');
          if (projectId) {
            console.log('[DEBUG] Open project button clicked for:', projectId);
            window.location.href = '/project/' + encodeURIComponent(projectId);
          }
        }
      });
    } else {
      console.log('[DEBUG] projectList not found on DOMContentLoaded');
    }
  });
})();
