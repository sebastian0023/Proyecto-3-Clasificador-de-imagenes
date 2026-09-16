/**
 * Shell de la aplicación: barra lateral y enrutado.
 *
 * El router es por hash y hecho a mano: siete pantallas no justifican traer
 * react-router, y así el build no depende de nada más que React.
 */

import { useEffect, useState } from 'react';
import Analyzers from './pages/Analyzers';
import Copilot from './pages/Copilot';
import Exploration from './pages/Exploration';
import Overview from './pages/Overview';
import Settings from './pages/Settings';
import Splits from './pages/Splits';
import Versions from './pages/Versions';

const PAGES = [
  { id: 'overview', label: 'Overview', glyph: '◴', element: <Overview /> },
  { id: 'analyzers', label: 'Analyzers', glyph: '◫', element: <Analyzers /> },
  { id: 'splits', label: 'Splits', glyph: '⑂', element: <Splits /> },
  { id: 'versions', label: 'Versions', glyph: '↻', element: <Versions /> },
  { id: 'copilot', label: 'Copilot', glyph: '✦', element: <Copilot /> },
  { id: 'exploration', label: 'Exploración', glyph: '⁘', element: <Exploration /> },
  { id: 'settings', label: 'Settings', glyph: '⚙', element: <Settings /> },
] as const;

type PageId = (typeof PAGES)[number]['id'];

const readHash = (): PageId => {
  const candidate = window.location.hash.replace('#/', '') as PageId;
  return PAGES.some((page) => page.id === candidate) ? candidate : 'overview';
};

export default function App() {
  const [page, setPage] = useState<PageId>(readHash);

  useEffect(() => {
    const onChange = () => setPage(readHash());
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);

  const current = PAGES.find((item) => item.id === page) ?? PAGES[0];

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" />
          <span className="brand-name">
            Dataset
            <br />
            Quality
          </span>
        </div>

        <nav className="nav">
          {PAGES.map((item) => (
            <button
              key={item.id}
              aria-current={item.id === page ? 'page' : undefined}
              onClick={() => {
                window.location.hash = `#/${item.id}`;
                setPage(item.id);
              }}
            >
              <span className="glyph" aria-hidden="true">
                {item.glyph}
              </span>
              <span className="label">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">
          MLOps · Proyecto 2
          <br />
          Calidad y versionado
        </div>
      </aside>

      {/* La clave remonta la pantalla al cambiar: cada una recarga sus datos. */}
      <main className="main" key={current.id}>
        {current.element}
      </main>
    </div>
  );
}
