import { useState } from "react";
import { searchActors, type SearchResult } from "../api/client";

interface SearchPageProps {
  onSelectActor: (actorId: string) => void;
}

export default function SearchPage({ onSelectActor }: SearchPageProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch() {
    if (query.trim().length < 2) return;

    setLoading(true);
    setError("");
    setSearched(true);

    try {
      const response = await searchActors(query.trim());
      setResults(response.results);
    } catch {
      setError("Search failed.");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-section">
      <div className="page-title">
        <div className="eyebrow">INVESTIGATION</div>
        <h1>Search Intelligence</h1>
        <p>
          Search actors, handles and wallet identifiers across the
          intelligence database.
        </p>
      </div>

      <div className="search-box">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search handle, actor ID or wallet..."
        />

        <button onClick={handleSearch} disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {searched && !loading && results.length === 0 && !error && (
        <div className="empty-state">
          No matching intelligence found.
        </div>
      )}

      <div className="search-results">
        {results.map((result) => (
          <button
            className="result-card"
            key={`${result.type}-${result.id}-${result.matched_value}`}
            onClick={() => onSelectActor(result.id)}
          >
            <div>
              <span className="result-type">{result.type}</span>
              <strong>{result.matched_value}</strong>
            </div>

            <div>
              <span className="actor-id">{result.id}</span>
              <small>{result.risk_category}</small>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}