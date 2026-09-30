/** Models (P3): las versiones de modelo publicadas y la versión activa. Contenido en F9. */

import { Card } from '../components/ui';

export default function Models() {
  return (
    <>
      <div className="page-head">
        <div>
          <h1>Models</h1>
          <p className="page-sub">
            Versiones de modelo publicadas en S3 con su tarjeta, y la versión activa
            que usa la inferencia.
          </p>
        </div>
      </div>
      <Card title="En construcción">
        <p className="state">Esta página se construye en F9.</p>
      </Card>
    </>
  );
}
