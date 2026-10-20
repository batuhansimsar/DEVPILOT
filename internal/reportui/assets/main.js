'use strict';
const el=id=>document.getElementById(id);
const node=(type,value,className)=>{const n=document.createElement(type);if(className)n.className=className;n.textContent=value;return n};
const fallback=a=>a?.length?a.join(', '):'Not detected';
async function refresh(){
 el('refresh').disabled=true;el('findings').replaceChildren(node('p','Inspecting project…','muted'));
 try{
  const response=await fetch('/api/doctor',{cache:'no-store'});if(!response.ok)throw new Error('API returned '+response.status);
  const data=await response.json();
  el('path').textContent=data.path;el('languages').textContent=fallback(data.languages);el('frameworks').textContent=fallback(data.frameworks);el('manager').textContent=data.package_manager||'Not detected';el('findingCount').textContent=String(data.findings.length);
  if(!data.findings.length)el('findings').replaceChildren(node('p','No findings from the checks performed. This does not guarantee builds or tests pass.','muted'));
  else el('findings').replaceChildren(...data.findings.map(f=>{
   const row=node('article','','finding');row.append(node('span',f.level.toUpperCase(),'severity '+f.level),node('strong',f.message),node('small',f.code,'muted'));
   if(f.remedy)row.append(node('p',f.remedy));return row;
  }));
  if(!data.tests)el('tests').replaceChildren(node('p','No test command discovered.','muted'));
  else {const tests=node('div','','test-command');tests.append(node('code',[data.tests.executable,...data.tests.arguments].join(' ')));el('tests').replaceChildren(tests)}
 }catch(e){el('findings').replaceChildren(node('p',e.message,'error'))}finally{el('refresh').disabled=false}
}
el('refresh').addEventListener('click',refresh);refresh();
