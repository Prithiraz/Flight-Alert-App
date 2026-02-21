import { Link, useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase';

export default function Header() {
  const navigate = useNavigate();

  async function handleLogout() {
    await supabase.auth.signOut();
    navigate('/');
  }

  return (
    <nav style={{ padding: '0.75rem 1.5rem', background: '#1e3a5f', display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
      <Link to="/search" style={{ color: '#fff', textDecoration: 'none', fontWeight: 500 }}>Search</Link>
      <Link to="/alerts" style={{ color: '#fff', textDecoration: 'none', fontWeight: 500 }}>Alerts</Link>
      <button
        onClick={handleLogout}
        style={{ marginLeft: 'auto', background: 'transparent', border: '1px solid #fff', color: '#fff', padding: '0.25rem 0.75rem', cursor: 'pointer', borderRadius: '4px' }}
      >
        Logout
      </button>
    </nav>
  );
}
