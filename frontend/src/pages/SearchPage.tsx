import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight, Clock3, Search, Sparkles, TrendingUp, X } from "lucide-react";
import { searchActors, type SearchResult } from "../api/client";

interface SearchPageProps {
  onSelectActor: (actorId: string) => void;
}

interface FrequentActor {
  id: string;
  handle: string;
  category?: string;
  count: number;
  lastSearched: number;
}

const STORAGE_KEY = "decypher_frequent_actors";

function loadFrequentActors(): FrequentActor[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((item) => item && typeof item.id === "string")
      .sort((a, b) => Number(b.count || 0) - Number(a.count || 0) || Number(b.lastSearched || 0) - Number(a.lastSearched || 0))
      .slice(0, 6);
  } catch {
    return [];
  }
}

function recordFrequentActor(result: SearchResult) {
  const current = loadFrequentActors();
  const existing = current.find((item) => item.id === result.id);
  const next = existing
    ? current.map((item) =>
        item.id === result.id
          ? {
              ...item,
              handle: result.matched_value || item.handle,
              category: result.risk_category || item.category,
              count: item.count + 1,
              lastSearched: Date.now(),
            }
          : item,
      )
    : [
        ...current,
        {
          id: result.id,
          handle: result.matched_value,
          category: result.risk_category,
          count: 1,
          lastSearched: Date.now(),
        },
      ];

  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(
      next
        .sort((a, b) => b.count - a.count || b.lastSearched - a.lastSearched)
        .slice(0, 6),
    ),
  );
}

export default function SearchPage({ onSelectActor }: SearchPageProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");
  const [frequentActors, setFrequentActors] = useState<FrequentActor[]>(loadFrequentActors);

  useEffect(() => {
    setFrequentActors(loadFrequentActors());
  }, []);

  async function handleSearch(searchValue = query) {
    const trimmed = searchValue.trim();
    if (trimmed.length < 2) return;

    setQuery(trimmed);
    setLoading(true);
    setError("");
    setSearched(true);

    try {
      const response = await searchActors(trimmed);
      setResults(response.results);
    } catch {
      setError("Search failed. Check the API connection and try again.");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  function openResult(result: SearchResult) {
    recordFrequentActor(result);
    setFrequentActors(loadFrequentActors());
    onSelectActor(result.id);
  }

  function openFrequent(actor: FrequentActor) {
    handleSearch(actor.id).then(() => onSelectActor(actor.id));
  }

  const searchHints = useMemo(
    () => ["Actor ID", "Handle", "Wallet", "PGP fingerprint"],
    [],
  );

  function clearHistory() {
    localStorage.removeItem(STORAGE_KEY);
    setFrequentActors([]);
  }

  return (
    <section className="page-section search-page">
      <div className="search-hero">
        <div className="search-hero-copy">
          <div className="eyebrow">INVESTIGATION WORKSPACE</div>
          <h1>Search Intelligence</h1>
          <p>
            Search across actor identities, personas, wallets and PGP
            fingerprints. Jump from one identifier straight into an
            investigation.
          </p>
        </div>
        <div className="search-hero-icon" aria-hidden="true">
          <Search size={26} />
        </div>
      </div>

      <div className="search-command">
        <div className="search-input-wrap">
          <Search size={17} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Search actor ID, handle, wallet or PGP fingerprint..."
            aria-label="Search intelligence"
            autoComplete="off"
          />
          {query && (
            <button
              className="search-clear"
              onClick={() => {
                setQuery("");
                setResults([]);
                setSearched(false);
              }}
              aria-label="Clear search"
            >
              <X size={15} />
            </button>
          )}
        </div>
        <button
          className="primary-button search-submit"
          onClick={() => handleSearch()}
          disabled={loading || query.trim().length < 2}
        >
          {loading ? "Searching…" : "Search"}
          {!loading && <ArrowUpRight size={15} />}
        </button>
      </div>

      <div className="search-hints">
        <span>Search by</span>
        {searchHints.map((hint) => (
          <span className="search-hint" key={hint}>
            {hint}
          </span>
        ))}
      </div>

      {frequentActors.length > 0 && (
        <section className="frequent-section">
          <div className="section-heading">
            <div>
              <div className="eyebrow">YOUR WORKSPACE</div>
              <h2>Frequently searched actors</h2>
              <p>Quick access to investigations you return to most often.</p>
            </div>
            <button className="text-button" onClick={clearHistory}>
              Clear
            </button>
          </div>

          <div className="frequent-grid">
            {frequentActors.map((actor, index) => (
              <button
                className="frequent-card"
                key={actor.id}
                onClick={() => openFrequent(actor)}
              >
                <div className="frequent-rank">{String(index + 1).padStart(2, "0")}</div>
                <div className="frequent-main">
                  <strong>{actor.handle}</strong>
                  <span>{actor.id}</span>
                </div>
                <div className="frequent-meta">
                  <span>{actor.count} {actor.count === 1 ? "search" : "searches"}</span>
                  <ArrowUpRight size={14} />
                </div>
              </button>
            ))}
          </div>
        </section>
      )}

      {!frequentActors.length && !searched && (
        <section className="search-intro-grid">
          <div className="search-intro-card">
            <div className="intro-icon"><TrendingUp size={18} /></div>
            <div>
              <strong>Frequently searched</strong>
              <p>Actors you open from search will appear here automatically.</p>
            </div>
          </div>
          <div className="search-intro-card">
            <div className="intro-icon"><Clock3 size={18} /></div>
            <div>
              <strong>Fast investigations</strong>
              <p>Search once, then jump back into the same actor without retyping identifiers.</p>
            </div>
          </div>
          <div className="search-intro-card">
            <div className="intro-icon"><Sparkles size={18} /></div>
            <div>
              <strong>Cross-identifier search</strong>
              <p>Handles, wallets and PGP fingerprints resolve back to their actor profile.</p>
            </div>
          </div>
        </section>
      )}

      {error && <div className="error">{error}</div>}

      {searched && !loading && results.length === 0 && !error && (
        <div className="empty-state search-empty">
          <Search size={22} />
          <strong>No matching intelligence</strong>
          <span>Try an actor ID, handle, wallet address or PGP fingerprint.</span>
        </div>
      )}

      {results.length > 0 && (
        <section className="results-section">
          <div className="section-heading results-heading">
            <div>
              <div className="eyebrow">MATCHES</div>
              <h2>{results.length} intelligence {results.length === 1 ? "result" : "results"}</h2>
              <p>Matching records for <strong>{query}</strong>.</p>
            </div>
          </div>

          <div className="search-results">
            {results.map((result) => (
              <button
                className="result-card"
                key={`${result.type}-${result.id}-${result.matched_value}`}
                onClick={() => openResult(result)}
              >
                <div className="result-main">
                  <span className="result-type">{result.type.replace("_", " ")}</span>
                  <strong>{result.matched_value}</strong>
                </div>
                <div className="result-side">
                  <span className="actor-id">{result.id}</span>
                  {result.risk_category && <small>{result.risk_category}</small>}
                </div>
                <ArrowUpRight className="result-arrow" size={15} />
              </button>
            ))}
          </div>
        </section>
      )}
    </section>
  );
}
