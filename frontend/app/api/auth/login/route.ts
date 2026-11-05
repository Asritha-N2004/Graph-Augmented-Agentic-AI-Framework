import {NextResponse} from 'next/server';
import {COOKIE,SESSION_SECONDS,credentialsMatch,issueSession,sameOrigin} from '../../../../lib/auth';
export const runtime='nodejs';
const attempts=new Map<string,{count:number,until:number}>();
export async function POST(request:Request){
  if(!sameOrigin(request))return NextResponse.json({detail:'Request origin is not allowed.'},{status:403});
  let body;
  try{body=await request.json()}catch{return NextResponse.json({detail:'Enter your email and password.'},{status:400})}
  if(typeof body.email!=='string'||typeof body.password!=='string'||body.email.length>254||body.password.length>256||!body.email||!body.password)return NextResponse.json({detail:'Enter a valid email and password.'},{status:400});
  const key=body.email.trim().toLowerCase();const entry=attempts.get(key);
  if(entry&&entry.until>Date.now()&&entry.count>=5)return NextResponse.json({detail:'Too many attempts. Please try again in five minutes.'},{status:429,headers:{'Retry-After':'300'}});
  try{
    if(!credentialsMatch(body.email,body.password)){
      if(attempts.size>1000)attempts.clear();
      attempts.set(key,{count:entry&&entry.until>Date.now()?entry.count+1:1,until:entry&&entry.until>Date.now()?entry.until:Date.now()+300000});
      return NextResponse.json({detail:'Email or password is incorrect.'},{status:401});
    }
    attempts.delete(key);const response=NextResponse.json({ok:true});
    response.cookies.set(COOKIE,issueSession(),{httpOnly:true,secure:process.env.NODE_ENV==='production',sameSite:'lax',path:'/',maxAge:SESSION_SECONDS});
    response.headers.set('Cache-Control','no-store');return response;
  }catch{return NextResponse.json({detail:'Sign-in is not configured. Contact the workspace administrator.'},{status:503})}
}
