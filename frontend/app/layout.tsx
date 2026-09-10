import './globals.css';
import 'leaflet/dist/leaflet.css';
import type { Metadata } from 'next';
export const metadata: Metadata = { title: 'ThermaGuard AI | Thermal Intelligence', description: 'Explainable thermal event monitoring and decision support.' };
export default function Layout({children}:Readonly<{children:React.ReactNode}>){return <html lang="en"><body>{children}</body></html>}
