import {redirect} from 'next/navigation';
import {currentSession} from '../lib/auth';
import Dashboard from './dashboard';
export default async function Home(){
  if(!await currentSession())redirect('/login');
  return <Dashboard/>;
}
