import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { supabase } from './lib/supabase';
import Header from './components/Header';
import Login from './pages/Login';
import Search from './pages/Search';
import Alerts from './pages/Alerts';

function ProtectedRoute({ session, children }) {
  if (!session) return <Navigate to="/" replace />;
  return children;
}

function App() {
  const [session, setSession] = useState(undefined);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session ?? null);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, sess) => {
      setSession(sess ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  if (session === undefined) return null;

  return (
    <BrowserRouter>
      {session && <Header />}
      <Routes>
        <Route path="/" element={session ? <Navigate to="/search" replace /> : <Login />} />
        <Route path="/search" element={<ProtectedRoute session={session}><Search /></ProtectedRoute>} />
        <Route path="/alerts" element={<ProtectedRoute session={session}><Alerts /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
