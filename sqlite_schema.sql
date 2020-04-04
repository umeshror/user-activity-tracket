-- TABLE
CREATE TABLE ActivityLog
(
	id TEXT(36) not null
		primary key,
	action VARCHAR(255),
	user_id VARCHAR(255)
		references user,
	attributes TEXT,
	created_at DATETIME,
	updated_at DATETIME
);
CREATE TABLE user
(
	id TEXT(36) not null
		primary key,
	email VARCHAR(120),
	name VARCHAR(255),
	created_at DATETIME,
	updated_at DATETIME
);
 
-- INDEX
CREATE INDEX ix_user_email
	on user (email);

 
