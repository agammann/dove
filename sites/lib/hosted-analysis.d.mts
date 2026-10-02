import type { Work, Requirement } from './dove-types';
export const HOSTED_CHARACTER_LIMIT: number;
export function analyzeDocumentsHosted(work: Work, options: { apiKey: string; model?: string; signal?: AbortSignal; onProgress?: (text: string) => void }): Promise<Omit<Requirement, 'id'>[]>;
export function visitorGenerator(apiKey: string, model?: string): AnalysisGenerator;
