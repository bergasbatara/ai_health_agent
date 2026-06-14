import { AppProviders } from "./AppProviders";
import { AppShell } from "./AppShell";
import { NotFoundPage } from "./NotFoundPage";
import { resolveRoute } from "./routes";

export function App() {
  const route = resolveRoute(window.location.pathname);

  return (
    <AppProviders>
      <AppShell>{route?.element ?? <NotFoundPage />}</AppShell>
    </AppProviders>
  );
}
