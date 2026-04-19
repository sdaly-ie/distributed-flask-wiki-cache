#!/usr/bin/env python3
"""
wiki.py - Wikipedia lookup script for CT5169 CA1.

Runs on the Amazon EC2 Ubuntu instance. Invoked remotely from the
Flask VM via Paramiko SSH. Accepts a search term as command line
arguments, performs a Wikipedia summary lookup, and prints the
result to stdout. Errors are written to stderr so the calling
Flask application can surface them to the user.
"""

import sys
import wikipedia


def main():
    if len(sys.argv) < 2:
        print("Usage: wiki.py <search term>", file=sys.stderr)
        sys.exit(1)

    # Support multi-word queries passed as separate argv entries
    query = " ".join(sys.argv[1:]).strip()

    try:
        summary = wikipedia.summary(query, sentences=5, auto_suggest=True)
        print(summary)
    except wikipedia.exceptions.DisambiguationError as e:
        options = ", ".join(e.options[:5])
        print(f"Multiple Wikipedia pages match '{query}'. "
              f"Try one of: {options}")
    except wikipedia.exceptions.PageError:
        print(f"No Wikipedia page found for '{query}'.")
    except Exception as e:
        print(f"Wikipedia lookup failed: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()