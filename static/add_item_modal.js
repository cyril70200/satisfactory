// add_item_modal.js
(function() {
  function filterAddItemOptions() {
    var searchBox = document.getElementById('itemSearchBox');
    var select = document.getElementById('itemSelect');
    if (!searchBox || !select) return;
    var filter = searchBox.value.trim().toLowerCase();
    var anyVisible = false;
    Array.from(select.options).forEach(function(option) {
      var text = option.text.toLowerCase();
      var match = text.includes(filter);
      option.style.display = match ? '' : 'none';
      if (match && !anyVisible) {
        select.selectedIndex = option.index;
        anyVisible = true;
      }
    });
    if (!anyVisible) {
      select.selectedIndex = -1;
    }
  }
  document.addEventListener('DOMContentLoaded', function() {
    var searchBox = document.getElementById('itemSearchBox');
    if (searchBox) {
      searchBox.addEventListener('input', filterAddItemOptions);
    }
  });
  window.filterAddItemOptions = filterAddItemOptions;
})();
