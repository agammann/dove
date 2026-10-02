import { visitorAnalysis } from '../../../../lib/server/visitor-analysis.mjs';

export const dynamic = 'force-dynamic';
export function POST(request: Request) { return visitorAnalysis(request); }
