/** Evaluation (P3): la evaluación única en el test congelado. Contenido en F9. */

import { Card } from '../components/ui';

export default function Evaluation() {
  return (
    <>
      <div className="page-head">
        <div>
          <h1>Evaluation</h1>
          <p className="page-sub">
            Métricas de la evaluación única en el test congelado: accuracy, F1 por
            clase y matriz de confusión.
          </p>
        </div>
      </div>
      <Card title="En construcción">
        <p className="state">Esta página se construye en F9.</p>
      </Card>
    </>
  );
}
