CREATE TABLE `access_requests` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`email` text NOT NULL,
	`business` text NOT NULL,
	`problem` text NOT NULL,
	`consent` integer NOT NULL,
	`created_at` integer NOT NULL,
	`source_hash` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `requests_created_idx` ON `access_requests` (`created_at`);--> statement-breakpoint
CREATE INDEX `requests_source_created_idx` ON `access_requests` (`source_hash`,`created_at`);