export const dynamic="force-dynamic";
export function GET(){return Response.json({error:"Dove now stores work in your browser. Open /workspace; no account is required."},{status:410,headers:{"Cache-Control":"no-store"}})}
export const POST=GET;export const PUT=GET;export const DELETE=GET;
