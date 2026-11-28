// 图片预览：选择文件后，把缩略图渲染到 data-preview 指定的容器里
document.querySelectorAll('.image-input').forEach(function (input) {
  input.addEventListener('change', function () {
    var preview = document.querySelector(input.dataset.preview);
    if (!preview) return;
    preview.innerHTML = '';
    var files = input.files;
    for (var i = 0; i < files.length; i++) {
      (function (file) {
        var reader = new FileReader();
        reader.onload = function (ev) {
          var img = document.createElement('img');
          img.src = ev.target.result;
          preview.appendChild(img);
        };
        reader.readAsDataURL(file);
      })(files[i]);
    }
  });
});
