(function(){
  if (window.__selector_ws) return;
  var ws = new WebSocket('ws://localhost:8765');
  window.__selector_ws = ws;

  function cssPath(el){
    var path = [];
    while (el && el.nodeType === 1){
      var selector = el.nodeName.toLowerCase();
      if (el.id){
        selector += '#' + el.id;
        path.unshift(selector);
        break;
      } else {
        var sib = el, nth = 1;
        while (sib = sib.previousElementSibling){
          if (sib.nodeName.toLowerCase() === selector) nth++;
        }
        if (nth !== 1) selector += ':nth-of-type(' + nth + ')';
      }
      path.unshift(selector);
      el = el.parentNode;
    }
    return path.join(' > ');
  }

  function getXPath(el){
    if (el.id) return '//' + el.tagName.toLowerCase() + '[@id="' + el.id + '"]';
    if (el === document.body) return '/html/body';
    var ix = 0;
    var siblings = el.parentNode.childNodes;
    for (var i=0; i<siblings.length; i++){
      var sib = siblings[i];
      if (sib === el) {
        return getXPath(el.parentNode) + '/' + el.tagName.toLowerCase() + '[' + (ix+1) + ']';
      }
      if (sib.nodeType === 1 && sib.tagName === el.tagName) {
        ix++;
      }
    }
  }

  document.addEventListener('contextmenu', function(e){
    var msg = {
      css: cssPath(e.target),
      xpath: getXPath(e.target)
    };
    var data = JSON.stringify(msg);
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(data);
    } else {
      ws.addEventListener('open', function(){
        ws.send(data);
      }, {once: true});
    }
  }, true);
})();
