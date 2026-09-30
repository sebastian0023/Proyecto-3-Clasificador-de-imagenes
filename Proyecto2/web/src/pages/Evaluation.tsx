/**
 * Evaluation (P3): la evaluación única en el test congelado (F9 T21).
 *
 * Se bloquea hasta que exista la selección del candidato: si el backend
 * responde 409 (o 423) no se revela ninguna métrica de test (criterio 6.3).
 * Con evaluación: accuracy, F1 macro, matriz de confusión (filas=real,
 * columnas=predicho), métricas por clase y baseline de la clase mayoritaria.
 * La galería de aciertos/errores y la exportación del CSV llegan en el
 * siguiente slice de T21.
 */

import { useEffect, useState } from 'react';
import { Card, Pill, Tile } from '../components/ui';
import { ApiError, api, type EvaluationReport } from '../lib/api';

const pct = (n: number): string => `${(n * 100).toFixed(1)}%`;

export default function Evaluation() {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [blocked, setBlocked] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.p3
      .evaluation()
      .then((r) => {
        if (!cancelled) setReport(r);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        // 409/423: la selección no está cerrada -> bloqueado, sin revelar test.
        if (e instanceof ApiError && (e.status === 409 || e.status === 423)) {
          setBlocked(e.message);
        } else {
          setError(e instanceof Error ? e.message : 'Error desconocido');
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const cm = report?.confusion_matrix;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Evaluation</h1>
          <p className="page-sub">
            Evaluación única en el test congelado. Se revela solo después de cerrar la
            selección del candidato.
          </p>
        </div>
        {report && (
          <Pill kind={report.passes_threshold ? 'pass' : 'fail'}>
            {report.passes_threshold ? 'supera' : 'no supera'} el umbral {pct(report.threshold)}
          </Pill>
        )}
      </div>

      {error && <div className="banner warn">{error}</div>}

      {blocked ? (
        <Card title="Evaluación bloqueada">
          <p className="state">
            {blocked}. El test no se revela hasta que exista la selección del modelo.
          </p>
        </Card>
      ) : report ? (
        <>
          <div className="tiles">
            <Tile value={pct(report.accuracy)} label="Accuracy" tone="a" />
            <Tile value={report.f1_macro.toFixed(3)} label="F1 macro" tone="b" />
            <Tile value={report.test_size} label="Recortes de test" tone="d" />
            <Tile value={pct(report.majority_baseline)} label="Baseline (mayoritaria)" tone="c" />
          </div>

          <div className="cols-2">
            <Card
              title="Matriz de confusión"
              hint="Filas = clase real, columnas = clase predicha."
            >
              {cm && (
                <table aria-label="Matriz de confusión">
                  <thead>
                    <tr>
                      <th>real \ predicho</th>
                      {cm.labels.map((label) => (
                        <th key={label} className="num">
                          {label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {cm.labels.map((label, i) => (
                      <tr key={label}>
                        <td>{label}</td>
                        {(cm.rows_true_cols_pred[i] ?? []).map((value, j) => (
                          <td
                            key={cm.labels[j]}
                            className="num mono"
                            style={i === j ? { fontWeight: 600, color: 'var(--pass)' } : undefined}
                          >
                            {value}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>

            <Card title="Por clase">
              <table>
                <thead>
                  <tr>
                    <th>clase</th>
                    <th className="num">precision</th>
                    <th className="num">recall</th>
                    <th className="num">f1</th>
                    <th className="num">support</th>
                  </tr>
                </thead>
                <tbody>
                  {report.per_class.map((row) => (
                    <tr key={row.class}>
                      <td>{row.class}</td>
                      <td className="num mono">{row.precision.toFixed(3)}</td>
                      <td className="num mono">{row.recall.toFixed(3)}</td>
                      <td className="num mono">{row.f1.toFixed(3)}</td>
                      <td className="num mono">{row.support}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="row" style={{ marginTop: 8 }}>
                <span>Clase mayoritaria: {report.majority_class}</span>
                <span className="mono">{pct(report.majority_baseline)}</span>
              </div>
            </Card>
          </div>
        </>
      ) : (
        !error && <p className="state">Cargando evaluación…</p>
      )}
    </>
  );
}
