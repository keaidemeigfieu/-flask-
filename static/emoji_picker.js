// 表情包面板：点按钮弹出/收起，点 emoji 插入到对应输入框，点别处关闭
document.addEventListener('click', function (e) {
  var btn = e.target.closest('.emoji-btn');
  if (btn) {
    var target = btn.getAttribute('data-target');
    var panel = document.getElementById('emoji-panel-' + target);
    if (panel) {
      var isHidden = panel.style.display === 'none' || panel.style.display === '';
      panel.style.display = isHidden ? 'grid' : 'none';
    }
    e.stopPropagation();
    return;
  }

  var em = e.target.closest('.emoji');
  if (em) {
    var panel = em.closest('.emoji-panel');
    var targetId = panel.id.replace('emoji-panel-', '');
    var ta = document.getElementById(targetId);
    if (ta) {
      ta.value += (em.textContent || '').trim();
      ta.focus();
    }
    return;
  }

  // 点击别处关闭所有面板
  document.querySelectorAll('.emoji-panel').forEach(function (p) { p.style.display = 'none'; });
});
