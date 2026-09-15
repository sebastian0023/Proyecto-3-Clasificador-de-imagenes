/** Splits: es honesto el reparto train/val/test. */

import { Legend, StackedBar } from '../components/charts';
import { Card, Pill, Resolve, Tile, useApi } from '../components/ui';
import { api, type SplitName } from '../lib/api';

const COLOR: Record<SplitName, string> = {
  train: 'var(--c2)',
  val: 'var(--c3)',
  test: 'var(--c4)',
};

const ORDEN: SplitName[] = ['train', 'val', 'test'];

export default function Splits() {
  const state = useApi(() => api.splits());

  return (
    <Resolve state={state}>
      {(envelope) => {
        const manifest = envelope.data;
        const total = ORDEN.reduce((sum, name) => sum + (manifest.counts[name] ?? 0), 0);

        const desviaciones = ORDEN.map((name) => {
          const objetivo = manifest.ratios[name] ?? 0;
          const real = total ? (manifest.counts[name] ?? 0) / total : 0;
          return { name, real, objetivo, delta: real - objetivo };
        });
        const peor = Math.max(...desviaciones.map((d) => Math.abs(d.delta)));

        return (
          <>
            <div className="page-head">
              <div>
                <h1>Splits</h1>
                <p className="page-sub">
                  Reparto en entrenamiento, validación y prueba. Estratificado por{' '}
                  <span className="mono">{manifest.stratified_by}</span>, y los casi-duplicados se
                  asignan juntos para que ninguna copia cruce de partición.
                </p>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <Pill kind="muted">seed = {manifest.seed}</Pill>
                <Pill kind="accent">{total} imágenes</Pill>
              </div>
            </div>

            <div className="tiles">
              {ORDEN.map((name) => (
                <Tile
                  key={name}
                  value={(manifest.counts[name] ?? 0).toLocaleString('es')}
                  label={`${name} · objetivo ${((manifest.ratios[name] ?? 0) * 100).toFixed(0)}%`}
                  tone={name === 'train' ? 'b' : name === 'val' ? 'c' : 'd'}
                />
              ))}
              <Tile
                value={`${(peor * 100).toFixed(1)}%`}
                label="Desviación máxima"
                tone={peor > 0.05 ? 'fail' : 'a'}
              />
            </div>

            <Card
              title="Reparto"
              hint="Cada segmento es proporcional al número de imágenes de esa partición."
            >
              <StackedBar
                segments={ORDEN.map((name) => ({
                  label: name,
                  value: manifest.counts[name] ?? 0,
                  color: COLOR[name],
                }))}
              />
              <Legend items={ORDEN.map((name) => ({ label: name, color: COLOR[name] }))} />
            </Card>

            <div className="cols-2" style={{ marginTop: 14 }}>
              <Card
                title="Proporción real contra objetivo"
                hint="Un reparto que se aleja del objetivo hace que las métricas de validación dejen de ser comparables entre corridas."
              >
                <table>
                  <thead>
                    <tr>
                      <th>Partición</th>
                      <th className="num">Imágenes</th>
                      <th className="num">Real</th>
                      <th className="num">Objetivo</th>
                      <th className="num">Δ</th>
                    </tr>
                  </thead>
                  <tbody>
                    {desviaciones.map((d) => (
                      <tr key={d.name}>
                        <td>{d.name}</td>
                        <td className="num mono">{manifest.counts[d.name] ?? 0}</td>
                        <td className="num mono">{(d.real * 100).toFixed(1)}%</td>
                        <td className="num mono">{(d.objetivo * 100).toFixed(0)}%</td>
                        <td
                          className="num mono"
                          style={{
                            color: Math.abs(d.delta) > 0.05 ? 'var(--fail)' : 'var(--muted)',
                          }}
                        >
                          {d.delta >= 0 ? '+' : ''}
                          {(d.delta * 100).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>

              <Card title="Integridad del reparto">
                <div className="row">
                  <div className="row-main">
                    <span className="dot pass" />
                    Ninguna imagen en dos particiones
                  </div>
                </div>
                <div className="row">
                  <div className="row-main">
                    <span className={`dot ${peor > 0.05 ? 'fail' : 'pass'}`} />
                    Desviación máxima del {(peor * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="row">
                  <div className="row-main">
                    <span className="dot pass" />
                    Reproducible con seed = {manifest.seed}
                  </div>
                </div>
                <p className="hint" style={{ marginTop: 14, marginBottom: 0 }}>
                  La primera no se comprueba en esta pantalla: el contrato{' '}
                  <span className="mono">SplitsManifest</span> rechaza un manifiesto donde una
                  imagen aparezca dos veces, o donde los conteos no cuadren con las asignaciones.
                  Si llegó hasta aquí, es que ya los cumple.
                </p>
              </Card>
            </div>
          </>
        );
      }}
    </Resolve>
  );
}
