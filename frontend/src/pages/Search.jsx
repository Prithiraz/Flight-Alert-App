import { useState } from 'react';
import { searchFlights } from '../lib/api';

const inputStyle = { padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' };

export default function Search() {
  const [form, setForm] = useState({
    from_iata: '',
    to_iata: '',
    departure_date: '',
    return_date: '',
    passengers: 1,
    cabin_class: 'economy',
  });
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function handleChange(e) {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    setResults(null);
    try {
      const data = await searchFlights({
        ...form,
        passengers: Number(form.passengers),
        return_date: form.return_date || undefined,
      });
      const sorted = (data.results || data.flights || data || []).slice().sort((a, b) => (a.price ?? 0) - (b.price ?? 0));
      setResults(sorted);
    } catch (err) {
      setError(err.message || 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: '700px', margin: '2rem auto', padding: '0 1rem' }}>
      <h2>Search Flights</h2>
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
          Departure Date
          <input type="date" name="departure_date" value={form.departure_date} onChange={handleChange} required style={inputStyle} />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          Return Date (optional)
          <input type="date" name="return_date" value={form.return_date} onChange={handleChange} style={inputStyle} />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          Passengers
          <input type="number" name="passengers" value={form.passengers} onChange={handleChange} min="1" max="9" required style={inputStyle} />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          Cabin Class
          <select name="cabin_class" value={form.cabin_class} onChange={handleChange} style={inputStyle}>
            <option value="economy">Economy</option>
            <option value="premium_economy">Premium Economy</option>
            <option value="business">Business</option>
            <option value="first">First</option>
          </select>
        </label>
        <div style={{ gridColumn: '1 / -1' }}>
          <button type="submit" disabled={loading} style={{ padding: '0.6rem 1.5rem', background: '#1e3a5f', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
            {loading ? 'Searching…' : 'Search'}
          </button>
        </div>
      </form>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      {results && results.length === 0 && <p>No flights found.</p>}

      {results && results.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {results.map((flight, i) => (
            <li key={flight.id || i} style={{ border: '1px solid #ddd', borderRadius: '6px', padding: '0.75rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong>{flight.from_iata || flight.origin} → {flight.to_iata || flight.destination}</strong>
                {flight.departure_date && <span style={{ marginLeft: '0.5rem', color: '#555', fontSize: '0.9rem' }}>{flight.departure_date}</span>}
                {flight.airline && <span style={{ marginLeft: '0.5rem', color: '#555', fontSize: '0.9rem' }}>· {flight.airline}</span>}
                {flight.duration && <span style={{ marginLeft: '0.5rem', color: '#555', fontSize: '0.9rem' }}>· {flight.duration}</span>}
              </div>
              <strong style={{ color: '#1e3a5f', fontSize: '1.1rem' }}>
                {flight.currency || '£'}{flight.price}
              </strong>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
