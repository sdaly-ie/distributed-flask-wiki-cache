# Distributed Flask Web Application with Remote Wikipedia Search and MySQL Cache

## Overview

This project is a distributed Python web application built for a cloud computing assignment. A Flask application runs on an Ubuntu virtual machine, executes a remote Wikipedia search script on an Ubuntu Amazon EC2 instance over SSH using Paramiko, and caches repeated search results in a MySQL database running in Docker on a separate Ubuntu virtual machine.

## What it demonstrates

- Flask web application on Ubuntu
- Host browser access to the application
- Remote Python execution on Amazon EC2 using Paramiko over SSH
- MySQL caching on a separate VM in Docker
- Basic distributed application design across multiple machines
- VM-to-VM networking using NAT and Host-only adapters

## Architecture

Browser on Host Machine -> Flask VM -> MySQL Cache VM
Browser on Host Machine -> Flask VM -> Amazon EC2 wiki.py fallback

## Search flow

1. The user enters a search term in the Flask web application.
2. Flask checks the MySQL cache first.
3. If a cached result exists, Flask returns it immediately.
4. If no cached result exists, Flask connects to the EC2 instance over SSH.
5. Flask runs wiki.py remotely on the EC2 VM.
6. The result is returned to Flask and saved into MySQL.
7. Future identical searches are served from the cache.

## Main files

- main.py - Flask web application with cache lookup and remote EC2 execution
- paramiko_test.py - standalone SSH test script for remote execution
- requirements.txt - Python dependencies

## Dependencies

Install dependencies with:

    pip install -r requirements.txt

## Configuration

This public repo uses placeholder values for:

- EC2 public IP
- SSH private key path
- cache VM IP
- database password

Replace the placeholder environment values in your local environment before running.

## Notes

- The real private key file is intentionally excluded.
- The live infrastructure details have been replaced with placeholders for safety.
- This repo is intended as a portfolio-safe version of the project.
