import { frontendEnv } from "./lib/api/env.ts";

export function App() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 p-8">
      <div className="mx-auto max-w-2xl rounded border border-slate-200 bg-white p-6">
        <h1 className="text-xl font-semibold">FinSignal</h1>
        <p className="mt-2 text-sm text-slate-600">
          Frontend workspace initialized (Phase F0 readiness baseline).
        </p>
        <p className="mt-2 text-xs text-slate-500">
          API Base: <code>{frontendEnv.apiBaseUrl}</code>
        </p>
      </div>
    </main>
  );
}

export default App;
