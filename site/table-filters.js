var prior_dev = null;

function setVisible(dev, visible) {
  if (!dev) return;
  var devs = document.getElementsByClassName(dev);
  for (var i = 0; i < devs.length; i++) {
    console.log(devs[i]);
    devs[i].style.display = visible ? 'block' : 'none';
  }
}

function show(dev) { setVisible(dev, true); }

function hide(dev) { setVisible(dev, false); }

function refresh() {
  var selector = document.getElementById('developer');
  var dev = selector.value;
  if (dev == prior_dev) return;
  hide(`dev-${prior_dev}`);
  show(`dev-${dev}`);
  prior_dev = dev;
}
