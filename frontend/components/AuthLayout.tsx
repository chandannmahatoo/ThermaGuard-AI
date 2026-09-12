import React from 'react';
import {Flame,ScanLine} from 'lucide-react';
import AuthHighlights from './AuthHighlights';
export default function AuthLayout({title,description,children}:{title:string;description:string;children:React.ReactNode}) {
  return <main className="login-page"><section className="login-art" aria-label="About ThermaGuard"><div className="brand"><span className="brand-mark"><Flame size={20}/></span><span>ThermaGuard <b>AI</b></span></div><div><span className="eyebrow">DETECT · UNDERSTAND · ACT</span><h1>{title}</h1><p>{description}</p><AuthHighlights/><div className="orbit" aria-hidden="true"><ScanLine size={80}/></div></div><small>SATELLITE EVIDENCE · GEOSPATIAL INTELLIGENCE</small></section>{children}</main>;
}
