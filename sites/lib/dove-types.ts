export type Evidence = { documentId: string; page: number; quote: string };
export type Requirement = { id: string; title: string; category: string; status: "missing"|"received"|"conflict"|"satisfied"|"waived"; evidence: Evidence[]; reason: string; reviewedBy?: string };
export type DocumentRecord = { id: string; name: string; mime: string; size: number; pages: string[]; approved: boolean };
export type Packet = { id: string; pdfId?: string; number: string; digest: string; total: string; currency: string; recipient: string; revision: number; approved: boolean; approvedBy?: string; created: string; documents: string[]; summary: string; delivery: string; providerId?: string };
export type RequestRecord = { id: string; requirements: string[]; body: string; recipient: string; status: string; providerId?: string; created: string };
export type Work = { id: string; title: string; customer: string; contactName: string; email: string; authorized: boolean; currency: string; description: string; status: string; revision: number; documents: DocumentRecord[]; requirements: Requirement[]; packages: Packet[]; requests: RequestRecord[]; activity: {at:string; by:string; text:string}[]; created: string; calls: number; paused: boolean };
export type Workspace = {id:string; name:string; billing:string; paused:number};
