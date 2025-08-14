from typing import Mapping, Any, Sequence, reveal_type
import json
import sqlglot

SQL_FACTORY_DEMONSTRATION_INFO_DICT: Mapping[
    str, Mapping[str, str | Sequence[Mapping[str, Any]]]
] = {
    "select": {
        "demonstration": [
            {
                "sql": "SELECT id, name, email FROM customers;",
                "table_name": "customers",
                "column_info_list": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "email", "type": "TEXT"},
                ],
            },
            {
                "sql": "SELECT * FROM vehicles WHERE price = 30000;",
                "table_name": "vehicles",
                "column_info_list": [
                    {"name": "id", "type": "INT"},
                    {"name": "make", "type": "TEXT"},
                    {"name": "model", "type": "TEXT"},
                    {"name": "year", "type": "INT"},
                    {"name": "price", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT course_id, name, instructor FROM lessons WHERE instructor = 'Dr. Brown';",
                "table_name": "lessons",
                "column_info_list": [
                    {"name": "course_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "instructor", "type": "TEXT"},
                ],
            },
        ],
        "explanation": "SELECT statements.",
    },
    "insert": {
        "demonstration": [
            {
                "sql": "INSERT INTO workers (id, name, salary) VALUES (2, 'Mary James', 7000);",
                "table_name": "workers",
                "column_info_list": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "salary", "type": "INT"},
                ],
            },
            {
                "sql": "INSERT INTO staff (id, name, role) VALUES (2, 'Bob Green', 'Manager');",
                "table_name": "staff",
                "column_info_list": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "role", "type": "TEXT"},
                ],
            },
            {
                "sql": "INSERT INTO cars (vehicle_id, make, price) VALUES (2, 'Audi A6', 25000);",
                "table_name": "cars",
                "column_info_list": [
                    {"name": "vehicle_id", "type": "INT"},
                    {"name": "make", "type": "TEXT"},
                    {"name": "price", "type": "INT"},
                ],
            },
        ],
        "explanation": "INSERT statements.",
    },
    "delete": {
        "demonstration": [
            {
                "sql": "DELETE FROM staff WHERE id = 1;",
                "table_name": "staff",
                "column_info_list": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "role", "type": "TEXT"},
                ],
            },
            {
                "sql": "DELETE FROM workers WHERE department = 'Sales';",
                "table_name": "workers",
                "column_info_list": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "department", "type": "TEXT"},
                    {"name": "salary", "type": "INT"},
                ],
            },
            {
                "sql": "DELETE FROM buyers WHERE customer_id = 2;",
                "table_name": "buyers",
                "column_info_list": [
                    {"name": "customer_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "email", "type": "TEXT"},
                ],
            },
        ],
        "explanation": "DELETE statements.",
    },
    "update": {
        "demonstration": [
            {
                "sql": "UPDATE gadgets SET price = 250 WHERE product_id = 102;",
                "table_name": "gadgets",
                "column_info_list": [
                    {"name": "product_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "price", "type": "INT"},
                ],
            },
            {
                "sql": "UPDATE students SET age = 21 WHERE student_id = 1;",
                "table_name": "students",
                "column_info_list": [
                    {"name": "student_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "age", "type": "INT"},
                    {"name": "grade", "type": "TEXT"},
                ],
            },
            {
                "sql": "UPDATE users SET email = 'new_email@example.com' WHERE role = 'admin';",
                "table_name": "users",
                "column_info_list": [
                    {"name": "user_id", "type": "INT"},
                    {"name": "email", "type": "TEXT"},
                    {"name": "role", "type": "TEXT"},
                ],
            },
        ],
        "explanation": "UPDATE statements.",
    },
    "where_single_condition": {
        "demonstration": [
            {
                "sql": "SELECT * FROM students WHERE age = 20;",
                "table_name": "students",
                "column_info_list": [
                    {"name": "student_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "age", "type": "INT"},
                    {"name": "grade", "type": "TEXT"},
                ],
            },
            {
                "sql": "UPDATE cars SET price = 27000 WHERE vehicle_id = 2;",
                "table_name": "cars",
                "column_info_list": [
                    {"name": "vehicle_id", "type": "INT"},
                    {"name": "make", "type": "TEXT"},
                    {"name": "price", "type": "INT"},
                ],
            },
            {
                "sql": "DELETE FROM staff WHERE id = 1;",
                "table_name": "staff",
                "column_info_list": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "role", "type": "TEXT"},
                ],
            },
        ],
        "explanation": "WHERE clause with a single condition (e.g., WHERE id = 5).",
    },
    "where_multiple_conditions": {
        "demonstration": [
            {
                "sql": "SELECT id, name, salary FROM workers WHERE salary > 5000 AND department = 'HR';",
                "table_name": "workers",
                "column_info_list": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "department", "type": "TEXT"},
                    {"name": "salary", "type": "INT"},
                ],
            },
            {
                "sql": "DELETE FROM students WHERE age = 20 AND grade = 'A';",
                "table_name": "students",
                "column_info_list": [
                    {"name": "student_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "age", "type": "INT"},
                    {"name": "grade", "type": "TEXT"},
                ],
            },
            {
                "sql": "UPDATE workers SET salary = 7500 WHERE salary = 5000 and department = 'HR';",
                "table_name": "workers",
                "column_info_list": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "department", "type": "TEXT"},
                    {"name": "salary", "type": "INT"},
                ],
            },
        ],
        "explanation": "WHERE clause with multiple conditions combined using AND/OR.",
    },
    "order_by_single_column": {
        "demonstration": [
            {
                "sql": "SELECT vehicle_id, make, price FROM cars ORDER BY price ASC;",
                "table_name": "cars",
                "column_info_list": [
                    {"name": "vehicle_id", "type": "INT"},
                    {"name": "make", "type": "TEXT"},
                    {"name": "price", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT id, name, salary FROM workers WHERE salary > 9000 ORDER BY salary DESC;",
                "table_name": "workers",
                "column_info_list": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "department", "type": "TEXT"},
                    {"name": "salary", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT customer_id, name, email FROM buyers WHERE name = 'Sarah Lee' ORDER BY email DESC;",
                "table_name": "buyers",
                "column_info_list": [
                    {"name": "customer_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "email", "type": "TEXT"},
                ],
            },
        ],
        "explanation": "ORDER BY clause sorting based on a single column.",
    },
    "limit_only": {
        "demonstration": [
            {
                "sql": "SELECT * FROM workers LIMIT 5;",
                "table_name": "workers",
                "column_info_list": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "salary", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT id, name, salary FROM workers WHERE salary > 5000 ORDER BY salary DESC LIMIT 5;",
                "table_name": "workers",
                "column_info_list": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "department", "type": "TEXT"},
                    {"name": "salary", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT id, name, location FROM distributors WHERE id = 6 LIMIT 2;",
                "table_name": "distributors",
                "column_info_list": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "location", "type": "TEXT"},
                ],
            },
        ],
        "explanation": "LIMIT clause limiting the number of returned rows, without the OFFSET clause.",
    },
    "column_alias": {
        "demonstration": [
            {
                "sql": "SELECT id AS worker_id, name AS worker_name FROM workers;",
                "table_name": "workers",
                "column_info_list": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "salary", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT customer_id AS buyer_id, name AS buyer_name FROM buyers WHERE name = 'Mark Jordan';",
                "table_name": "buyers",
                "column_info_list": [
                    {"name": "customer_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "email", "type": "TEXT"},
                ],
            },
            {
                "sql": "SELECT id AS staff_id, name AS staff_name FROM staff WHERE department = 'Logistics';",
                "table_name": "staff",
                "column_info_list": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "role", "type": "TEXT"},
                    {"name": "department", "type": "TEXT"},
                ],
            },
        ],
        "explanation": "Aliasing columns in SELECT (e.g., SELECT name AS employee_name).",
    },
    "table_alias": {
        "demonstration": [
            {
                "sql": "SELECT c.vehicle_id, c.make, c.price FROM cars as c;",
                "table_name": "cars",
                "column_info_list": [
                    {"name": "vehicle_id", "type": "INT"},
                    {"name": "make", "type": "TEXT"},
                    {"name": "price", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT e.employee_id, e.name, e.salary FROM employees AS e WHERE e.salary > 50000;",
                "table_name": "employees",
                "column_info_list": [
                    {"name": "employee_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "department", "type": "TEXT"},
                    {"name": "salary", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT b.customer_id AS buyer_id, b.name AS buyer_name FROM buyers as b WHERE b.name = 'Mark Jordan';",
                "table_name": "buyers",
                "column_info_list": [
                    {"name": "customer_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "email", "type": "TEXT"},
                ],
            },
        ],
        "explanation": "Aliasing tables in FROM (e.g., FROM employees AS e).",
    },
    "where_nested_conditions": {
        "demonstration": [
            {
                "sql": "SELECT region, sales FROM sales_data WHERE (year = 2023 AND quarter = 3) OR region = 'North';",
                "table_name": "sales_data",
                "column_info_list": [
                    {"name": "region", "type": "TEXT"},
                    {"name": "year", "type": "INT"},
                    {"name": "quarter", "type": "INT"},
                    {"name": "sales", "type": "INT"},
                ],
            },
            {
                "sql": "DELETE FROM orders WHERE (order_date < '2022-01-01' AND customer_id != 10) OR status IN ('pending', 'shipped');",
                "table_name": "orders",
                "column_info_list": [
                    {"name": "order_id", "type": "INT"},
                    {"name": "order_date", "type": "DATE"},
                    {"name": "customer_id", "type": "INT"},
                    {"name": "status", "type": "TEXT"},
                ],
            },
            {
                "sql": "UPDATE products SET price = 99.99 WHERE (category = 'Electronics' AND price < 100) OR (category = 'Furniture' AND stock < 50);",
                "table_name": "products",
                "column_info_list": [
                    {"name": "product_id", "type": "INT"},
                    {"name": "product_name", "type": "TEXT"},
                    {"name": "category", "type": "TEXT"},
                    {"name": "price", "type": "INT"},
                    {"name": "stock", "type": "INT"},
                ],
            },
        ],
        "explanation": "WHERE clause with nested logical conditions (e.g., WHERE (A AND B) OR C).",
    },
    "group_by_single_column": {
        "demonstration": [
            {
                "sql": "SELECT region, AVG(sales) FROM sales_data GROUP BY region;",
                "table_name": "sales_data",
                "column_info_list": [
                    {"name": "region", "type": "TEXT"},
                    {"name": "sales", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT customer_id, COUNT(order_id) AS num_orders FROM orders GROUP BY customer_id;",
                "table_name": "orders",
                "column_info_list": [
                    {"name": "customer_id", "type": "INT"},
                    {"name": "order_id", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT product_name, SUM(quantity) FROM orders WHERE order_date < '2023-12-31' GROUP BY product_name;",
                "table_name": "orders",
                "column_info_list": [
                    {"name": "product_name", "type": "TEXT"},
                    {"name": "quantity", "type": "INT"},
                    {"name": "order_date", "type": "DATE"},
                ],
            },
        ],
        "explanation": "GROUP BY clause grouping based on a single column.",
    },
    "group_by_multiple_columns": {
        "demonstration": [
            {
                "sql": "SELECT department, job_title, AVG(salary) AS average_salary FROM employees GROUP BY department, job_title;",
                "table_name": "employees",
                "column_info_list": [
                    {"name": "department", "type": "TEXT"},
                    {"name": "job_title", "type": "TEXT"},
                    {"name": "salary", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT department, job_title, COUNT(employee_id) AS num_employees FROM employees GROUP BY department, job_title HAVING COUNT(employee_id) > 5;",
                "table_name": "employees",
                "column_info_list": [
                    {"name": "department", "type": "TEXT"},
                    {"name": "job_title", "type": "TEXT"},
                    {"name": "employee_id", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT order_id, customer_id, SUM(total_amount) AS total_spent FROM orders GROUP BY order_id, customer_id;",
                "table_name": "orders",
                "column_info_list": [
                    {"name": "order_id", "type": "INT"},
                    {"name": "customer_id", "type": "INT"},
                    {"name": "total_amount", "type": "INT"},
                ],
            },
        ],
        "explanation": "GROUP BY clause grouping based on multiple columns.",
    },
    "having_single_condition_with_aggregate": {
        "demonstration": [
            {
                "sql": "SELECT product_region, SUM(quantity) AS total_sales FROM sales GROUP BY product_region HAVING SUM(quantity) > 100;",
                "table_name": "sales",
                "column_info_list": [
                    {"name": "product_region", "type": "TEXT"},
                    {"name": "quantity", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT customer_region, AVG(order_amount) AS average_order_amount FROM orders GROUP BY customer_region HAVING AVG(order_amount) > 200;",
                "table_name": "orders",
                "column_info_list": [
                    {"name": "customer_region", "type": "TEXT"},
                    {"name": "order_amount", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT department, job_title, AVG(salary) AS average_salary FROM employees GROUP BY department, job_title HAVING AVG(salary) > 100;",
                "table_name": "employees",
                "column_info_list": [
                    {"name": "department", "type": "TEXT"},
                    {"name": "job_title", "type": "TEXT"},
                    {"name": "salary", "type": "INT"},
                ],
            },
        ],
        "explanation": "HAVING clause with a single condition involving a single aggregate function.",
    },
    "having_multiple_conditions_with_aggregate": {
        "demonstration": [
            {
                "sql": "SELECT product_region, SUM(quantity) AS total_sales FROM sales GROUP BY product_region HAVING SUM(quantity) > 100 AND SUM(quantity) < 500;",
                "table_name": "sales",
                "column_info_list": [
                    {"name": "product_region", "type": "TEXT"},
                    {"name": "quantity", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT department, AVG(spending) AS average_spending FROM employees GROUP BY department HAVING AVG(spending) > 3000 AND AVG(spending) < 5000;",
                "table_name": "employees",
                "column_info_list": [
                    {"name": "department", "type": "TEXT"},
                    {"name": "spending", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT department, COUNT(employee_id) AS num_employees FROM employees GROUP BY department HAVING COUNT(employee_id) > 5 OR COUNT(employee_id) < 10;",
                "table_name": "employees",
                "column_info_list": [
                    {"name": "department", "type": "TEXT"},
                    {"name": "employee_id", "type": "INT"},
                ],
            },
        ],
        "explanation": "HAVING clause with multiple conditions involving aggregate functions.",
    },
    "having_aggregate_calculation": {
        "demonstration": [
            {
                "sql": "SELECT department, COUNT(*) AS num_employees FROM employees GROUP BY department HAVING MAX(salary) - MIN(salary) > 15000;",
                "table_name": "employees",
                "column_info_list": [
                    {"name": "department", "type": "TEXT"},
                    {"name": "employee_id", "type": "INT"},
                    {"name": "salary", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT lesson_name, COUNT(*) AS num_students FROM students GROUP BY lesson_name HAVING MAX(score) - MIN(score) > 20;",
                "table_name": "students",
                "column_info_list": [
                    {"name": "lesson_name", "type": "TEXT"},
                    {"name": "student_id", "type": "INT"},
                    {"name": "score", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT employee_name, MAX(salary) AS max_salary FROM employees GROUP BY employee_name HAVING MAX(salary) - MIN(salary) > 15000;",
                "table_name": "employees",
                "column_info_list": [
                    {"name": "employee_name", "type": "TEXT"},
                    {"name": "salary", "type": "INT"},
                ],
            },
        ],
        "explanation": "HAVING clause involves aggregated values (e.g., COUNT(*), MAX(), MIN()) and calculation (e.g., MAX(salary) - MIN(salary)).",
    },
    "order_by_multiple_columns_same_direction": {
        "demonstration": [
            {
                "sql": "SELECT * FROM students ORDER BY grade DESC, year_of_study DESC;",
                "table_name": "students",
                "column_info_list": [
                    {"name": "student_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "grade", "type": "TEXT"},
                    {"name": "year_of_study", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT * FROM employees ORDER BY department ASC, hire_date ASC;",
                "table_name": "employees",
                "column_info_list": [
                    {"name": "employee_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "department", "type": "TEXT"},
                    {"name": "hire_date", "type": "DATE"},
                ],
            },
            {
                "sql": "SELECT course, MAX(grade), COUNT(id) FROM students GROUP BY course HAVING COUNT(id) > 1 ORDER BY MAX(grade) DESC, course DESC;",
                "table_name": "students",
                "column_info_list": [
                    {"name": "course", "type": "TEXT"},
                    {"name": "grade", "type": "TEXT"},
                    {"name": "id", "type": "INT"},
                ],
            },
        ],
        "explanation": "ORDER BY clause sorting based on multiple columns. The sort direction is the same for all columns.",
    },
    "order_by_multiple_columns_different_directions": {
        "demonstration": [
            {
                "sql": "SELECT * FROM students ORDER BY grade DESC, age + year_of_study ASC;",
                "table_name": "students",
                "column_info_list": [
                    {"name": "student_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "grade", "type": "TEXT"},
                    {"name": "age", "type": "INT"},
                    {"name": "year_of_study", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT * FROM employees ORDER BY department ASC, hire_date DESC;",
                "table_name": "employees",
                "column_info_list": [
                    {"name": "employee_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "department", "type": "TEXT"},
                    {"name": "hire_date", "type": "DATE"},
                ],
            },
            {
                "sql": "SELECT * FROM students WHERE age = 20 ORDER BY name DESC, score ASC;",
                "table_name": "students",
                "column_info_list": [
                    {"name": "student_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "age", "type": "INT"},
                    {"name": "score", "type": "INT"},
                ],
            },
        ],
        "explanation": "ORDER BY clause with mixed sort directions.",
    },
    "limit_and_offset": {
        "demonstration": [
            {
                "sql": "SELECT * FROM employees LIMIT 2 OFFSET 3;",
                "table_name": "employees",
                "column_info_list": [
                    {"name": "employee_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "department", "type": "TEXT"},
                    {"name": "salary", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT order_id, customer_id, total_amount FROM orders WHERE total_amount > 1800 LIMIT 5 OFFSET 3;",
                "table_name": "orders",
                "column_info_list": [
                    {"name": "order_id", "type": "INT"},
                    {"name": "customer_id", "type": "INT"},
                    {"name": "total_amount", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT * FROM students ORDER BY enrollment_date DESC LIMIT 3 OFFSET 2;",
                "table_name": "students",
                "column_info_list": [
                    {"name": "student_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "enrollment_date", "type": "DATE"},
                ],
            },
        ],
        "explanation": "Usage of both LIMIT and OFFSET together.",
    },
    "subquery_single": {
        "demonstration": [
            {
                "sql": "SELECT name, age FROM students WHERE age > (SELECT AVG(age) FROM students);",
                "table_name": "students",
                "column_info_list": [
                    {"name": "student_id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "age", "type": "INT"},
                    {"name": "grade", "type": "TEXT"},
                ],
            },
            {
                "sql": "SELECT product, price FROM products WHERE price < (SELECT price FROM products WHERE product = 'Laptop') * 1.1;",
                "table_name": "products",
                "column_info_list": [
                    {"name": "product", "type": "TEXT"},
                    {"name": "price", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT athlete_name, event, score FROM athlete_performance WHERE score > (SELECT MAX(score) FROM athlete_performance WHERE event = 'High Jump') AND event = 'Long Jump';",
                "table_name": "athlete_performance",
                "column_info_list": [
                    {"name": "athlete_name", "type": "TEXT"},
                    {"name": "event", "type": "TEXT"},
                    {"name": "score", "type": "INT"},
                ],
            },
        ],
        "explanation": "Single subquery within SELECT, WHERE, or HAVING. Notice that the subquery should relate to exactly one table.",
    },
    "subquery_multiple": {
        "demonstration": [
            {
                "sql": "SELECT name FROM employees WHERE salary > (SELECT MIN(salary) FROM employees) AND salary < (SELECT MAX(salary) FROM employees);",
                "table_name": "employees",
                "column_info_list": [
                    {"name": "name", "type": "TEXT"},
                    {"name": "salary", "type": "INT"},
                    {"name": "department", "type": "TEXT"},
                ],
            },
            {
                "sql": "SELECT employee_name, department FROM employees WHERE department = (SELECT department FROM employees WHERE employee_name = 'Alice') AND salary > (SELECT MAX(salary) FROM employees WHERE department = 'HR');",
                "table_name": "employees",
                "column_info_list": [
                    {"name": "employee_name", "type": "TEXT"},
                    {"name": "department", "type": "TEXT"},
                    {"name": "salary", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT title FROM books WHERE price > (SELECT AVG(price) FROM books) AND price < (SELECT MAX(price) FROM books);",
                "table_name": "books",
                "column_info_list": [
                    {"name": "title", "type": "TEXT"},
                    {"name": "price", "type": "INT"},
                    {"name": "category", "type": "TEXT"},
                ],
            },
        ],
        "explanation": "Multiple subqueries within the main query. Notice that the subquery should relate to exactly one table.",
    },
    "subquery_nested": {
        "demonstration": [
            {
                "sql": "SELECT name, age FROM students WHERE age > (SELECT AVG(age) FROM students WHERE grade = (SELECT MAX(grade) FROM students));",
                "table_name": "students",
                "column_info_list": [
                    {"name": "name", "type": "TEXT"},
                    {"name": "age", "type": "INT"},
                    {"name": "grade", "type": "TEXT"},
                ],
            },
            {
                "sql": "SELECT product, price FROM products WHERE price < (SELECT price FROM products WHERE product = (SELECT product FROM products WHERE price = (SELECT MAX(price) FROM products)));",
                "table_name": "products",
                "column_info_list": [
                    {"name": "product", "type": "TEXT"},
                    {"name": "price", "type": "INT"},
                ],
            },
            {
                "sql": "SELECT account_id FROM transactions GROUP BY account_id HAVING SUM(amount) > (SELECT AVG(total) FROM (SELECT SUM(amount) AS total FROM transactions GROUP BY account_id) AS sub);",
                "table_name": "transactions",
                "column_info_list": [
                    {"name": "transaction_id", "type": "INT"},
                    {"name": "account_id", "type": "INT"},
                    {"name": "amount", "type": "INT"},
                ],
            },
        ],
        "explanation": "Subqueries nested within other subqueries. Notice that the subquery should relate to exactly one table.",
    },
}

INSTRUCTION_FACTORY_DEMONSTRATION_INFO_LIST: Sequence[Mapping[str, Any]] = [
    {
        "sql": "SELECT department, AVG(salary) FROM employees WHERE (age > 30 AND age < 50) OR department = 'HR' GROUP BY department;",
        "table_name": "employees",
        "column_info_list": [
            {"name": "department", "type": "TEXT"},
            {"name": "salary", "type": "INT"},
            {"name": "age", "type": "INT"},
        ],
        "instruction": "What are the departments and their average salaries for employees aged between 30 and 50 or in the 'HR' department? Return department and corresponding average salary.",
    },
    {
        "sql": "SELECT vehicle_id, make, price FROM cars WHERE price = 25000 ORDER BY price ASC LIMIT 5;",
        "table_name": "cars",
        "column_info_list": [
            {"name": "vehicle_id", "type": "INT"},
            {"name": "make", "type": "TEXT"},
            {"name": "price", "type": "INT"},
        ],
        "instruction": "Which vehicles have a price of 25000? Return the vehicle ID, make, and price, ordered by price in ascending order, and limit the results to 5 entries.",
    },
    {
        "sql": "DELETE FROM books WHERE id = 1;",
        "table_name": "books",
        "column_info_list": [
            {"name": "id", "type": "INT"},
            {"name": "title", "type": "TEXT"},
            {"name": "author", "type": "TEXT"},
            {"name": "genre", "type": "TEXT"},
        ],
        "instruction": "Delete the book with id equal to 1 from the books table.",
    },
    {
        "sql": "SELECT id, title, publisher FROM publications WHERE publisher = 'Pearson' OR publisher = 'Wiley' ORDER BY title ASC LIMIT 3;",
        "table_name": "publications",
        "column_info_list": [
            {"name": "id", "type": "INT"},
            {"name": "title", "type": "TEXT"},
            {"name": "publisher", "type": "TEXT"},
        ],
        "instruction": "What are the IDs, titles, and publishers of publications published by either 'Pearson' or 'Wiley'? Return the results ordered by title in ascending order, limited to 3 entries.",
    },
    {
        "sql": "UPDATE staff SET salary = 5500 WHERE id = 1;",
        "table_name": "staff",
        "column_info_list": [
            {"name": "id", "type": "INT"},
            {"name": "name", "type": "TEXT"},
            {"name": "position", "type": "TEXT"},
            {"name": "salary", "type": "INT"},
        ],
        "instruction": "Update the salary of the staff member with id equal to 1 to 5500 in the staff table.",
    },
    {
        "sql": "INSERT INTO workers (id, name, salary) VALUES (2, 'Mary James', 7000);",
        "table_name": "workers",
        "column_info_list": [
            {"name": "id", "type": "INT"},
            {"name": "name", "type": "TEXT"},
            {"name": "salary", "type": "INT"},
        ],
        "instruction": "Insert a new worker with ID 2, name 'Mary James', and a salary of 7000 into the workers table.",
    },
]

ROW_FACTORY_DEMONSTRATION_INFO_DICT: Mapping[str, Mapping[str, Any]] = {
    "SELECT": {
        "instruction": "What are the categories and the count of products in each category where the price is between 100 and 500 or the stock is greater than 50? Return category and corresponding count.",
        "sql": "SELECT category, COUNT(*) FROM products WHERE (price > 100 AND price < 500) OR stock > 50 GROUP BY category;",
        "table_name": "products",
        "columns": [
            {"name": "category", "type": "TEXT"},
            {"name": "price", "type": "INT"},
            {"name": "stock", "type": "INT"},
        ],
        "rows": [
            ["Electronics", 200, 60],
            ["Clothing", 80, 40],
            ["Home", 40, 10],
            ["Electronics", 35, 60],
            ["Clothing", 120, 45],
            ["Home", 350, 65],
            ["Electronics", 220, 50],
            ["Clothing", 130, 35],
            ["Home", 400, 75],
            ["Electronics", 230, 52],
        ],
        "explanation": 'Row ["Clothing", 80, 40] and ["Home", 40, 10] do not satisfy the condition (price > 100 AND price < 500) OR stock > 50. They are not included in the aggregation calculation. The other rows which satisfy the condition are included in the aggregation calculation.',
    },
    "INSERT": {
        "instruction": "Insert a new worker with ID 6, name 'Mary James', and a salary of 7000 into the workers table.",
        "sql": "INSERT INTO workers (id, name, salary) VALUES (6, 'Mary James', 7000);",
        "table_name": "workers",
        "columns": [
            {"name": "id", "type": "INT"},
            {"name": "name", "type": "TEXT"},
            {"name": "salary", "type": "INT"},
        ],
        "rows": [
            [1, "John Doe", 5000],
            [2, "Mary James", 7000],
            [3, "Alice Smith", 6000],
            [4, "Bob Johnson", 5500],
            [5, "Charlie Brown", 6500],
        ],
        "explanation": "The table do not define a primary key, so the new row is inserted without any conflict.",
    },
    "UPDATE": {
        "instruction": "Update the salary of the worker with id equal to 2 to 7500 in the workers table.",
        "sql": "UPDATE workers SET salary = 7500 WHERE id = 2;",
        "table_name": "workers",
        "columns": [
            {"name": "id", "type": "INT"},
            {"name": "name", "type": "TEXT"},
            {"name": "department", "type": "TEXT"},
            {"name": "salary", "type": "INT"},
        ],
        "rows": [
            [1, "John Doe", "Engineering", 7000],
            [2, "Jane Smith", "Marketing", 6500],
            [3, "Alice Johnson", "Sales", 7200],
            [4, "Bob Brown", "HR", 6800],
            [5, "Charlie Davis", "Engineering", 7100],
        ],
        "explanation": "Row with the id 2 is updated, thus at least one row is affected by the update statement.",
    },
    "DELETE": {
        "instruction": "Delete the gadget with product_id 102 from the gadgets table.",
        "sql": "DELETE FROM gadgets WHERE product_id = 102;",
        "table_name": "gadgets",
        "columns": [
            {"name": "product_id", "type": "INT"},
            {"name": "name", "type": "TEXT"},
            {"name": "category", "type": "TEXT"},
        ],
        "rows": [
            [101, "Smartphone X", "Electronics"],
            [102, "Laptop Pro", "Computers"],
            [103, "Tablet Mini", "Electronics"],
            [104, "Smartwatch 2", "Wearables"],
            [105, "Headphones Plus", "Audio"],
        ],
        "explanation": "Row with the product_id 102 is deleted, thus at least one row is affected by the delete statement.",
    },
}


def validate() -> None:
    from src.factories.data.standard_v0303.instance.db_bench.sql_factory import (
        PseudoDBBench,
    )
    from src.tasks.instance.db_bench.task import (
        ColumnInfo,
    )
    from src.factories.data.standard_v0303.instance.db_bench.skill_evaluator import (
        SkillEvaluator,
    )
    import sqlglot

    db_bench = PseudoDBBench(2)
    for skill, info_dict in SQL_FACTORY_DEMONSTRATION_INFO_DICT.items():
        if skill not in [
            # "select",
            # "insert",
            # "delete",
            # "update",
            # "where_single_condition",
            # "where_multiple_conditions",
            # "order_by_single_column",
            # "limit_only",
            # "column_alias",
            # "table_alias",
            # "where_nested_conditions",
            # "group_by_single_column",
            # "group_by_multiple_columns",
            # "having_single_condition_with_aggregate",
            # "having_multiple_conditions_with_aggregate",
            # "having_aggregate_calculation",
            # "order_by_multiple_columns_same_direction",
            # "order_by_multiple_columns_different_directions",
            # "limit_and_offset",
            # "subquery_single",
            # "subquery_multiple",
            "subquery_nested",
        ]:
            continue
        print("=" * 20)
        print(f"Skill: {skill}")
        # print(f"Explanation: {info_dict['explanation']}")
        for sql_info in info_dict["demonstration"]:
            assert isinstance(sql_info, Mapping)
            sql = sql_info["sql"]
            print(f"SQL: {sql_info['sql']}")
            skill_list = SkillEvaluator.evaluate(sqlglot.parse_one(sql))
            print(f"Skill List: {skill_list}")
            print(f"{len(skill_list)=}")
            assert skill in skill_list
            # continue
            column_info_list = [
                ColumnInfo(name=column_info["name"], type=column_info["type"])
                for column_info in sql_info["column_info_list"]
            ]
            sql_execution_result = db_bench.execute_sql(
                sql, sql_info["table_name"], column_info_list, []
            )

            print(f"SQL Execution Result: {sql_execution_result}")


if __name__ == "__main__":
    validate()
