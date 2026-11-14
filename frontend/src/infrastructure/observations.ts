/** Observation retrieval contract; no fixture implementation in production. */
export interface ObservationRepository {
  list(): Promise<unknown>;
}
