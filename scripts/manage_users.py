"""Simple command‑line user management utility for the webapp.

Usage examples:

    # create a new user (interactive password input)
    python scripts/manage_users.py create alice --scopes "['*']" --superuser

    # list usernames
    python scripts/manage_users.py list

    # add a service API key to an existing user
    python scripts/manage_users.py add-key alice my-generated-key

    # revoke all API keys for a user
    python scripts/manage_users.py clear-keys alice

The tool operates against the same JSON store used by the webapp, making it
useful for bootstrapping and migrations.
"""
import argparse
import getpass
import json
import secrets
import sys
from pathlib import Path

from webapp.store import add_user, list_users, set_api_key, load_users, save_users
from webapp.security.auth import get_password_hash, generate_api_key


def do_create(args):
    username = args.username
    users = load_users()
    if username in users and not args.force:
        print(f"user '{username}' already exists (use --force to overwrite)")
        return

    pwd = args.password
    if not pwd:
        pwd = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm: ")
        if pwd != confirm:
            print("passwords did not match")
            sys.exit(1)

    hashed = get_password_hash(pwd)
    scopes = json.loads(args.scopes) if args.scopes else []
    record = add_user(
        username, hashed,
        scopes=scopes,
        is_active=not args.inactive,
        is_superuser=args.superuser,
    )
    print(f"created user '{username}'")
    if args.api_key:
        raw = generate_api_key()
        set_api_key(username, raw)
        print(f"generated api key: {raw}")


def do_list(_args):
    for u in list_users():
        print(u)


def do_add_key(args):
    raw = args.key or generate_api_key()
    set_api_key(args.username, raw)
    print(f"added key to {args.username}: {raw}")


def do_clear_keys(args):
    users = load_users()
    user = users.get(args.username)
    if not user:
        print(f"no such user {args.username}")
        sys.exit(1)
    user['api_keys'] = []
    save_users(users)
    print(f"cleared keys for {args.username}")


def main():
    parser = argparse.ArgumentParser(description="Manage webapp users")
    sub = parser.add_subparsers(dest='cmd')

    p = sub.add_parser('create', help='create or update a user')
    p.add_argument('username')
    p.add_argument('--password', help='plain text password (unsafe)')
    p.add_argument('--scopes', help='JSON array of scopes', default='[]')
    p.add_argument('--superuser', action='store_true')
    p.add_argument('--inactive', action='store_true')
    p.add_argument('--api-key', action='store_true', help='generate an api key')
    p.add_argument('--force', action='store_true')

    sub.add_parser('list', help='list usernames')

    p2 = sub.add_parser('add-key', help='add a service API key to user')
    p2.add_argument('username')
    p2.add_argument('key', nargs='?')

    p3 = sub.add_parser('clear-keys', help='revoke all keys for a user')
    p3.add_argument('username')

    args = parser.parse_args()
    if args.cmd == 'create':
        do_create(args)
    elif args.cmd == 'list':
        do_list(args)
    elif args.cmd == 'add-key':
        do_add_key(args)
    elif args.cmd == 'clear-keys':
        do_clear_keys(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
