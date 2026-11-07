import { createRootRoute, Outlet } from '@tanstack/react-router';
import { Toaster } from 'sonner';
import { Shell } from '@/components/sentinel/Shell';
export const Route=createRootRoute({component:()=> <><Shell><Outlet/></Shell><Toaster theme="dark" richColors/></>});
