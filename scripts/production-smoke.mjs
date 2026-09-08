const base=(process.env.PRODUCTION_URL||"https://saudi-business-web.vercel.app").replace(/\/$/,"");
const attempts=Number(process.env.SMOKE_ATTEMPTS||12);
const delayMs=Number(process.env.SMOKE_DELAY_MS||15000);
const timeoutMs=Number(process.env.SMOKE_TIMEOUT_MS||10000);
const sleep=(ms)=>new Promise(r=>setTimeout(r,ms));
async function get(path,{json=false}={}){const c=new AbortController();const timer=setTimeout(()=>c.abort(),timeoutMs);try{const r=await fetch(base+path,{signal:c.signal,headers:{"User-Agent":"Saudi-Business-Production-Smoke/1.0","Cache-Control":"no-cache"}});const body=json?await r.json().catch(()=>null):await r.text();return {ok:r.ok,status:r.status,body};}finally{clearTimeout(timer)}}
async function check(){
  const home=await get("/");
  if(!home.ok) throw new Error(`home HTTP ${home.status}`);
  if(!home.body.includes("Decision cockpit")&&!home.body.includes("لوحة القرار")) throw new Error("premium homepage marker not deployed yet");
  for(const path of ["/tools","/tools/feasibility","/tools/funding","/login"]){const r=await get(path);if(!r.ok)throw new Error(`${path} HTTP ${r.status}`);}
  const health=await get("/api/deployment-health",{json:true});
  if(!health.ok) throw new Error(`deployment health HTTP ${health.status}: ${JSON.stringify(health.body)}`);
  if(health.body?.status!=="ready"||health.body?.frontend!=="ready"||health.body?.backend!=="ready") throw new Error(`deployment not ready: ${JSON.stringify(health.body)}`);
  if(health.body?.backendHealth?.db_connected!==true) throw new Error(`database not connected: ${JSON.stringify(health.body)}`);
  console.log("Saudi Business production smoke: PASS");
  console.log(JSON.stringify(health.body,null,2));
}
let last;
for(let i=1;i<=attempts;i++){
  try{await check();process.exit(0)}catch(e){last=e;console.warn(`Attempt ${i}/${attempts}: ${e instanceof Error?e.message:String(e)}`);if(i<attempts)await sleep(delayMs)}
}
throw last;
