import type { Work, Requirement } from './dove-types';
export function verifyProposals(work:Work, proposals:unknown):Omit<Requirement,'id'>[];
export function analyzeDocumentsBrowser(work:Work, options?:{signal?:AbortSignal;onProgress?:(text:string)=>void}):Promise<Omit<Requirement,'id'>[]>;
