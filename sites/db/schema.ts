import { integer, sqliteTable, text, index } from "drizzle-orm/sqlite-core";
export const accessRequests = sqliteTable("access_requests", {
 id:text("id").primaryKey(), name:text("name").notNull(), email:text("email").notNull(), business:text("business").notNull(), problem:text("problem").notNull(), consent:integer("consent").notNull(), createdAt:integer("created_at").notNull(), sourceHash:text("source_hash").notNull()
}, table => [index("requests_created_idx").on(table.createdAt),index("requests_source_created_idx").on(table.sourceHash,table.createdAt)]);

export const doveWorkspaces=sqliteTable("dove_workspaces",{id:text("id").primaryKey(),name:text("name").notNull(),billing:text("billing").notNull().default(""),paused:integer("paused").notNull().default(1),bytes:integer("bytes").notNull().default(0),fileCount:integer("file_count").notNull().default(0)});
export const doveMembers=sqliteTable("dove_members",{userId:text("user_id").primaryKey(),orgId:text("org_id").notNull().references(()=>doveWorkspaces.id),email:text("email").notNull()},t=>[index("dove_members_org").on(t.orgId)]);
export const doveInvitations=sqliteTable("dove_invitations",{hash:text("hash").primaryKey(),orgId:text("org_id").notNull().references(()=>doveWorkspaces.id),email:text("email"),expires:integer("expires").notNull(),usedBy:text("used_by")});
export const doveWork=sqliteTable("dove_work",{id:text("id").primaryKey(),orgId:text("org_id").notNull().references(()=>doveWorkspaces.id),data:text("data").notNull(),version:integer("version").notNull().default(0),updated:integer("updated").notNull(),deleted:integer("deleted").notNull().default(0)},t=>[index("dove_work_org_updated").on(t.orgId,t.deleted,t.updated)]);
export const doveFiles=sqliteTable("dove_files",{id:text("id").primaryKey(),orgId:text("org_id").notNull().references(()=>doveWorkspaces.id),workId:text("work_id").notNull(),storageKey:text("storage_key").notNull(),name:text("name").notNull(),mime:text("mime").notNull(),size:integer("size").notNull()},t=>[index("dove_files_work").on(t.orgId,t.workId)]);
export const doveLimits=sqliteTable("dove_limits",{id:text("id").primaryKey(),count:integer("count").notNull()});
