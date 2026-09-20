CREATE TABLE `dove_files` (
	`id` text PRIMARY KEY NOT NULL,
	`org_id` text NOT NULL,
	`work_id` text NOT NULL,
	`storage_key` text NOT NULL,
	`name` text NOT NULL,
	`mime` text NOT NULL,
	`size` integer NOT NULL,
	FOREIGN KEY (`org_id`) REFERENCES `dove_workspaces`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX `dove_files_work` ON `dove_files` (`org_id`,`work_id`);--> statement-breakpoint
CREATE TABLE `dove_invitations` (
	`hash` text PRIMARY KEY NOT NULL,
	`org_id` text NOT NULL,
	`email` text,
	`expires` integer NOT NULL,
	`used_by` text,
	FOREIGN KEY (`org_id`) REFERENCES `dove_workspaces`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `dove_limits` (
	`id` text PRIMARY KEY NOT NULL,
	`count` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `dove_members` (
	`user_id` text PRIMARY KEY NOT NULL,
	`org_id` text NOT NULL,
	`email` text NOT NULL,
	FOREIGN KEY (`org_id`) REFERENCES `dove_workspaces`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX `dove_members_org` ON `dove_members` (`org_id`);--> statement-breakpoint
CREATE TABLE `dove_work` (
	`id` text PRIMARY KEY NOT NULL,
	`org_id` text NOT NULL,
	`data` text NOT NULL,
	`version` integer DEFAULT 0 NOT NULL,
	`updated` integer NOT NULL,
	`deleted` integer DEFAULT 0 NOT NULL,
	FOREIGN KEY (`org_id`) REFERENCES `dove_workspaces`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX `dove_work_org_updated` ON `dove_work` (`org_id`,`deleted`,`updated`);--> statement-breakpoint
CREATE TABLE `dove_workspaces` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`billing` text DEFAULT '' NOT NULL,
	`paused` integer DEFAULT 1 NOT NULL,
	`bytes` integer DEFAULT 0 NOT NULL,
	`file_count` integer DEFAULT 0 NOT NULL
);
