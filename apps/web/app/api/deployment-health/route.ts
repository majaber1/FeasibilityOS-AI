const backend=(process.env.BACKEND_API_URL||'').replace(/\/$/,'');

export async function GET(){
  if(!backend){
    return Response.json({status:'degraded',frontend:'ready',backend:'not_configured',missing:['BACKEND_API_URL']},{status:503,headers:{'Cache-Control':'no-store'}});
  }
  try{
    const [readyResponse,healthResponse]=await Promise.all([
      fetch(`${backend}/health/ready`,{cache:'no-store',signal:AbortSignal.timeout(5000)}),
      fetch(`${backend}/health`,{cache:'no-store',signal:AbortSignal.timeout(5000)}).catch(()=>null),
    ]);
    const raw=healthResponse?.ok?await healthResponse.json().catch(()=>({})):{};
    const health={
      service:typeof raw.service==='string'?raw.service:undefined,
      version:typeof raw.version==='string'?raw.version:undefined,
      environment:typeof raw.environment==='string'?raw.environment:undefined,
      db_enabled:typeof raw.db_enabled==='boolean'?raw.db_enabled:undefined,
      db_backend:typeof raw.db_backend==='string'?raw.db_backend:undefined,
      db_connected:typeof raw.db_connected==='boolean'?raw.db_connected:undefined,
      persistence:typeof raw.persistence==='string'?raw.persistence:undefined,
      object_storage:typeof raw.object_storage==='string'?raw.object_storage:undefined,
      storage_provider:typeof raw.storage_provider==='string'?raw.storage_provider:undefined,
    };
    return Response.json({status:readyResponse.ok?'ready':'degraded',frontend:'ready',backend:readyResponse.ok?'ready':'not_ready',backendHealth:health},{status:readyResponse.ok?200:503,headers:{'Cache-Control':'no-store'}});
  }catch(error){
    console.error('[deployment-health] backend unreachable',error instanceof Error?error.message:String(error));
    return Response.json({status:'degraded',frontend:'ready',backend:'unreachable'},{status:503,headers:{'Cache-Control':'no-store','Retry-After':'30'}});
  }
}
