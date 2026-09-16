-- Docker init script: creates test database alongside main database
-- This runs once when the PostgreSQL container is first initialized.
CREATE DATABASE projectflow_test
    WITH OWNER = projectflow
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TEMPLATE = template0;
