/** Settings: la configuración efectiva y el estado de los artefactos. */

import type { ReactNode } from 'react';
import { Card, Pill, Resolve, useApi } from '../components/ui';
import { api } from '../lib/api';

function Campo({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="row">
      <span style={{ color: 'var(--ink-2)' }}>{label}</span>
      <span className="mono">{value}</span>
    </div>
  );
}

export default function Settings() {
  const config = useApi(() => api.config());
  const status = useApi(() => api.status());

  return (
    <Resolve state={config}>
      {(cfg) => (
        <>
          <div className="page-head">
            <div>
              <h1>Settings</h1>
              <p className="page-sub">
                Configuración efectiva del entorno. Las credenciales nunca llegan aquí: el
                endpoint devuelve solo campos no sensibles, y hay una prueba que lo verifica.
              </p>
            </div>
            <Pill kind="accent">{cfg.app_env}</Pill>
          </div>

          <div className="cols-2">
            <div className="grid">
              <Card
                title="Artefactos del pipeline"
                hint="Qué ha producido el pipeline hasta ahora y qué comando genera cada cosa."
              >
                {status.kind === 'ready' ? (
                  Object.entries(status.data).map(([nombre, info]) => (
                    <div className="row" key={nombre}>
                      <div className="row-main">
                        <span className={`dot ${info.available ? 'pass' : 'skipped'}`} />
                        <div>
                          <div style={{ fontWeight: 500 }}>{nombre}</div>
                          <div className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>
                            {info.produced_by}
                          </div>
                        </div>
                      </div>
                      <Pill kind={info.available ? 'pass' : 'muted'}>
                        {info.available ? 'generado' : 'pendiente'}
                      </Pill>
                    </div>
                  ))
                ) : (
                  <p className="state">Consultando…</p>
                )}
              </Card>

              <Card title="Base de datos" hint="MariaDB — metadatos y cajas.">
                <Campo label="Host" value={cfg.database.host} />
                <Campo label="Puerto" value={cfg.database.port} />
                <Campo label="Base" value={cfg.database.name} />
                <Campo label="Usuario" value={cfg.database.user} />
                <Campo label="Contraseña" value={<Pill kind="muted">no expuesta</Pill>} />
              </Card>
            </div>

            <div className="grid">
              <Card
                title="Almacenamiento de objetos"
                hint="MinIO en local, S3 en producción. Solo cambia el endpoint."
              >
                <Campo label="Endpoint" value={cfg.object_storage.endpoint_url} />
                {cfg.object_storage.buckets.map((bucket) => (
                  <Campo key={bucket} label="Bucket" value={bucket} />
                ))}
              </Card>

              <Card title="Dónde se cambia esto">
                <p style={{ margin: '0 0 10px', color: 'var(--ink-2)', fontSize: 13 }}>
                  La configuración sale de <span className="mono">.env</span>, validada por{' '}
                  <span className="mono">pydantic-settings</span> al arrancar. Si falta una
                  credencial, el proceso aborta en el primer segundo diciendo cuál.
                </p>
                <p style={{ margin: 0, color: 'var(--ink-2)', fontSize: 13 }}>
                  Los umbrales de calidad viven aparte, en{' '}
                  <span className="mono">quality.yaml</span>, para que ajustar una política sea un
                  cambio de una línea que queda registrado en Git — y no una recompilación.
                </p>
              </Card>
            </div>
          </div>
        </>
      )}
    </Resolve>
  );
}
