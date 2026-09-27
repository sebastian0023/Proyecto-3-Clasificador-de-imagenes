/**
 * Training (P3): elegir un release aprobado, ver su procedencia y el split
 * 70/20/10, y (en T19) configurar y lanzar un entrenamiento.
 *
 * Slice A (este archivo): selector de release aprobado, panel de procedencia y
 * generación/vista del manifiesto con la tabla de conteos por clase y partición.
 * El formulario de parámetros y el seguimiento del trabajo llegan en los
 * siguientes slices de T19.
 */

import { useEffect, useState } from 'react';
import { Card, Pill } from '../components/ui';
import {
  api,
  type ManifestCreated,
  type P3ReleaseDetail,
  type P3ReleaseSummary,
  type SplitName,
} from '../lib/api';

const SPLITS: SplitName[] = ['train', 'val', 'test'];
/** Semilla por defecto del manifiesto (contrato §3: seed por defecto 42). */
const SEED = 42;

/** Suma los conteos de una clase en las tres particiones. */
function totalPorClase(counts: ManifestCreated['counts'], className: string): number {
  return SPLITS.reduce((acc, split) => acc + (counts.crops[split][className] ?? 0), 0);
}

export default function Training() {
  const [releases, setReleases] = useState<P3ReleaseSummary[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [provenance, setProvenance] = useState<P3ReleaseDetail | null>(null);
  const [manifest, setManifest] = useState<ManifestCreated | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Releases aprobados: la lista de la que se puede elegir.
  useEffect(() => {
    let cancelled = false;
    api.p3
      .releases(true)
      .then((res) => {
        if (cancelled) return;
        setReleases(res.releases);
        setSelectedId((prev) => prev ?? res.releases[0]?.release_id ?? null);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Error desconocido');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Procedencia del release elegido. Cambiar de release descarta el manifiesto
  // anterior: pertenece a otro release.
  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setProvenance(null);
    setManifest(null);
    api.p3
      .release(selectedId)
      .then((detail) => {
        if (!cancelled) setProvenance(detail);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Error desconocido');
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  async function generarManifiesto() {
    if (!selectedId) return;
    setGenerating(true);
    setError(null);
    try {
      setManifest(await api.p3.createManifest(selectedId, SEED));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error desconocido');
    } finally {
      setGenerating(false);
    }
  }

  const selected = releases?.find((r) => r.release_id === selectedId) ?? null;
  const classNames = manifest ? Object.keys(manifest.counts.crops.train) : [];

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Training</h1>
          <p className="page-sub">
            Elige un release aprobado, revisa su procedencia y el split 70/20/10,
            configura los parámetros y lanza un entrenamiento.
          </p>
        </div>
      </div>

      {error && <div className="banner warn">{error}</div>}

      <div className="cols-2">
        <Card title="Release aprobado" hint="Solo se listan los releases que pasaron la compuerta de calidad de P2.">
          {releases === null ? (
            <p className="state">Cargando releases…</p>
          ) : releases.length === 0 ? (
            <p className="state">No hay releases aprobados todavía.</p>
          ) : (
            <>
              <label className="row" style={{ gap: 10 }}>
                <span>Release</span>
                <select
                  className="campo"
                  value={selectedId ?? ''}
                  onChange={(e) => setSelectedId(e.target.value)}
                >
                  {releases.map((r) => (
                    <option key={r.release_id} value={r.release_id}>
                      v{r.release_id} · {r.quality_status}
                    </option>
                  ))}
                </select>
              </label>

              {selected && (
                <>
                  <div className="row">
                    <span>Huella del dataset</span>
                    <span className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>
                      {selected.dataset_fingerprint.slice(0, 16)}…
                    </span>
                  </div>
                  <div className="row">
                    <span>Contenido</span>
                    <span className="mono" style={{ fontSize: 12 }}>
                      {selected.counts.images} img · {selected.counts.annotations} cajas
                    </span>
                  </div>
                </>
              )}
            </>
          )}
        </Card>

        <Card title="Procedencia" hint="Huellas que atan el release a su reporte de calidad y a su archivo.">
          {provenance === null ? (
            <p className="state">Selecciona un release para ver su procedencia.</p>
          ) : (
            <>
              <div className="row">
                <span>Reporte de calidad</span>
                <span className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>
                  {provenance.quality_report_fingerprint.slice(0, 16)}…
                </span>
              </div>
              <div className="row">
                <span>Archivo (sha256)</span>
                <span className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>
                  {provenance.archive_sha256.slice(0, 16)}…
                </span>
              </div>
              <div className="row">
                <span>Publicado en</span>
                <span style={{ display: 'inline-flex', gap: 4 }}>
                  {provenance.published_in.map((remote) => (
                    <Pill key={remote} kind="accent">
                      {remote.toUpperCase()}
                    </Pill>
                  ))}
                </span>
              </div>
            </>
          )}
        </Card>
      </div>

      <Card
        title="Manifiesto 70/20/10"
        hint="Se deriva del release aprobado: recorta las cajas COCO y reparte por grupos de duplicados sin fuga entre particiones."
        aside={
          <button
            type="button"
            className="ghost"
            onClick={generarManifiesto}
            disabled={!selectedId || generating}
          >
            {generating ? 'Generando…' : 'Generar manifiesto 70/20/10'}
          </button>
        }
      >
        {manifest === null ? (
          <p className="state">
            Aún no hay manifiesto para este release. Genéralo para ver los conteos por clase y
            partición.
          </p>
        ) : (
          <>
            <div className="row">
              <span>Manifiesto</span>
              <span className="mono" style={{ fontSize: 12 }}>
                {manifest.manifest_id}
              </span>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Clase</th>
                  {SPLITS.map((split) => (
                    <th key={split} className="num">
                      {split}
                    </th>
                  ))}
                  <th className="num">total</th>
                </tr>
              </thead>
              <tbody>
                {classNames.map((className) => (
                  <tr key={className}>
                    <td>{className}</td>
                    {SPLITS.map((split) => (
                      <td key={split} className="num mono">
                        {manifest.counts.crops[split][className] ?? 0}
                      </td>
                    ))}
                    <td className="num mono">{totalPorClase(manifest.counts, className)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </Card>
    </>
  );
}
