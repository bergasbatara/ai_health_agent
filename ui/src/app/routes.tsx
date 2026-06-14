import { DashboardPage } from "../pages";

export interface AppRoute {
  path: string;
  label: string;
  element: JSX.Element;
}

export const appRoutes: AppRoute[] = [
  {
    path: "/",
    label: "Dashboard",
    element: <DashboardPage />,
  },
];

export function resolveRoute(pathname: string): AppRoute | null {
  return appRoutes.find((route) => route.path === pathname) ?? null;
}
