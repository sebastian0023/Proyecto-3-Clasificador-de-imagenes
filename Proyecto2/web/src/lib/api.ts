/**
 * Cliente de la API.
 *
 * Los tipos espejan los contratos congelados del Frente 2 (`quality.json`,
 * `splits.json`, `versions.json`) mas el de exploracion. Cada artefacto llega
 * envuelto en un sobre que dice quien lo produjo.
 */

export interface Envelope<T> {
  source: 'pipeline';
  produced_by: string;
  data: T;
}

// --- quality.json -----------------------------------------------------------
export type CheckStatus = 'pass' | 'fail' | 'skipped';
export type Severity = 'error' | 'warning';

/** Un par de imágenes que el pHash considera la misma foto. */
export interface DuplicatePair {
  kept: number;
  duplicate: number;
  distance: number;
  similarity: number;
}

/**
 * Detalle del check `duplicates`: los pares y a qué clases afectan.
 *
 * `images_by_class` cuenta imágenes SOBRANTES que contienen al menos una caja
 * de esa clase, ordenadas de mayor a menor. Una copia con cajas de dos clases
 * suma en las dos, así que la suma puede superar el total de sobrantes.
 */
export interface DuplicatesDetail {
  max_distance: number;
  pairs: DuplicatePair[];
  groups: number;
  images_by_class: Record<string, number>;
  boxes_by_class: Record<string, number>;
  images_without_class: number;
}

export interface CheckResult {
  name: string;
  status: CheckStatus;
  severity: Severity;
  observed: number;
  threshold: number;
  message: string;
  offenders: number[];
  /** Solo lo lleva el check `duplicates`; `null` en todos los demás. */
  duplicates?: DuplicatesDetail | null;
}

export interface QualityReport {
  schema_version: 1;
  generated_at: string;
  dataset_fingerprint: string;
  config_version: number;
  status: 'pass' | 'fail';
  exit_code: 0 | 1;
  totals: { images: number; annotations: number; categories: number };
  checks: CheckResult[];
}

// --- splits.json ------------------------------------------------------------
export type SplitName = 'train' | 'val' | 'test';

export interface SplitsManifest {
  schema_version: 1;
  generated_at: string;
  seed: number;
  ratios: Record<SplitName, number>;
  counts: Record<SplitName, number>;
  stratified_by: string;
  assignments: { image_id: number; split: SplitName }[];
}

// --- versions.json ----------------------------------------------------------
export interface DatasetVersion {
  schema_version: 1;
  version: string;
  created_at: string;
  dataset_fingerprint: string;
  quality_report_fingerprint: string;
  splits_fingerprint: string;
  storage_uri: string;
  quality_status: 'pass' | 'fail';
  counts: { images: number; annotations: number; categories: number };
  notes: string | null;
}

export interface VersionsManifest {
  schema_version: 1;
  versions: DatasetVersion[];
}

// --- exploration.json -------------------------------------------------------
export interface ExplorationManifest {
  schema_version: 1;
  generated_at: string;
  method: 'pca' | 'tsne';
  seed: number;
  dimensions: 2;
  variance_explained: number;
  method_detail: string;
  points: { image_id: number; x: number; y: number; category_id: number | null }[];
}

// --- descriptiva ------------------------------------------------------------
export interface DatasetStats {
  totals: { images: number; annotations: number; categories: number };
  images_per_class: Record<string, number>;
  boxes_per_class: Record<string, number>;
  annotations_per_image: number;
  images_without_annotations: number;
  mean_box_area_ratio: number;
  median_box_area_ratio: number;
  p90_box_area_ratio: number;
}

export interface AnalysisArtifact {
  stats: DatasetStats;
  checks: CheckResult[];
}

export interface Config {
  app_env: string;
  database: { host: string; port: number; name: string; user: string };
  object_storage: { endpoint_url: string; buckets: string[] };
}

// --- quality.yaml -----------------------------------------------------------
/**
 * Un check de la política: `enabled`, `severity` y los umbrales propios de ese
 * analizador. El tipo se deja abierto a propósito — los umbrales cambian de un
 * check a otro y quien decide qué es válido es `QualityConfig` en el servidor,
 * que responde 422 nombrando el campo. Duplicar aquí esas reglas solo crearía
 * una segunda fuente de verdad que se desincroniza.
 */
export type PolicyValue = boolean | number | string;
export type CheckPolicy = Record<string, PolicyValue>;

export interface SplitsPolicy {
  seed: number;
  ratios: Record<SplitName, number>;
  tolerance: number;
  group_near_duplicates: boolean;
}

export interface QualityPolicy {
  version: number;
  min_images_per_class: CheckPolicy;
  small_objects: CheckPolicy;
  class_imbalance: CheckPolicy;
  duplicates: CheckPolicy;
  degenerate_boxes: CheckPolicy;
  spatial_bias: CheckPolicy;
  splits: SplitsPolicy;
}

export interface PolicyEnvelope {
  source: 'quality.yaml';
  path: string;
  data: QualityPolicy;
  warnings: string[];
}

export interface PolicySaved {
  /** Rutas que cambiaron, como `duplicates.max_ratio`. */
  changed: string[];
  data: QualityPolicy;
  warnings: string[];
  stale_reports: boolean;
  next_steps: string[];
}

export interface DedupePlan {
  remove_count: number;
  annotations_removed: number;
  total_images: number;
  kept: number;
  sample: string[];
}

export interface DedupeResult {
  removed_images: number;
  removed_annotations?: number;
  remaining_images?: number;
  quarantine_dir?: string;
  stale_reports: boolean;
  next_steps?: string[];
  undo?: string;
  message?: string;
}

export interface RefreshResult {
  status: 'pass' | 'fail';
  exit_code: 0 | 1;
  dataset_fingerprint: string;
  totals: { images: number; annotations: number; categories: number };
  blocking: string[];
  warnings: string[];
  duration_seconds: number;
  checks: { name: string; status: CheckStatus; severity: Severity }[];
  next_steps: string[];
}

export interface CopilotAnswer {
  request_id: string;
  answer: string;
  tool_calls: CopilotToolCall[];
  citations: CopilotCitation[];
}

export interface CopilotCitation {
  artifact: string;
  artifact_revision: string;
  generated_at: string | null;
  dataset_fingerprint: string | null;
}

export interface CopilotToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  status: 'success' | 'failed' | 'rejected';
  duration_ms: number;
  citation: CopilotCitation | null;
  error: string | null;
}

/** Error que conserva el mensaje de la API, no un `fetch failed` generico. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // La respuesta no era JSON: nos quedamos con el codigo de estado.
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export const api = {
  status: () =>
    request<Record<string, { available: boolean; produced_by: string }>>('/api/status'),
  quality: () => request<Envelope<QualityReport>>('/api/quality'),
  splits: () => request<Envelope<SplitsManifest>>('/api/splits'),
  versions: () => request<Envelope<VersionsManifest>>('/api/versions'),
  exploration: () => request<Envelope<ExplorationManifest>>('/api/exploration'),
  stats: () => request<Envelope<AnalysisArtifact>>('/api/stats'),
  config: () => request<Config>('/api/config'),
  policy: () => request<PolicyEnvelope>('/api/policy'),
  savePolicy: (data: QualityPolicy) =>
    request<PolicySaved>('/api/policy', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  duplicatesPlan: () => request<DedupePlan>('/api/duplicates/plan'),
  duplicatesRemove: () =>
    request<DedupeResult>('/api/duplicates/remove', { method: 'POST' }),
  pipelineRefresh: () => request<RefreshResult>('/api/pipeline/refresh', { method: 'POST' }),
  copilot: (question: string) =>
    request<CopilotAnswer>('/api/copilot/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    }),
};

/**
 * Formatea una metrica segun lo que representa.
 *
 * La direccion de la comparacion no viaja en `CheckResult` — el contrato esta
 * congelado — asi que se deriva del nombre del check. Es el unico punto donde
 * el frontend sabe algo que el contrato no dice.
 */
export function formatMetric(value: number, name: string): string {
  if (name === 'min_images_per_class') return String(Math.round(value));
  if (name === 'class_imbalance') return `${value.toFixed(1)}x`;
  if (name === 'degenerate_boxes' && value >= 1) return String(Math.round(value));
  return `${(value * 100).toFixed(1)}%`;
}

export function comparison(name: string): '>=' | '<=' {
  return name === 'min_images_per_class' ? '>=' : '<=';
}
