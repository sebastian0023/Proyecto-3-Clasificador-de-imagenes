/** Versions: el historial inmutable de releases. */

import { Card, Pill, Resolve, useApi } from '../components/ui';
import { api } from '../lib/api';

function Delta({ actual, previo }: { actual: number; previo: number }) {
  const diferencia = actual - previo;
  const color = diferencia > 0 ? 'var(--pass)' : diferencia < 0 ? 'var(--fail)' : 'var(--muted)';
  return (
    <span className="mono" style={{ color }}>
      {diferencia > 0 ? '+' : ''}
      {diferencia.toLocaleString('es')}
    </span>
  );
}

export default function Versions() {
  const state = useApi(() => api.versions());

  return (
    <Resolve state={state}>
      {(envelope) => {
        // El manifiesto viene en orden ascendente; la más reciente va arriba.
        const versions = [...envelope.data.versions].reverse();
        const ultima = versions[0];
        const previa = versions[1];

        return (
          <>
            <div className="page-head">
              <div>
                <h1>Versions</h1>
                <p className="page-sub">
                  Cada versión se identifica por la huella de su contenido. Una versión publicada
                  no se edita nunca: un cambio produce una versión nueva.
                </p>
              </div>
              <Pill kind="accent">
                {versions.length} {versions.length === 1 ? 'versión' : 'versiones'}
              </Pill>
            </div>

            <div className="cols-2">
              <Card title="Historial">
                {versions.length === 0 ? (
                  <p className="state">
                    Todavía no hay ninguna versión. Corre <code>dq release</code>.
                  </p>
                ) : (
                  versions.map((version) => (
                    <div className="row" key={version.version}>
                      <div className="row-main">
                        <Pill kind={version.quality_status === 'pass' ? 'pass' : 'fail'}>
                          v{version.version}
                        </Pill>
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontSize: 12.5 }}>{version.notes ?? 'sin notas'}</div>
                          <div className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>
                            {version.created_at.slice(0, 10)} ·{' '}
                            {version.dataset_fingerprint.slice(0, 12)}…
                          </div>
                        </div>
                      </div>
                      <div style={{ textAlign: 'right', flex: 'none' }}>
                        <div className="mono" style={{ fontSize: 12 }}>
                          {version.counts.images} img
                        </div>
                        <div className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>
                          {version.counts.annotations} cajas
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </Card>

              <div className="grid">
                {ultima && previa && (
                  <Card title="Diff" hint={`v${previa.version} → v${ultima.version}`}>
                    <div className="row">
                      <span>Imágenes</span>
                      <Delta actual={ultima.counts.images} previo={previa.counts.images} />
                    </div>
                    <div className="row">
                      <span>Bounding boxes</span>
                      <Delta actual={ultima.counts.annotations} previo={previa.counts.annotations} />
                    </div>
                    <div className="row">
                      <span>Categorías</span>
                      <Delta actual={ultima.counts.categories} previo={previa.counts.categories} />
                    </div>
                  </Card>
                )}

                {ultima && (
                  <Card
                    title="Última versión"
                    hint="Tres huellas distintas: los datos, el reporte de calidad y el reparto. Cambiar cualquiera produce una versión nueva."
                  >
                    <div className="row">
                      <span>Calidad</span>
                      <Pill kind={ultima.quality_status === 'pass' ? 'pass' : 'fail'}>
                        {ultima.quality_status}
                      </Pill>
                    </div>
                    <div className="row">
                      <span>Almacenamiento</span>
                      <span className="mono" style={{ fontSize: 11, wordBreak: 'break-all' }}>
                        {ultima.storage_uri}
                      </span>
                    </div>
                    {(
                      [
                        ['dataset', ultima.dataset_fingerprint],
                        ['calidad', ultima.quality_report_fingerprint],
                        ['splits', ultima.splits_fingerprint],
                      ] as const
                    ).map(([label, hash]) => (
                      <div className="row" key={label}>
                        <span>{label}</span>
                        <span className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>
                          {hash.slice(0, 20)}…
                        </span>
                      </div>
                    ))}
                    {ultima.quality_status === 'fail' && (
                      <div className="banner warn">
                        Esta versión se publicó con la compuerta en fail (se usó{' '}
                        <span className="mono">--force</span>). No debería promoverse a producción.
                      </div>
                    )}
                  </Card>
                )}
              </div>
            </div>
          </>
        );
      }}
    </Resolve>
  );
}
