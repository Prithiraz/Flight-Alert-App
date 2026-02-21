import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import { createAlert, listAlerts, deleteAlert } from '../lib/api';

const inputStyle = { padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' };

export default function Alerts() {
  const [form, setForm] = useState({
    from_iata: '',
    to_iata: '',
    max_price: '',
    currency: 'GBP',
    departure_date: '',
    channels: 'email',
  });
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetchLoading, setFetchLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [userEmail, setUserEmail] = useState('');

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      const email = data?.user?.email || '';
      setUserEmail(email);
      if (email) fetchAlerts(email);
    });
  }, []);

  async function fetchAlerts(email) {
    setFetchLoading(true);
    try {
      const data = await listAlerts(email);
      setAlerts(data.alerts || data || []);
    } catch {
      // silently fail on initial load
    } finally {
      setFetchLoading(false);
    }
  }

  function handleChange(e) {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      await createAlert({
        ...form,
        max_price: Number(form.max_price),
        departure_date: form.departure_date || undefined,
        user_email: userEmail,
      });
      setSuccess('Alert created successfully.');
      setForm(prev => ({ ...prev, from_iata: '', to_iata: '', max_price: '', departure_date: '' }));
      fetchAlerts(userEmail);
    } catch (err) {
      setError(err.message || 'Failed to create alert');
    } finally {
      setLoading(false);
    }
  }

  async function handleDeactivate(alertId) {
    try {
      await deleteAlert(alertId, userEmail);
      setAlerts(prev => prev.filter(a => a.id !== alertId));
    } catch (err) {
      setError(err.message || 'Failed to deactivate alert');
    }
  }

  return (
    <div style={{ maxWidth: '700px', margin: '2rem auto', padding: '0 1rem' }}>
      <h2>Price Alerts</h2>

      <form onSubmit={handleSubmit} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          From (IATA)
          <input name="from_iata" value={form.from_iata} onChange={handleChange} placeholder="e.g. LHR" required style={inputStyle} />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          To (IATA)
          <input name="to_iata" value={form.to_iata} onChange={handleChange} placeholder="e.g. JFK" required style={inputStyle} />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          Max Price
          <input type="number" name="max_price" value={form.max_price} onChange={handleChange} min="0" required style={inputStyle} />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          Currency
          <select name="currency" value={form.currency} onChange={handleChange} style={inputStyle}>
            <option value="GBP">GBP</option>
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
          </select>
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          Departure Date (optional)
          <input type="date" name="departure_date" value={form.departure_date} onChange={handleChange} style={inputStyle} />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          Notification Channel
          <select name="channels" value={form.channels} onChange={handleChange} style={inputStyle}>
            <option value="email">Email</option>
            <option value="sms">SMS</option>
            <option value="push">Push</option>
          </select>
        </label>
        <div style={{ gridColumn: '1 / -1' }}>
          <button type="submit" disabled={loading} style={{ padding: '0.6rem 1.5rem', background: '#1e3a5f', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
            {loading ? 'Creating…' : 'Create Alert'}
          </button>
        </div>
      </form>

      {error && <p style={{ color: 'red' }}>{error}</p>}
      {success && <p style={{ color: 'green' }}>{success}</p>}

      <h3>Your Alerts</h3>
      {fetchLoading ? (
        <p>Loading alerts…</p>
      ) : alerts.length === 0 ? (
        <p>No alerts yet.</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {alerts.map(alert => (
            <li key={alert.id} style={{ border: '1px solid #ddd', borderRadius: '6px', padding: '0.75rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong>{alert.from_iata} → {alert.to_iata}</strong>
                <span style={{ marginLeft: '0.5rem', color: '#555', fontSize: '0.9rem' }}>Max: {alert.currency} {alert.max_price}</span>
                {alert.departure_date && <span style={{ marginLeft: '0.5rem', color: '#555', fontSize: '0.9rem' }}>· {alert.departure_date}</span>}
              </div>
              <button
                onClick={() => handleDeactivate(alert.id)}
                style={{ background: '#c0392b', color: '#fff', border: 'none', borderRadius: '4px', padding: '0.3rem 0.75rem', cursor: 'pointer' }}
              >
                Deactivate
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
