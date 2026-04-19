from flask import Flask, request
import html
import os
import paramiko
import pymysql
import shlex

app = Flask(__name__)

# EC2 / Wikipedia settings
INSTANCE_IP = os.getenv("EC2_INSTANCE_IP", "YOUR_EC2_PUBLIC_IP")
SECURITY_KEY_FILE = os.getenv("EC2_KEY_FILE", "/path/to/YOUR_KEY.pem")
REMOTE_PYTHON = os.getenv("REMOTE_PYTHON", "/home/ubuntu/ct5169-wiki/venv/bin/python")
REMOTE_SCRIPT = os.getenv("REMOTE_SCRIPT", "/home/ubuntu/ct5169-wiki/wiki.py")
REMOTE_USERNAME = os.getenv("REMOTE_USERNAME", "ubuntu")

# MySQL cache settings
DB_HOST = os.getenv("CACHE_DB_HOST", "YOUR_CACHE_VM_IP")
DB_PORT = int(os.getenv("CACHE_DB_PORT", "7888"))
DB_NAME = os.getenv("CACHE_DB_NAME", "wiki_cache")
DB_USER = os.getenv("CACHE_DB_USER", "ct5169")
DB_PASSWORD = os.getenv("CACHE_DB_PASSWORD", "YOUR_DB_PASSWORD")


def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )


def get_cached_result(query):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT result_text FROM searches WHERE query_text = %s",
                (query,)
            )
            row = cursor.fetchone()
            return row["result_text"] if row else None
    finally:
        connection.close()


def save_result_to_cache(query, result_text):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO searches (query_text, result_text)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE result_text = VALUES(result_text)
                """,
                (query, result_text)
            )
        connection.commit()
    finally:
        connection.close()


def fetch_wikipedia_result(query):
    cmd = f'{REMOTE_PYTHON} {REMOTE_SCRIPT} {shlex.quote(query)}'

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    key = paramiko.RSAKey.from_private_key_file(SECURITY_KEY_FILE)
    client.connect(hostname=INSTANCE_IP, username=REMOTE_USERNAME, pkey=key)

    stdin, stdout, stderr = client.exec_command(cmd)
    stdin.close()

    errors = stderr.read().decode().strip()
    output = stdout.read().decode().strip()

    client.close()

    if errors:
        return f"Remote error:\n{errors}"
    if output:
        return output
    return "No output returned from Wikipedia script."


@app.route("/", methods=["GET"])
def home():
    return """
    <html>
      <head><title>CT5169 Search App</title></head>
      <body>
        <h1>CT5169 Search App</h1>
        <form action="/search" method="get">
          <label for="q">Search:</label>
          <input type="text" id="q" name="q" required>
          <button type="submit">Search</button>
        </form>
      </body>
    </html>
    """


@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "").strip()

    if not query:
        return """
        <html>
          <head><title>Search Result</title></head>
          <body>
            <h1>Search Result</h1>
            <p>No search term provided.</p>
            <a href="/">Search for something else</a>
          </body>
        </html>
        """

    try:
        cached_result = get_cached_result(query)

        if cached_result:
            result_text = cached_result
            source = "Cache"
        else:
            result_text = fetch_wikipedia_result(query)
            save_result_to_cache(query, result_text)
            source = "Remote Wikipedia via EC2"

    except Exception as e:
        result_text = f"Application error: {str(e)}"
        source = "Error"

    safe_query = html.escape(query)
    safe_result = html.escape(result_text)
    safe_source = html.escape(source)

    return f"""
    <html>
      <head><title>Search Result</title></head>
      <body>
        <h1>Search Result</h1>
        <p>You searched for: <strong>{safe_query}</strong></p>
        <p><strong>Source:</strong> {safe_source}</p>
        <pre>{safe_result}</pre>
        <a href="/">Search for something else</a>
      </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8888, debug=True)
