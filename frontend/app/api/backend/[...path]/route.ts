import {NextResponse} from 'next/server';
import {currentSession,sameOrigin} from '../../../../lib/auth';
export const runtime='nodejs';
async function forward(request:Request,{params}:{params:Promise<{path:string[]}>}){
  if(!await currentSession())return NextResponse.json({detail:'Please sign in to continue.'},{status:401});
  if(request.method==='POST'&&!sameOrigin(request))return NextResponse.json({detail:'Request origin is not allowed.'},{status:403});
  const {path}=await params;
  // A fixed upstream origin and validated segments prevent an open proxy.
  if(path.some(p=>!p||p==='.'||p==='..'||p.includes('/')||p.includes('\\')))return NextResponse.json({detail:'Invalid API path.'},{status:400});
  const base=process.env.BACKEND_URL||process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000';
  const upstream=new URL('/'+path.map(encodeURIComponent).join('/'),base);upstream.search=new URL(request.url).search;
  const headers:Record<string,string>={};
  if(request.headers.get('content-type'))headers['Content-Type']=request.headers.get('content-type')!;
  if(process.env.BACKEND_API_KEY)headers['X-CIRP-API-Key']=process.env.BACKEND_API_KEY;
  try{
    const response=await fetch(upstream,{method:request.method,headers,body:request.method==='POST'?await request.text():undefined,cache:'no-store',signal:AbortSignal.timeout(120000)});
    const outgoing=new Headers({'Cache-Control':'no-store'});
    for(const name of ['content-type','content-disposition'])if(response.headers.has(name))outgoing.set(name,response.headers.get(name)!);
    return new Response(response.body,{status:response.status,headers:outgoing});
  }catch{return NextResponse.json({detail:'The analytics service is unavailable. Please try again.'},{status:502})}
}
export {forward as GET,forward as POST};
