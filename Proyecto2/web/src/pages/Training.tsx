/** Training (P3): elegir un release aprobado y lanzar un entrenamiento. */

import { Card } from '../components/ui';

export default function Training() {
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
      <Card title="En construcción">
        <p className="state">
          El selector de release, el formulario de configuración y el seguimiento
          del trabajo llegan en F8 T19.
        </p>
      </Card>
    </>
  );
}
