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
    """Open a new PyMySQL connection to the MySQL cache database.

    Uses the DB_* configuration resolved from environment variables
    at module load. Returns a connection configured with DictCursor
    so rows come back as dicts rather than tuples. Callers are
    responsible for closing the connection in a finally block.
    """
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )


def get_cached_result(query):
    """Look up a previous search in the MySQL cache.

    Returns the stored result_text for an exact match on
    query_text, or None if the query has not been searched
    before. A None return is what triggers the remote
    Wikipedia fallback path in the /search route.
    """
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
    """Write or refresh a search result in the MySQL cache.

    Uses INSERT ... ON DUPLICATE KEY UPDATE so a repeat
    search for the same term overwrites the stored result
    rather than raising a duplicate-key error. The UNIQUE
    constraint on searches.query_text (see db/schema.sql)
    is what makes this upsert possible.
    """
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
    """Run wiki.py on the EC2 VM over SSH and return its stdout.

    Opens a Paramiko SSH session to the configured EC2 instance,
    executes the remote Python interpreter against wiki.py with
    the user query passed as a shell-quoted argument, and returns 
    the remote stdout. If stdout is empty and stderr contains
    output, stderr is returned instead so genuine failures surface
    in the browser.
    """
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
    # stderr can contain harmless warnings (e.g. library deprecation notices). Only treat stderr as an error when stdout is empty.
    if output:
        return output
    if errors:
        return f"Remote error:\n{errors}"
    return "No output returned from Wikipedia script."

@app.route("/", methods=["GET"])
def home():
    """Render the search form as the landing page."""
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
    """Handle a search request using a cache-aside strategy.

    Contract:
      1. If the query is already in MySQL, return the cached
         result and tag the Source as 'Cache'.
      2. Otherwise call fetch_wikipedia_result() to run wiki.py
         on the EC2 VM, persist the result via
         save_result_to_cache(), and tag the Source as
         'Remote Wikipedia via EC2'.
    Any exception in this flow is caught and rendered as an
    error page so the browser always receives a response.
    """
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

    # Cache-aside: check MySQL first; on miss, fall back to EC2
    # and write the result through so the next call is a cache hit.
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
        <pre style="white-space: pre-wrap; word-wrap: break-word;">{safe_result}</pre>
        <a href="/">Search for something else</a>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8888, debug=True)