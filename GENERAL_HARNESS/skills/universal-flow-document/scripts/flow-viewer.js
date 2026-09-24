/* DOM-only rendering: input text never becomes markup or script. */
(() => {
  const data=JSON.parse(document.getElementById('flow-data').textContent);
  const $=id=>document.getElementById(id);
  const el=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x;};
  const svg=(tag,attrs={})=>{const x=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v]of Object.entries(attrs))x.setAttribute(k,String(v));return x;};
  let flow=data.flows[0],scenario=null,selected=null,zoom=1,outcome='all',hashNotice='';
  const lastScenarioByFlow=new Map();
  const typeNames={start:'시작',process:'처리',decision:'판단',input_output:'입출력',database:'데이터',external:'외부',event:'이벤트',async:'비동기',callback:'콜백',stream:'스트림',success:'완료',failure:'실패',hold:'보류',note:'참고'};
  const statusNames={implemented:'구현 근거 있음',designed:'설계·운영 규칙',conditional:'조건부',unknown:'확인 필요'};
  const outcomeNames={all:'전체',success:'완료',failure:'실패',hold:'보류',ongoing:'진행 중'};
  $('brand').textContent=data.meta.title;$('stamp').textContent=data.meta.generatedAt||'';
  const sourceText=s=>[s.file||s.document,s.symbol||s.method,s.line?`L${s.line}`:'',s.revision].filter(Boolean).join(' · ')||JSON.stringify(s);
  function sourceList(items){const list=el('ul');for(const s of items||[]){const li=el('li');let url=null;try{const u=new URL(s.url);if(['http:','https:'].includes(u.protocol)&&!u.username&&!u.password)url=u.href;}catch{}if(url){const a=el('a',sourceText(s));a.href=url;a.target='_blank';a.rel='noopener noreferrer';li.append(a);}else li.textContent=sourceText(s);list.append(li);}return list;}
  function field(parent,title,value){if(value===undefined||value===null||value==='')return;parent.append(el('h4',title));if(Array.isArray(value)){const list=el('ul');value.forEach(v=>list.append(el('li',v)));parent.append(list);}else parent.append(el('p',value));}
  function writeHash(mode='replace'){const p=new URLSearchParams({flow:flow.id});if(scenario)p.set('scenario',scenario.id);const url='#'+p;(mode==='push'?history.pushState:history.replaceState).call(history,null,'',url);}
  function readHash(){const p=new URLSearchParams(location.hash.slice(1)),f=data.flows.find(f=>f.id===p.get('flow'));if(!f)return false;flow=f;const requested=p.get('scenario'),found=f.scenarios?.find(s=>s.id===requested)||null;scenario=found;outcome=found?.kind||'all';hashNotice=requested&&!found?'요청한 세부 경로가 없어 전체 흐름을 표시합니다.':'';if(found)lastScenarioByFlow.set(`${f.id}:${found.kind}`,found.id);selected=null;return true;}
  function closeMenu(focusMenu=false){document.body.classList.remove('menu-open');$('menu').setAttribute('aria-expanded','false');if(focusMenu)$('menu').focus();}
  function changeFlow(f){flow=f;scenario=null;outcome='all';hashNotice='';selected=null;zoom=1;renderList();renderFlow();writeHash('push');closeMenu();$('title').focus();}
  function applyZoom(){const board=$('chart').querySelector('svg');if(!board)return;const [,,w,h]=board.getAttribute('viewBox').split(' ').map(Number);board.setAttribute('width',w*zoom);board.setAttribute('height',h*zoom);$('zoom-label').textContent=Math.round(zoom*100)+'%';}
  function renderList(){
    $('flows').replaceChildren();const terms=$('search').value.trim().toLowerCase().split(/\s+/).filter(Boolean),category=$('category').value;
    const matches=data.flows.filter(f=>{const haystack=[f.title,f.category,f.group,f.summary,f.api?.method,f.api?.path].join(' ').toLowerCase();return(!category||f.category===category)&&terms.every(term=>haystack.includes(term));});
    for(const group of new Set(matches.map(f=>f.group||f.category||'흐름'))){$('flows').append(el('h3',group,'nav-group'));for(const f of matches.filter(f=>(f.group||f.category||'흐름')===group)){const b=el('button');b.type='button';b.append(el('span',f.title));if(f.api)b.append(el('small',f.api.method+' '+f.api.path));b.setAttribute('aria-current',String(f===flow));b.onclick=()=>changeFlow(f);$('flows').append(b);}}
    const filtered=terms.length>0||Boolean(category),outside=!matches.includes(flow);$('search-status').textContent=matches.length?`${matches.length} / 전체 ${data.flows.length}개${outside?' · 현재 흐름은 검색 결과 밖에 있음':''}`:`검색 결과 없음 · 전체 ${data.flows.length}개`;$('filter-reset').hidden=!filtered;$('search-clear').disabled=!$('search').value;
  }
  function scenariosFor(kind){return (flow.scenarios||[]).filter(s=>s.kind===kind);}
  function chooseOutcome(kind){const choices=scenariosFor(kind);if(kind!=='all'&&!choices.length)return;outcome=kind;scenario=null;hashNotice='';if(kind!=='all'){const remembered=lastScenarioByFlow.get(`${flow.id}:${kind}`);scenario=choices.find(s=>s.id===remembered)||choices[0];lastScenarioByFlow.set(`${flow.id}:${kind}`,scenario.id);}selected=null;renderFlow();writeHash('push');}
  function renderScenarioControls(){
    const buttons=$('result-buttons');buttons.replaceChildren();const kinds=['all','success','failure'];for(const extra of ['hold','ongoing'])if(scenariosFor(extra).length)kinds.push(extra);
    for(const kind of kinds){const count=kind==='all'?(flow.scenarios||[]).length:scenariosFor(kind).length,b=el('button',`${outcomeNames[kind]} ${count}`,'result-button');b.type='button';b.dataset.kind=kind;b.setAttribute('aria-pressed',String(outcome===kind));if(kind!=='all'&&!count){b.disabled=true;b.title=`등록된 ${outcomeNames[kind]} 경로 없음`;}b.onclick=()=>chooseOutcome(kind);buttons.append(b);}
    const choices=outcome==='all'?[]:scenariosFor(outcome),picker=$('scenario-picker'),choice=$('scenario');choice.replaceChildren();picker.hidden=choices.length<2;if(choices.length>1){$('scenario-label').textContent=outcome==='failure'?'실패 원인':`${outcomeNames[outcome]} 경로`;for(const s of choices){const op=el('option',s.label);op.value=s.id;choice.append(op);}choice.value=scenario?.id||choices[0].id;}
    const base=scenario?.summary||scenario?.label||(outcome==='all'?'전체 분기와 설명을 표시합니다.':`등록된 ${outcomeNames[outcome]} 경로 없음`);$('scenario-summary').textContent=hashNotice||base;
  }
  function selectNode(id,fromChart){
    selected=id;document.querySelectorAll('[data-node-id]').forEach(x=>{const yes=x.dataset.nodeId===id;x.classList.toggle('selected',yes);if(x.getAttribute('role')==='button'||x.tagName==='BUTTON')x.setAttribute('aria-pressed',String(yes));});
    const target=[...(fromChart?$('details'):$('chart')).querySelectorAll('[data-node-id]')].find(x=>x.dataset.nodeId===id);
    target?.scrollIntoView({block:'center',inline:'center',behavior:'auto'});
    if(fromChart&&target){target.tabIndex=-1;target.focus({preventScroll:true});}
  }
  function renderGraph(){
    const min=Math.min(...flow.nodes.map(n=>n.column)),max=Math.max(...flow.nodes.map(n=>n.column));
    const width=Math.max(620,(max-min)*340+470),height=(Math.max(...flow.nodes.map(n=>n.row))+1)*190+110;
    const board=svg('svg',{viewBox:`0 0 ${width} ${height}`,width,height,'aria-label':`${flow.title} 플로우차트`});
    const defs=svg('defs');for(const [id,color]of [['arrow','#516e73'],['arrow-failure','#a52831']]){const m=svg('marker',{id,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});m.append(svg('path',{d:'M0 0 L10 5 L0 10 Z',fill:color}));defs.append(m);}board.append(defs);
    const boxes=new Map(flow.nodes.map(n=>[n.id,{x:75+(n.column-min)*340,y:55+n.row*190,w:250,h:n.type==='decision'?120:86}]));
    const activeNodes=scenario?new Set(scenario.path):null,activeEdges=new Set();
    if(scenario)for(let i=1;i<scenario.path.length;i++){const e=flow.edges.find(e=>scenario.edgePath?e.id===scenario.edgePath[i-1]:e.from===scenario.path[i-1]&&e.to===scenario.path[i]);if(e)activeEdges.add(e.id);}
    for(const e of flow.edges){const a=boxes.get(e.from),b=boxes.get(e.to);let d,lx,ly;
      if(b.y>a.y){const sx=a.x+a.w/2,sy=a.y+a.h,tx=b.x+b.w/2,ty=b.y;const mid=(sy+ty)/2;d=`M${sx} ${sy} C${sx} ${mid} ${tx} ${mid} ${tx} ${ty}`;lx=(sx+tx)/2;ly=mid-7;}
      else {const side=Math.max(a.x+a.w,b.x+b.w)+45;d=`M${a.x+a.w} ${a.y+a.h/2} H${side} V${b.y+b.h/2} H${b.x+b.w}`;lx=side+5;ly=(a.y+b.y)/2+30;}
      const dim=scenario&&!activeEdges.has(e.id);const line=svg('path',{d,class:`edge ${e.kind}${dim?' dim':''}`,'data-edge-id':e.id,'marker-end':`url(#${e.kind==='failure'?'arrow-failure':'arrow'})`});board.append(line);
      const label=e.label||(['async','callback','compensation'].includes(e.kind)?e.kind:'');if(label){const t=svg('text',{x:lx,y:ly,class:`edge-label${dim?' dim':''}`});t.textContent=label;board.append(t);}
    }
    for(const n of flow.nodes){const b=boxes.get(n.id),cx=b.x+b.w/2,cy=b.y+b.h/2;const g=svg('g',{class:`node${activeNodes&&!activeNodes.has(n.id)&&n.type!=='note'?' dim':''}${selected===n.id?' selected':''}`,'data-node-id':n.id,'data-type':n.type,tabindex:0,role:'button','aria-label':n.title,'aria-pressed':String(selected===n.id)});
      if(n.type==='decision')g.append(svg('polygon',{class:'shape',points:`${cx},${b.y} ${b.x+b.w},${cy} ${cx},${b.y+b.h} ${b.x},${cy}`}));
      else if(n.type==='input_output')g.append(svg('polygon',{class:'shape',points:`${b.x+18},${b.y} ${b.x+b.w},${b.y} ${b.x+b.w-18},${b.y+b.h} ${b.x},${b.y+b.h}`}));
      else if(n.type==='database')g.append(svg('path',{class:'shape',d:`M${b.x} ${b.y+12} C${b.x} ${b.y-3} ${b.x+b.w} ${b.y-3} ${b.x+b.w} ${b.y+12} V${b.y+b.h-12} C${b.x+b.w} ${b.y+b.h+3} ${b.x} ${b.y+b.h+3} ${b.x} ${b.y+b.h-12} Z M${b.x} ${b.y+12} C${b.x} ${b.y+28} ${b.x+b.w} ${b.y+28} ${b.x+b.w} ${b.y+12}`}));
      else {g.append(svg('rect',{class:'shape',x:b.x,y:b.y,width:b.w,height:b.h,rx:['start','success','failure','hold'].includes(n.type)?30:8}));if(n.type==='external')g.append(svg('rect',{class:'shape',x:b.x+6,y:b.y+6,width:b.w-12,height:b.h-12,rx:4}));}
      const actor=svg('text',{x:b.x,y:b.y-12,class:'actor'});actor.textContent=String(flow.nodes.indexOf(n)+1).padStart(2,'0')+' · '+(n.owner||'주체 미기재');g.append(actor);
      const text=svg('text',{x:cx,y:n.type==='database'?cy+1:cy-7});const chars=Array.from(n.title),limit=n.type==='decision'?12:20,lines=[];for(let i=0;i<chars.length;i+=limit)lines.push(chars.slice(i,i+limit).join(''));
      const shown=lines.slice(0,2);if(lines.length>2)shown[1]=shown[1].slice(0,-1)+'…';shown.forEach((line,i)=>{const t=svg('tspan',{x:cx,dy:i?17:0});t.textContent=line;text.append(t);});g.append(text);
      const badge=svg('text',{x:cx,y:b.y+b.h-8,class:'badge'});badge.textContent=typeNames[n.type];g.append(badge);const full=svg('title');full.textContent=n.title+' — '+(n.description||'설명 미기재');g.append(full);
      g.onclick=()=>selectNode(n.id,true);g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectNode(n.id,true);}};board.append(g);
    }const chart=$('chart');chart.replaceChildren(board);applyZoom();chart.scrollTop=0;
    const entry=flow.nodes.find(n=>n.type==='start'||n.entry===true),entryBox=boxes.get(entry.id);
    chart.scrollLeft=Math.max(0,(entryBox.x+entryBox.w/2)*zoom-chart.clientWidth/2);
  }
  function renderDetails(){
    $('details').replaceChildren();for(const n of flow.nodes){const card=el('article',undefined,'step');card.dataset.nodeId=n.id;const h=el('h3'),button=el('button',String(flow.nodes.indexOf(n)+1).padStart(2,'0')+'. '+n.title);button.type='button';button.dataset.nodeId=n.id;button.setAttribute('aria-pressed',String(selected===n.id));button.onclick=()=>selectNode(n.id,false);h.append(button);card.append(h,el('p',(n.owner||'주체 미기재')+' · '+typeNames[n.type],'owner'));
      if(n.status)card.append(el('p',statusNames[n.status.kind]+' · '+n.status.detail,'status'));
      field(card,'판단 조건',n.condition);if(n.stateChange)field(card,'상태 변화',n.stateChange.before+' → '+n.stateChange.after);
      if(n.description)card.append(el('p',n.description));if(n.why){card.append(el('h4','왜 필요한가'),el('p',n.why));}
      for(const [title,values]of [['입력',n.inputs],['출력',n.outputs],['실패',n.failures]])if(values?.length){card.append(el('h4',title));const ul=el('ul');for(const v of values)ul.append(el('li',v));card.append(ul);}
      for(const c of flow.failureCases||[])if(c.nodeId===n.id){const block=el('div',undefined,'failure-case');field(block,'실패 조건',c.condition);field(block,'반환 상태·코드',[c.status,c.code].filter(Boolean).join(' · '));field(block,'영향',c.effect);field(block,'다음 행동',c.nextAction);field(block,'재시도',c.retry);if(c.source)block.append(sourceList(c.source));card.append(block);}
      if(n.flowRef){const target=data.flows.find(f=>f.id===n.flowRef),b=el('button','상세 흐름 → '+target.title,'drilldown');b.onclick=()=>changeFlow(target);card.append(b);}
      if(n.source?.length){const refs=el('details');refs.append(el('summary','단계 근거'),sourceList(n.source));card.append(refs);}
      if(scenario&&!scenario.path.includes(n.id)&&n.type!=='note')card.classList.add('dim');if(selected===n.id)card.classList.add('selected');$('details').append(card);
    }
  }
  function renderFlow(){
    $('title').textContent=flow.title;$('summary').textContent=flow.summary;$('provenance').textContent=[data.meta.subtitle,data.meta.provenance].filter(Boolean).join(' · ');$('implementation').textContent=flow.status?statusNames[flow.status.kind]+' · '+flow.status.detail:'';
    $('facts').replaceChildren();for(const [name,value]of [['분류',flow.category],['시작',flow.entryKind],['접근 조건',flow.access],['입력',flow.input],['출력',flow.output],['API',flow.api?flow.api.method+' '+flow.api.path:null]])if(value){const div=el('div');div.append(el('dt',name),el('dd',value));$('facts').append(div);}
    $('coverage').replaceChildren();if(flow.coverage){const d=el('details');d.append(el('summary','범위·분석 근거'));field(d,'포함 범위',flow.coverage.scope);field(d,'대조 기준',flow.coverage.basis);field(d,'제외·한계',flow.coverage.excluded);$('coverage').append(d);}
    $('completion').replaceChildren();if(flow.completion){const d=el('details');d.append(el('summary','접수와 후속 완료의 구분'));field(d,'접수 완료',flow.completion.acceptance);field(d,'후속 처리',flow.completion.processing);field(d,'결과 전달',flow.completion.resultDelivery);$('completion').append(d);}
    renderScenarioControls();
    $('failure-detail').replaceChildren();for(const c of flow.failureCases||[])if(c.scenarioId===scenario?.id){field($('failure-detail'),'실패 조건',c.condition);field($('failure-detail'),'영향·응답',[c.status,c.code,c.effect].filter(Boolean).join(' · '));field($('failure-detail'),'다음 행동',c.nextAction);field($('failure-detail'),'재시도',c.retry);}
    const api=$('api-details');api.replaceChildren();$('api-contract').hidden=!flow.api;if(flow.api){field(api,'요청',flow.api.request);field(api,'응답',flow.api.response);if(flow.api.signature)api.append(el('h3','요청 시그니처'),el('pre',flow.api.signature));for(const s of flow.api.schemas||[]){api.append(el('h3',s.name),el('pre',s.body));if(s.source)api.append(sourceList(s.source));}}
    renderGraph();renderDetails();$('sources').replaceChildren(...sourceList(flow.sources).children);
  }
  $('scenario').onchange=e=>{scenario=flow.scenarios.find(s=>s.id===e.target.value&&s.kind===outcome)||null;if(scenario)lastScenarioByFlow.set(`${flow.id}:${outcome}`,scenario.id);selected=null;hashNotice='';renderFlow();writeHash('push');};
  const all=el('option','전체 분류');all.value='';$('category').append(all);for(const c of new Set(data.flows.map(f=>f.category).filter(Boolean))){const o=el('option',c);o.value=c;$('category').append(o);}$('category').onchange=renderList;
  $('zoom-in').onclick=()=>{zoom=Math.min(2,zoom+.2);applyZoom();};$('zoom-out').onclick=()=>{zoom=Math.min(zoom,Math.max(.1,zoom-.2));applyZoom();};$('zoom-reset').onclick=()=>{zoom=1;applyZoom();};$('zoom-fit').onclick=()=>{const w=Number($('chart').querySelector('svg').getAttribute('viewBox').split(' ')[2]);zoom=Math.min(1,($('chart').clientWidth-4)/w);applyZoom();$('chart').scrollLeft=0;};
  const restore=()=>{if(readHash()){zoom=1;renderList();renderFlow();}};window.addEventListener('popstate',restore);window.addEventListener('hashchange',restore);
  $('search').oninput=renderList;$('search-clear').onclick=()=>{$('search').value='';renderList();$('search').focus();};$('filter-reset').onclick=()=>{$('search').value='';$('category').value='';renderList();$('search').focus();};$('menu').onclick=()=>{const open=document.body.classList.toggle('menu-open');$('menu').setAttribute('aria-expanded',String(open));if(open)$('search').focus();};document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.body.classList.contains('menu-open'))closeMenu(true);});
  readHash();renderList();renderFlow();
})();
