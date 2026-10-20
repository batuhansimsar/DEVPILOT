'use strict';
const el = id => document.getElementById(id);
const add = (parent, tag, className, value) => {const node=document.createElement(tag);if(className)node.className=className;if(value!==undefined)node.textContent=String(value);parent.appendChild(node);return node;};
const list = value => Array.isArray(value) ? value : [];
function render(report){
 el('stats').replaceChildren();el('overview').replaceChildren();el('findings').replaceChildren();
 const findings=list(report.findings);const warnings=findings.filter(f=>f.level==='warning').length;
 for(const [label,value] of [['Languages',list(report.languages).length],['Warnings',warnings],['Findings',findings.length]]){
  const box=add(el('stats'),'div','stat');add(box,'div','number',value);add(box,'div','label',label);
 }
 add(el('overview'),'p','', 'Workspace: '+String(report.path||'unknown'));
 for(const language of list(report.languages))add(el('overview'),'span','tag',language);
 for(const framework of list(report.frameworks))add(el('overview'),'span','tag',framework);
 if(report.package_manager)add(el('overview'),'p','', 'Package manager: '+report.package_manager);
 if(report.tests){const test=report.tests;add(el('overview'),'p','', 'Discovered test command (not executed):');add(el('overview'),'code','', [test.executable,...list(test.arguments)].join(' '));}
 if(!list(report.languages).length)add(el('overview'),'p','', 'No supported project manifest detected.');
 for(const finding of findings){const row=add(el('findings'),'article','panel finding '+String(finding.level||'info'));add(row,'strong','',String(finding.level||'info').toUpperCase()+' · '+String(finding.code||'finding'));add(row,'p','',finding.message||'');if(finding.remedy)add(row,'p','label','Next: '+finding.remedy);}
 if(!findings.length)add(el('findings'),'p','', 'No findings reported.');
 el('status').textContent='Inspection complete';el('status').className='';
}
async function refresh(){const button=el('refresh');button.disabled=true;el('status').textContent='Inspecting project…';try{const response=await fetch('/api/report',{cache:'no-store'});if(!response.ok)throw new Error('HTTP '+response.status);render(await response.json());}catch(error){el('status').textContent='Diagnosis unavailable: '+error.message;el('status').className='error';}finally{button.disabled=false;}}
el('refresh').addEventListener('click',refresh);refresh();
