/**
 * Copilot: preguntas en lenguaje natural sobre el reporte real.
 *
 * La pantalla es obligatoria en la rúbrica y se construye ahora aunque el
 * agente MCP sea del Frente 8. Lo que queda fijado aquí es el contrato de la
 * respuesta: la rúbrica exige que se VEAN las herramientas que consultó,
 * porque una cifra sin llamada detrás es una cifra inventada.
 */

import { useEffect, useRef, useState } from 'react';
import { Card, Pill } from '../components/ui';
import { api, type CopilotAnswer } from '../lib/api';

interface Turno {
  role: 'user' | 'bot';
  text: string;
  tools?: CopilotAnswer['tool_calls'];
}

const SUGERENCIAS = [
  '¿Por qué está bloqueado el release?',
  '¿Qué clases no llegan a 300 imágenes?',
  '¿Cuántos duplicados hay y a qué clase afectan?',
  '¿Qué checks pasan pero están cerca del umbral?',
];

const HERRAMIENTAS: [string, string][] = [
  ['get_quality_report', 'El veredicto completo: cada check con su valor y su umbral.'],
  ['get_failed_checks', 'Solo las reglas que no se cumplen. Para explicar un bloqueo.'],
  ['get_class_distribution', 'Imágenes y cajas por clase.'],
  ['get_split_report', 'Reparto train/val/test y su semilla.'],
  ['list_versions', 'Historial de releases con sus huellas.'],
];

export default function Copilot() {
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [borrador, setBorrador] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const finRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turnos]);

  async function enviar(pregunta: string) {
    const texto = pregunta.trim();
    if (!texto || ocupado) return;
    setBorrador('');
    setTurnos((previos) => [...previos, { role: 'user', text: texto }]);
    setOcupado(true);
    try {
      const respuesta = await api.copilot(texto);
      setTurnos((previos) => [
        ...previos,
        { role: 'bot', text: respuesta.answer, tools: respuesta.tool_calls },
      ]);
    } catch {
      setTurnos((previos) => [
        ...previos,
        {
          role: 'bot',
          text:
            'El agente todavía no está conectado: es el Frente 8, el servidor MCP con las ' +
            'herramientas de solo lectura. Esta pantalla ya está lista para cuando exista, y ' +
            'el contrato de la respuesta ya incluye las llamadas a herramientas.',
        },
      ]);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Dataset Copilot</h1>
          <p className="page-sub">
            Responde consultando el reporte real. Cada cifra que menciona viene de una llamada a
            una herramienta, y esas llamadas se muestran bajo la respuesta.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Pill kind="muted">solo lectura</Pill>
          <Pill kind="warning">Frente 8 pendiente</Pill>
        </div>
      </div>

      <div className="cols-2">
        <Card>
          <div className="chat">
            {turnos.length === 0 && (
              <p className="state">
                Pregunta lo que quieras sobre este dataset. El agente responde consultando{' '}
                <code>quality.json</code>, no su memoria.
              </p>
            )}
            {turnos.map((turno, index) => (
              <div key={index} className={`bubble ${turno.role}`}>
                {turno.text}
                {turno.tools && turno.tools.length > 0 && (
                  <div className="toolchips">
                    {turno.tools.map((llamada, posicion) => (
                      <span className="toolchip" key={posicion}>
                        {llamada.name}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {ocupado && <div className="bubble bot">consultando el reporte…</div>}
            <div ref={finRef} />
          </div>

          <div className="composer">
            <input
              value={borrador}
              onChange={(event) => setBorrador(event.target.value)}
              onKeyDown={(event) => event.key === 'Enter' && void enviar(borrador)}
              placeholder="Pregunta sobre este dataset…"
              disabled={ocupado}
            />
            <button onClick={() => void enviar(borrador)} disabled={ocupado || !borrador.trim()}>
              Enviar
            </button>
          </div>

          <div className="suggestions">
            {SUGERENCIAS.map((sugerencia) => (
              <button key={sugerencia} onClick={() => void enviar(sugerencia)} disabled={ocupado}>
                {sugerencia}
              </button>
            ))}
          </div>
        </Card>

        <div className="grid">
          <Card
            title="Herramientas previstas"
            hint="Todas de lectura. El agente no podrá publicar versiones, borrar imágenes ni cambiar umbrales."
          >
            {HERRAMIENTAS.map(([nombre, descripcion]) => (
              <div className="row" key={nombre}>
                <div className="row-main" style={{ alignItems: 'flex-start' }}>
                  <div>
                    <div className="mono" style={{ fontSize: 12 }}>
                      {nombre}
                    </div>
                    <div style={{ fontSize: 11.5, color: 'var(--muted)' }}>{descripcion}</div>
                  </div>
                </div>
              </div>
            ))}
          </Card>

          <Card title="Por qué solo lectura">
            <p style={{ margin: 0, color: 'var(--ink-2)' }}>
              Un asistente que explica por qué falló la compuerta es útil. Uno que puede
              desactivarla destruye la razón de existir del proyecto. La restricción es diseño, no
              timidez: si alguien le pide bajar un umbral, la respuesta correcta es explicar que
              eso se hace editando <span className="mono">quality.yaml</span>, donde queda
              registrado en Git.
            </p>
          </Card>
        </div>
      </div>
    </>
  );
}
