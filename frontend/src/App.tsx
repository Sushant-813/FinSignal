import { useState } from "react";
import { RouterProvider } from "react-router";
import { AppProviders } from "./app/providers/AppProviders.tsx";
import { createAppRouter } from "./app/router/routes.tsx";

export function App() {
  const [router] = useState(createAppRouter);

  return (
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  );
}

export default App;
