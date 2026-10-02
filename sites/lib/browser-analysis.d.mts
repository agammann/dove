import type { Work, Requirement } from './dove-types';
export function verifyProposals(work:Work, proposals:unknown):Omit<Requirement,'id'>[];
export type AnalysisGenerator = (messages:{role:string;content:string}[], options:{schema:unknown;maxTokens:number;signal?:AbortSignal})=>Promise<{value:{requirements:Omit<Requirement,'id'>[]}}>;
export function analyzeDocumentsBrowser(work:Work, options?:{signal?:AbortSignal;onProgress?:(text:string)=>void;runGeneration?:AnalysisGenerator;location?:string}):Promise<Omit<Requirement,'id'>[]>;
