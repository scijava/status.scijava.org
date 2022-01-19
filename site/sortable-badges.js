// This is free and unencumbered software released into the public domain.
// See the UNLICENSE file for details.

function imageData(img) {
  var canvas = document.createElement("canvas");
  canvas.width = img.width;
  canvas.height = img.height;

  // HACK: Without this, canvas.toDataURL() triggers the error
  // 'Tainted canvases may not be exported'.
  // See: http://stackoverflow.com/a/27260385/1207769
  var anonImg = new Image();
  anonImg.setAttribute('crossOrigin', 'anonymous');
  anonImg.src = img.src;

  canvas.getContext("2d").drawImage(anonImg, 0, 0);
  return canvas.toDataURL();
}

function hashCode(s) {
  // NB: Using the first 128 characters is good enough, and much faster.
  return s.substring(0, 128);
/*
  var hash = 0;
  if (s.length === 0) return hash;
  for (var i = 0; i < s.length; i++) {
    var c = s.charCodeAt(i);
    hash = ((hash << 5) - hash) + c;
    hash |= 0; // Convert to 32-bit integer
  }
  return hash.toString(16);
*/
}

// Thanks to Andreas: http://stackoverflow.com/users/402037/andreas
// See: http://stackoverflow.com/q/43686686/1207769
function makeBadgesSortable() {
  var tds = document.body.getElementsByClassName("badge");
  for (var i=0; i<tds.length; i++) {
    var imgs = tds[i].getElementsByTagName("img");
    if (imgs.length < 1) continue;
    tds[i].setAttribute("sorttable_customkey", hashCode(imageData(imgs[0])));
  }
}
