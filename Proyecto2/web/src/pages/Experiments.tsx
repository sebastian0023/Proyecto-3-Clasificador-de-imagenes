/**
 * Experiments (P3): las corridas reales de MLflow, con filtros, orden,
 * comparación y curvas (T20).
 *
 * Slice A (este archivo): tabla ordenable y filtrable por parámetros/métricas de
 * validación, y la tarjeta del candidato seleccionado (`selection.json`), sin
 * mostrar métricas de test. La comparación de 2+ corridas y las curvas
 * train/val llegan en el siguiente slice de T20.
 */

import { useEffect, useMemo, useState } from 'react';
import { Card, Pill } from '../components/ui';
import { api, type RunSummary, type Selection } from '../lib/api';

/** Métricas por las que se puede ordenar la tabla. */
type SortKey = 'best_val_accuracy' | 'best_val_loss' | 'best_epoch';

const fmt = (n: number): string => n.toFixed(3);
const shortId = (id: string): string => id.slice(0, 8);

export default function Experiments() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('best_val_accuracy');
  const [desc, setDesc] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.p3
      .runs({ status: 'FINISHED', order_by: 'val_accuracy', desc: true })
      .then((res) => {
        if (!cancelled) setRuns(res.runs);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Error desconocido');
      });
    // La selección puede no existir aún (menos de 10 corridas): no es un error.
    api.p3
      .selection()
      .then((s) => {
        if (!cancelled) setSelection(s);
      })
      .catch(() => {
        /* sin candidato todavía */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const shown = useMemo(() => {
    if (!runs) return [];
    const needle = filter.trim().toLowerCase();
    const filtered = needle
      ? runs.filter(
          (r) =>
            r.run_id.toLowerCase().includes(needle) ||
            JSON.stringify(r.params).toLowerCase().includes(needle),
        )
      : runs;
    return [...filtered].sort((a, b) => (desc ? b[sortKey] - a[sortKey] : a[sortKey] - b[sortKey]));
  }, [runs, filter, sortKey, desc]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setDesc((d) => !d);
    } else {
      setSortKey(key);
      setDesc(true);
    }
  }

  const arrow = (key: SortKey) => (key === sortKey ? (desc ? ' ▼' : ' ▲') : '');

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Experiments</h1>
          <p className="page-sub">
            Corridas de MLflow con filtros por parámetros y métricas de validación,
            comparación de corridas y curvas de entrenamiento.
          </p>
        </div>
        {runs && <Pill kind="accent">{runs.length} corridas</Pill>}
      </div>

      {error && <div className="banner warn">{error}</div>}

      {selection && (
        <Card
          title="Candidato seleccionado"
          hint="Elegido por validación (selection.json). Las métricas de test no se muestran aquí: se revelan solo en Evaluation, tras cerrar la selección."
        >
          <div className="row">
            <span>Corrida</span>
            <span className="mono" style={{ fontSize: 12 }}>
              {selection.run_id}
            </span>
          </div>
          <div className="row">
            <span>Regla</span>
            <span style={{ fontSize: 12 }}>{selection.rule}</span>
          </div>
          <div className="row">
            <span>val_accuracy · val_loss</span>
            <span className="mono">
              {fmt(selection.val_accuracy)} · {fmt(selection.val_loss)}
            </span>
          </div>
          <div className="row">
            <span>Mejor época · corridas evaluadas</span>
            <span className="mono">
              {selection.best_epoch} · {selection.candidates}
            </span>
          </div>
        </Card>
      )}

      <Card title="Corridas">
        <label className="row" style={{ gap: 10 }}>
          <span>Filtrar</span>
          <input
            className="campo"
            type="search"
            placeholder="optimizer, run_id, learning_rate…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </label>

        {runs === null ? (
          <p className="state">Cargando corridas…</p>
        ) : shown.length === 0 ? (
          <p className="state">Ninguna corrida coincide con el filtro.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>run</th>
                <th>optimizer</th>
                <th className="num">batch</th>
                <th className="num">lr</th>
                <th className="num sort-th">
                  <button type="button" onClick={() => toggleSort('best_val_accuracy')}>
                    val_acc{arrow('best_val_accuracy')}
                  </button>
                </th>
                <th className="num sort-th">
                  <button type="button" onClick={() => toggleSort('best_val_loss')}>
                    val_loss{arrow('best_val_loss')}
                  </button>
                </th>
                <th className="num sort-th">
                  <button type="button" onClick={() => toggleSort('best_epoch')}>
                    época{arrow('best_epoch')}
                  </button>
                </th>
                <th>estado</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((run) => (
                <tr key={run.run_id}>
                  <td className="mono" title={run.run_id}>
                    {shortId(run.run_id)}
                  </td>
                  <td>{run.params.optimizer}</td>
                  <td className="num mono">{run.params.batch_size}</td>
                  <td className="num mono">{run.params.learning_rate}</td>
                  <td className="num mono">{fmt(run.best_val_accuracy)}</td>
                  <td className="num mono">{fmt(run.best_val_loss)}</td>
                  <td className="num mono">{run.best_epoch}</td>
                  <td>
                    <Pill kind={run.status === 'FINISHED' ? 'pass' : 'muted'}>{run.status}</Pill>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </>
  );
}
