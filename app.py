from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import mysql.connector
import re
from config import db_config

app = Flask(__name__)
CORS(app)  # This will allow all origins by default


# Home route
@app.route('/')
def home():
    return render_template('index.html')  # Ensure index.html exists in the 'templates' folder


# MySQL database connection setup
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='flask_user',     # Replace with your actual username
            password='password',  # Replace with your actual password
            database='flask_project_db'   # Ensure this is your actual database name
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None


# Node class to represent AST structure
class Node:
    def __init__(self, node_type, operator=None, left=None, right=None, value=None):
        self.node_type = node_type  # "operator" or "operand"
        self.operator = operator    # AND/OR for operators, None for operands
        self.left = left            # Left child (if operator)
        self.right = right          # Right child (if operator)
        self.value = value          # Value for operands (e.g., comparison value)


# Tokenizing and parsing rules
def tokenize(rule_string):
    tokens = re.findall(r"\w+|[><=]+|AND|OR|\(|\)", rule_string)
    return tokens


# Recursively build AST from tokens
def build_ast(tokens):
    if len(tokens) == 0:
        return None

    if "(" in tokens and ")" in tokens:
        open_idx = tokens.index("(")
        close_idx = tokens.index(")")
        sub_tokens = tokens[open_idx + 1:close_idx]
        sub_tree = build_ast(sub_tokens)

        tokens = tokens[:open_idx] + [sub_tree] + tokens[close_idx + 1:]

    if len(tokens) == 1 and isinstance(tokens[0], Node):
        return tokens[0]

    if "AND" in tokens or "OR" in tokens:
        operator_idx = max(tokens.index("AND") if "AND" in tokens else -1,
                           tokens.index("OR") if "OR" in tokens else -1)
        left = build_ast(tokens[:operator_idx])
        right = build_ast(tokens[operator_idx + 1:])
        operator = tokens[operator_idx]
        return Node(node_type="operator", operator=operator, left=left, right=right)

    if len(tokens) == 3:  # E.g., age > 30
        return Node(node_type="operand", value=tokens)

    return None


# Function to create a rule (return AST root)
def create_rule(rule_string):
    tokens = tokenize(rule_string)
    return build_ast(tokens)


# Route to create the table in MySQL
@app.route('/create_table', methods=['GET'])
def create_table():
    connection = get_db_connection()
    if connection is None:
        return "Database connection failed!", 500

    cursor = connection.cursor()

    # Create the 'rules' table
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rules (
                id INT AUTO_INCREMENT PRIMARY KEY,
                rule_string TEXT
            )
        ''')
        connection.commit()
        return 'Table created successfully!'
    except mysql.connector.Error as err:
        return f"Error creating table: {err}", 500
    finally:
        cursor.close()
        connection.close()


# Function to evaluate the rule against user data
def evaluate_rule_ast(node, data):
    if node.node_type == "operand":
        attr, op, val = node.value
        attr_value = data.get(attr)

        # Type conversion for comparison
        if val.isdigit():
            val = int(val)
        elif val.replace('.', '', 1).isdigit():
            val = float(val)
        else:
            val = val.strip("'")

        if op == ">":
            return attr_value > val
        elif op == "<":
            return attr_value < val
        elif op == "=":
            return attr_value == val
    elif node.node_type == "operator":
        left_result = evaluate_rule_ast(node.left, data)
        right_result = evaluate_rule_ast(node.right, data)
        if node.operator == "AND":
            return left_result and right_result
        elif node.operator == "OR":
            return left_result or right_result
    return False


# API Route to evaluate a rule
@app.route('/evaluate_rule', methods=['POST'])
def evaluate_rule_api():
    content = request.json
    rule = content.get("rule")
    data = content.get("data")

    if not rule or not data:
        return jsonify({"message": "Rule or user data missing!"}), 400

    try:
        # Convert rule to AST
        ast_root = create_rule(rule)

        # Evaluate the rule with user data
        result = evaluate_rule_ast(ast_root, data)

        return jsonify({"result": result})
    except Exception as e:
        print(f"Error evaluating rule: {e}")
        return jsonify({"message": "Error evaluating rule."}), 500


# Route to add a rule to the database
@app.route('/add_rule', methods=['POST'])
def add_rule():
    content = request.json
    rule = content.get("rule")

    if not rule:
        return jsonify({"message": "Rule is required!"}), 400

    connection = get_db_connection()
    if connection is None:
        return "Database connection failed!", 500

    cursor = connection.cursor()

    try:
        cursor.execute("INSERT INTO rules (rule_string) VALUES (%s)", (rule,))
        connection.commit()
        return jsonify({"message": "Rule added successfully!"})
    except mysql.connector.Error as err:
        return f"Error inserting rule: {err}", 500
    finally:
        cursor.close()
        connection.close()


if __name__ == '__main__':
    app.run(debug=True)
