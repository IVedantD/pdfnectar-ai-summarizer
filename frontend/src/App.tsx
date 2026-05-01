import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { supabase } from "@/integrations/supabase/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { toast } from "sonner";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Auth from "./pages/Auth.tsx";
import Index from "./pages/Index.tsx";
import NotFound from "./pages/NotFound.tsx";
import ResetPassword from "./pages/ResetPassword.tsx";

const queryClient = new QueryClient();

function hashSearchParams(): URLSearchParams {
  const raw = window.location.hash.startsWith("#") ? window.location.hash.slice(1) : window.location.hash;
  return new URLSearchParams(raw);
}

/** True while the URL still carries Supabase OAuth callback data (PKCE, implicit, or provider error). */
function hasOAuthReturnParams(): boolean {
  const search = window.location.search;
  const hash = window.location.hash;
  const params = new URLSearchParams(search);
  if (params.has("code")) return true;
  if (params.has("error")) return true;
  if (hash.includes("access_token")) return true;
  if (hash.includes("error=")) return true;
  return false;
}

function readOAuthErrorFromUrl(): string | null {
  const q = new URLSearchParams(window.location.search);
  const fromQuery =
    q.get("error_description")?.replace(/\+/g, " ") || q.get("error");
  const h = hashSearchParams();
  const fromHash =
    h.get("error_description")?.replace(/\+/g, " ") || h.get("error");
  return fromQuery || fromHash || null;
}

async function clearOAuthUrlAndLocalAuth(): Promise<void> {
  const path = window.location.pathname + window.location.search;
  window.history.replaceState({}, document.title, path);
  try {
    await supabase.auth.signOut({ scope: "local" });
  } catch {
    /* ignore */
  }
}

/** Max time to wait for Supabase to turn ?code= / #access_token into a session before giving up. */
const OAUTH_CALLBACK_WAIT_MS = 15_000;

const OAUTH_FAIL_HINT =
  "Supabase needs your PC clock within a few minutes of real time. In Windows: Settings → Time & language → Date & time → turn on “Set time automatically” and “Set time zone automatically”, then restart the browser and try Google again.";

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { session, loading } = useAuth();
  const waitingForOAuth = !session && hasOAuthReturnParams();
  const [, rerender] = useState(0);
  const oauthUrlHandled = useRef(false);

  // Provider returned an error in the URL (no need to wait 15s).
  useEffect(() => {
    if (session || oauthUrlHandled.current) return;
    const providerErr = readOAuthErrorFromUrl();
    if (!providerErr) return;
    oauthUrlHandled.current = true;
    void clearOAuthUrlAndLocalAuth().then(() => {
      rerender((n) => n + 1);
      toast.error("Sign-in was rejected", {
        description: providerErr,
        duration: 12_000,
      });
    });
  }, [session]);

  useEffect(() => {
    if (!waitingForOAuth) return;
    const providerErr = readOAuthErrorFromUrl();
    if (providerErr) return;
    const timer = window.setTimeout(() => {
      void clearOAuthUrlAndLocalAuth().then(() => {
        rerender((n) => n + 1);
        toast.error("Sign-in did not finish", {
          description: OAUTH_FAIL_HINT,
          duration: 16_000,
        });
      });
    }, OAUTH_CALLBACK_WAIT_MS);
    return () => window.clearTimeout(timer);
  }, [waitingForOAuth]);

  if (loading || waitingForOAuth) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-4 border-gold border-t-transparent animate-spin"></div>
          <p className="text-sm font-medium">Securing session...</p>
        </div>
      </div>
    );
  }
  
  if (!session) {
    return <Navigate to="/auth" replace />;
  }
  
  return <>{children}</>;
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <AuthProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={
              <ProtectedRoute>
                <Index />
              </ProtectedRoute>
            } />
            <Route path="/auth" element={<Auth />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
