CREATE DATABASE flask_project_db;

CREATE USER 'flask_user'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON flask_project_db.* TO 'flask_user'@'localhost';
FLUSH PRIVILEGES;


INSERT INTO rules (rule_string) VALUES ('age > 30 AND department = "Sales"');



USE flask_project_db;

SELECT * FROM rules;


