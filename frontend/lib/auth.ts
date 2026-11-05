import {createHmac, randomBytes, scryptSync, timingSafeEqual} from 'node:crypto';
import {cookies} from 'next/headers';

export const COOKIE='cirp_session';
export const SESSION_SECONDS=8*60*60;
export const localDemo=process.env.NODE_ENV!=='production'&&!process.env.AUTH_EMAIL&&!process.env.AUTH_PASSWORD;
export const publicDemo=localDemo||process.env.PUBLIC_DEMO_LOGIN==='true';
const demoSecret='cirp-development-session-key-local-demo-only';
function settings(){
  if(!localDemo&&(!process.env.AUTH_SECRET||process.env.AUTH_SECRET.length<32||!process.env.AUTH_EMAIL||!process.env.AUTH_PASSWORD)) throw Error('Configure AUTH_EMAIL, AUTH_PASSWORD and a 32-character AUTH_SECRET.');
  if(process.env.NODE_ENV==='production'&&!process.env.BACKEND_API_KEY)throw Error('Configure the shared BACKEND_API_KEY.');
  return {email:process.env.AUTH_EMAIL||'analyst@cirp.local',password:process.env.AUTH_PASSWORD||'CIRP-Demo-2026',secret:process.env.AUTH_SECRET||demoSecret};
}
export function credentialsMatch(email:string,password:string){
  const config=settings();
  const actual=scryptSync(password,config.secret,32);
  const expected=scryptSync(config.password,config.secret,32);
  return timingSafeEqual(actual,expected)&&email.trim().toLowerCase()===config.email.trim().toLowerCase();
}
export function issueSession(){
  const config=settings();
  const payload=Buffer.from(JSON.stringify({email:config.email,expires:Date.now()+SESSION_SECONDS*1000,id:randomBytes(16).toString('hex')})).toString('base64url');
  return payload+'.'+createHmac('sha256',config.secret).update(payload).digest('base64url');
}
export function verifySession(token:string|undefined):{email:string}|null{
  if(!token||token.length>2048)return null;
  try{
    const [payload,signature,...extra]=token.split('.');if(!payload||!signature||extra.length)return null;
    const config=settings();const expected=createHmac('sha256',config.secret).update(payload).digest();const actual=Buffer.from(signature,'base64url');
    if(actual.length!==expected.length||!timingSafeEqual(actual,expected))return null;
    const session=JSON.parse(Buffer.from(payload,'base64url').toString());
    return session.email===config.email&&typeof session.expires==='number'&&session.expires>Date.now()?{email:session.email}:null;
  }catch{return null}
}
export async function currentSession(){return verifySession((await cookies()).get(COOKIE)?.value)}
export function sameOrigin(request:Request){const origin=request.headers.get('origin');return !origin||origin===new URL(request.url).origin}
