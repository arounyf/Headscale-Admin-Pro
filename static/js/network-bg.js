(function(){
  var style = document.createElement('style');
  style.textContent = [
    'body{background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 30%,#0f172a 60%,#1e1b4b 100%);background-size:400% 400%;animation:bgShift 20s ease infinite}',
    '@keyframes bgShift{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}',
    '.bg-orb{position:fixed;border-radius:50%;filter:blur(80px);z-index:-1;pointer-events:none;animation:orbFloat linear infinite}',
    '@keyframes orbFloat{0%{transform:translate(0,0) scale(1)}33%{transform:translate(30px,-30px) scale(1.1)}66%{transform:translate(-20px,20px) scale(0.9)}100%{transform:translate(0,0) scale(1)}}'
  ].join('\n');
  document.head.appendChild(style);

  // 生成 3 个光斑
  var colors = ['rgba(99,102,241,0.15)','rgba(139,92,246,0.12)','rgba(6,182,212,0.1)'];
  var sizes = ['400px','350px','300px'];
  var durations = ['18s','22s','20s'];
  var positions = [
    {top:'10%',left:'-5%'},
    {top:'50%',right:'-10%'},
    {bottom:'-10%',left:'30%'}
  ];
  for (var i = 0; i < 3; i++) {
    var orb = document.createElement('div');
    orb.className = 'bg-orb';
    orb.style.cssText = 'width:'+sizes[i]+';height:'+sizes[i]
      +';top:'+positions[i].top+';left:'+positions[i].left
      +';right:'+(positions[i].right||'auto')+';bottom:'+(positions[i].bottom||'auto')
      +';background:'+colors[i]+';animation-duration:'+durations[i];
    document.body.appendChild(orb);
  }
})();
