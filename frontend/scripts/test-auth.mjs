// Run against a local development server: node scripts/test-auth.mjs
import assert from 'node:assert/strict';
const base=process.env.AUTH_SMOKE_URL||'http://localhost:3000';
const credentials={email:process.env.AUTH_SMOKE_EMAIL||'analyst@cirp.local',password:process.env.AUTH_SMOKE_PASSWORD||'CIRP-Demo-2026'};
let response=await fetch(base,{redirect:'manual'});
assert.equal(response.status,307);assert.ok(response.headers.get('location').endsWith('/login'));
const endpoint=base+'/api/backend/api/analytics/overview';
assert.equal((await fetch(endpoint)).status,401);
response=await fetch(base+'/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...credentials,password:'incorrect-password'})});assert.equal(response.status,401);
response=await fetch(base+'/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(credentials)});assert.equal(response.status,200);
const cookie=response.headers.get('set-cookie');assert.ok(cookie.includes('HttpOnly'));assert.ok(cookie.includes('SameSite=lax'));
const headers={Cookie:cookie.split(';')[0]};
response=await fetch(endpoint,{headers});assert.equal(response.status,200);assert.ok((await response.json()).customers>0);
assert.equal((await fetch(base,{headers})).status,200);
assert.equal((await fetch(endpoint,{headers:{Cookie:'cirp_session=forged.invalid'}})).status,401);
assert.equal((await fetch(base+'/api/auth/login',{method:'POST',headers:{Origin:'https://untrusted.example','Content-Type':'application/json'},body:JSON.stringify(credentials)})).status,403);
response=await fetch(base+'/api/auth/logout',{method:'POST',headers});assert.equal(response.status,200);assert.ok(response.headers.get('set-cookie').includes('Max-Age=0'));
assert.equal((await fetch(endpoint)).status,401);
console.log('Passed: sign-in, invalid credentials, signed cookie, protected data, forged token, origin check, sign-out.');
