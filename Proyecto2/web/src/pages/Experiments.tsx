/** Experiments (P3): las corridas reales de MLflow, con filtros y curvas. */

import { Card } from '../components/ui';

export default function Experiments() {
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
      </div>
      <Card title="En construcción">
        <p className="state">
          La tabla de corridas, la comparación y las curvas llegan en F8 T20.
        </p>
      </Card>
    </>
  );
}
