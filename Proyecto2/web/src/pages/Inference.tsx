/** Inference (P3): subir una imagen y predecir con la versión activa. Contenido en F9. */

import { Card } from '../components/ui';

export default function Inference() {
  return (
    <>
      <div className="page-head">
        <div>
          <h1>Inference</h1>
          <p className="page-sub">
            Sube una imagen o elige una del portal, recórtala y predice su clase con
            la versión de modelo activa.
          </p>
        </div>
      </div>
      <Card title="En construcción">
        <p className="state">Esta página se construye en F9.</p>
      </Card>
    </>
  );
}
