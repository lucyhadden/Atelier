import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";

import { DOMAINS, useDomain } from "./lib/domain";
import { BoardDetail } from "./pages/BoardDetail";
import { Boards } from "./pages/Boards";
import { ItemDetail } from "./pages/ItemDetail";
import { Pieces } from "./pages/Pieces";
import { SpaceDetail } from "./pages/SpaceDetail";
import { Spaces } from "./pages/Spaces";

const DESTINATIONS = [
  { to: "/", label: "Boards", end: true },
  { to: "/pieces", label: "Pieces", end: false },
  { to: "/spaces", label: "Spaces", end: false },
];

function Bar() {
  const [domain, setDomain] = useDomain();
  const { search } = useLocation();

  return (
    <header className="bar">
      <Link className="bar__mark" to={{ pathname: "/", search }} aria-label="Atelier, home">
        Atelier
      </Link>

      <nav className="bar__nav" aria-label="Sections">
        {DESTINATIONS.map((d) => (
          <NavLink key={d.to} className="bar__link" to={{ pathname: d.to, search }} end={d.end}>
            {d.label}
          </NavLink>
        ))}
      </nav>

      <div className="bar__spacer" />

      <div className="switch" role="group" aria-label="What you are designing">
        {DOMAINS.map((d) => (
          <button
            key={d.key}
            type="button"
            className="switch__option"
            aria-pressed={domain === d.key}
            onClick={() => setDomain(d.key)}
          >
            {d.label}
          </button>
        ))}
      </div>
    </header>
  );
}

export function App() {
  return (
    <>
      <Bar />
      <main className="main">
        <Routes>
          <Route path="/" element={<Boards />} />
          <Route path="/boards/:boardId" element={<BoardDetail />} />
          <Route path="/pieces" element={<Pieces />} />
          <Route path="/items/:itemId" element={<ItemDetail />} />
          <Route path="/spaces" element={<Spaces />} />
          <Route path="/spaces/:spaceId" element={<SpaceDetail />} />
        </Routes>
      </main>
    </>
  );
}
