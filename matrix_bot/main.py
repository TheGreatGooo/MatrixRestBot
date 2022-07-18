#!/usr/bin/env python3

from ast import arg
import asyncio
import getpass
import json
import os
import sys
import argparse
from flask import Flask, request
from h11 import CLIENT

from nio import AsyncClient, LoginResponse

CONFIG_FILE = "credentials.json"
CLINET = None
APP = Flask(__name__)
ROOM_ID = None

def write_details_to_disk(resp: LoginResponse, homeserver) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump(
            {
                "homeserver": homeserver,
                "user_id": resp.user_id,
                "device_id": resp.device_id,
                "access_token": resp.access_token,
            },
            f,
        )


async def initializeClient(homeserver, bot_user_id, device_name, bot_password, room_id) -> None:
    if not os.path.exists(CONFIG_FILE):
        print(
            "First time use. Did not find credential file. Asking for "
            "homeserver, user, and password to create credential file."
        )

        if not (homeserver.startswith("https://") or homeserver.startswith("http://")):
            homeserver = "https://" + homeserver

        user_id = bot_user_id
        ROOM_ID = room_id
        client = AsyncClient(homeserver, user_id)
        CLIENT = client
        pw = bot_password

        resp = await client.login(pw, device_name=device_name)

        if isinstance(resp, LoginResponse):
            write_details_to_disk(resp, homeserver)
        else:
            print(f'homeserver = "{homeserver}"; user = "{user_id}"')
            print(f"Failed to log in: {resp}")
            sys.exit(1)

        print(
            "Logged in using a password. Credentials were stored.",
            "Will exit now.",
        )
        await client.close()
    else:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            client = AsyncClient(config["homeserver"])

            client.access_token = config["access_token"]
            client.user_id = config["user_id"]
            client.device_id = config["device_id"]

        await client.room_send(
            room_id,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": "Hello world!"},
        )

@APP.route('/message', methods=['GET','POST'])
async def message_handler():
 if request.method == 'POST':
    await send_message(request.get_json())
 elif request.method == 'GET':
    return get_message_cache()

def get_message_cache():
    return []

async def send_message(message_to_send):
    await CLIENT.room_send(
            ROOM_ID,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": message_to_send.body},
        )
    return {"message":"Done!"}

def main() -> None:
    parser = argparse.ArgumentParser(description='A rest server that proxies to matrix with e2e encryption')
    parser.add_argument('--homeserver', help='The homeserver ie. https://cake.example.org', required=True)
    parser.add_argument('--bot_uid', help='The bot userid only required for the initial run ie. @cookieMonster:cake.example.org', required=False)
    parser.add_argument('--device_name', help='The device name ie. ARowBot', required=True)
    parser.add_argument('--bot_pwd', help='The password for the bot only required for the initial run', required=False)
    parser.add_argument('--room_id', help='The room this bot is monitoring ie. !BotParty:cake.example.org', required=True)

    args = parser.parse_args()
    asyncio.run(initializeClient(args.homeserver, args.bot_uid, args.device_name, args.bot_pwd, args.room_id))
    APP.run(debug=True)