(function () {
  var remembered = new WeakMap();

  function updateFields() {
    var view = document.getElementById('sc-type');
    var round = document.getElementById('sc-round-field');
    var player = document.getElementById('sc-player-field');
    if (!view || !round || !player) return;
    round.style.display = view.value === 'one_player_all_rounds' ? 'none' : '';
    player.style.display = view.value === 'one_round_all_players' ? 'none' : '';
  }

  document.addEventListener('change', function (event) {
    if (event.target && event.target.id === 'sc-type') updateFields();
  });
  document.addEventListener('public-state:commit', updateFields);
  document.addEventListener('public-state:rollback', updateFields);
  document.addEventListener('DOMContentLoaded', updateFields);

  document.addEventListener('htmx:beforeRequest', function (event) {
    var target = event.detail && event.detail.target;
    if (!target) return;
    var options = target.querySelector('.sc-options');
    var points = target.querySelector('.scm-pts');
    if (!options && !points) return;
    var state = remembered.get(target) || { open: false, points: false };
    if (options) state.open = options.open;
    if (points) state.points = points.checked;
    remembered.set(target, state);
  });

  document.addEventListener('htmx:afterSwap', function (event) {
    var target = event.detail && event.detail.target;
    if (!target) return;
    var previous = remembered.get(target);
    if (previous) {
      var options = target.querySelector('.sc-options');
      if (options) options.open = previous.open;
      var points = target.querySelector('.scm-pts');
      if (points) points.checked = previous.points;
    }
    updateFields();
  });
})();
