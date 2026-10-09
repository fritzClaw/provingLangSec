CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, secret TEXT NOT NULL);
INSERT INTO users (name, email, secret) VALUES
  ('alice',   'alice@example.org',   'S3CR3T-ALICE-7f3a'),
  ('bob',     'bob@example.org',     'S3CR3T-BOB-91c2'),
  ('o''brien', 'obrien@example.org', 'S3CR3T-OBRIEN-5d0e'),
  ('zoë 😀',  'zoe@example.org',     'S3CR3T-ZOE-aa14');
