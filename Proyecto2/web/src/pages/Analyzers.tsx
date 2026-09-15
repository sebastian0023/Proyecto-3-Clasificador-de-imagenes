/** Analyzers: el detalle de cada check, con su valor contra su umbral. */

import { useState } from 'react';
import { BarChart } from '../components/charts';
import DedupeAction from '../components/DedupeAction';
import { Card, Pill, Resolve, Tile, useApi } from '../components/ui';
import { api, comparison, formatMetric, type CheckResult } from '../lib/api';

const POR_QUE: Record<string, string> = {
  min_images_per_class:
    'Sin volumen no hay dataset. Se cuentan imágenes distintas que contienen al menos una caja de la clase, no cajas: una foto con siete coches aporta una imagen a car, no siete.',
  small_objects:
    'Los detectores reducen la imagen varias veces antes de decidir. Un objeto que ocupa una fracción diminuta de su foto desaparece en ese proceso y no enseña nada.',
  class_imbalance:
    'Con un desbalance grande al modelo le sale rentable ignorar la clase rara y aun así acertar casi siempre: aprende a no detectarla nunca.',
  duplicates:
    'El pHash compara cómo se ve la imagen, así que detecta copias recomprimidas o reescaladas que un md5 no vería. Inflan el conteo por clase sin aportar variedad.',
  degenerate_boxes:
    'Cajas cuyas coordenadas exceden el borde de su imagen. Las de área nula no llegan aquí: la validación de la ingesta las rechaza antes.',
  spatial_bias:
    'Si los objetos caen siempre en la misma zona, el modelo aprende la posición en vez del objeto y falla cuando uno entra por la orilla.',
};

function Detalle({ check }: { check: CheckResult }) {
  const tone = check.status === 'fail' ? (check.severity === 'error' ? 'fail' : 'c') : 'b';
  return (
    <>
      <div className="tiles">
        <Tile value={formatMetric(check.observed, check.name)} label="Observado" tone={tone} />
        <Tile value={formatMetric(check.threshold, check.name)} label="Umbral" tone="d" />
        <Tile
          value={check.status === 'fail' ? check.severity : check.status}
          label={check.status === 'fail' ? 'Severidad' : 'Estado'}
          tone={tone}
        />
        <Tile value={check.offenders.length} label="Infractores" tone="a" />
      </div>

      <div className="cols-2">
        <Card title="Qué midió">
          <p style={{ margin: '0 0 12px', color: 'var(--ink-2)' }}>{check.message}</p>
          <div className="row">
            <span>Regla</span>
            <span className="mono">
              {formatMetric(check.observed, check.name)} {comparison(check.name)}{' '}
              {formatMetric(check.threshold, check.name)}
            </span>
          </div>
          <div className="row">
            <span>Si falla</span>
            <span>{check.severity === 'error' ? 'bloquea la publicación' : 'solo avisa'}</span>
          </div>
        </Card>

        <Card title="Por qué importa">
          <p style={{ margin: 0, color: 'var(--ink-2)' }}>
            {POR_QUE[check.name] ?? 'Sin descripción.'}
          </p>
        </Card>
      </div>

      {/* La accion vive junto al analizador que la justifica, no en un menu
          aparte: quien mira los 39 duplicados es quien decide eliminarlos. */}
      {check.name === 'duplicates' && (
        <div style={{ marginTop: 14 }}>
          <DedupeAction />
        </div>
      )}

      {check.offenders.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <Card
            title="Infractores"
            hint={`${check.offenders.length} identificadores. Los primeros 60:`}
          >
            <div className="mono" style={{ color: 'var(--ink-2)', wordBreak: 'break-all' }}>
              {check.offenders.slice(0, 60).join(', ')}
              {check.offenders.length > 60 && ' …'}
            </div>
          </Card>
        </div>
      )}
    </>
  );
}

export default function Analyzers() {
  const [activo, setActivo] = useState<string | null>(null);
  const quality = useApi(() => api.quality());

  return (
    <Resolve state={quality}>
      {(envelope) => {
        const checks = envelope.data.checks;
        const actual = checks.find((c) => c.name === activo) ?? checks[0];

        // Cada check contra su propio umbral, normalizado a 100% = el umbral.
        // Es la unica forma de ponerlos en la misma grafica: sus unidades no
        // son comparables entre si (imagenes, proporciones, veces).
        const resumen = checks
          .filter((c) => c.status !== 'skipped' && c.threshold > 0)
          .map((c) => ({
            label: c.name.replace(/_/g, ' ').slice(0, 13),
            value: Math.round((c.observed / c.threshold) * 100),
          }));

        return (
          <>
            <div className="page-head">
              <div>
                <h1>Analyzers</h1>
                <p className="page-sub">
                  Seis ángulos sobre el mismo dataset. Los analizadores solo miden: la decisión de
                  bloquear es de la compuerta.
                </p>
              </div>
            </div>

            <div className="tabs">
              {checks.map((check) => (
                <button
                  key={check.name}
                  aria-pressed={actual?.name === check.name}
                  onClick={() => setActivo(check.name)}
                >
                  {check.name.replace(/_/g, ' ')}
                  <Pill kind={check.status === 'fail' ? check.severity : check.status}>
                    {check.status}
                  </Pill>
                </button>
              ))}
            </div>

            {actual && <Detalle check={actual} />}

            <div style={{ marginTop: 14 }}>
              <Card
                title="Todos los checks contra su umbral"
                hint="Normalizado: 100% es justo el umbral. Por encima, la regla no se cumple. Las unidades originales no son comparables entre sí."
              >
                <BarChart data={resumen} threshold={100} thresholdLabel="umbral = 100%" />
              </Card>
            </div>
          </>
        );
      }}
    </Resolve>
  );
}
