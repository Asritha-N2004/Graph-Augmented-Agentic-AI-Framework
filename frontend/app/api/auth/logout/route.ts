import {NextResponse} from 'next/server';
import {COOKIE,sameOrigin} from '../../../../lib/auth';
export async function POST(request:Request){
  if(!sameOrigin(request))return NextResponse.json({detail:'Request origin is not allowed.'},{status:403});
  const response=NextResponse.json({ok:true});response.cookies.set(COOKIE,'',{httpOnly:true,secure:process.env.NODE_ENV==='production',sameSite:'lax',path:'/',maxAge:0});return response;
}
