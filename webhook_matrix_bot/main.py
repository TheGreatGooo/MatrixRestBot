#!/usr/bin/env python3

from ast import arg
import asyncio
import getpass
import json
import os
import sys
import argparse
from flask import Flask, jsonify, request
from importlib import util
from nio import AsyncClient, LoginResponse, ClientConfig, exceptions, crypto, RoomMessageText, MatrixRoom
from concurrent.futures import ThreadPoolExecutor
import time

CONFIG_FILE = "credentials.json"
APP = Flask(__name__)
room = None
client = None
EVENT_LOOP = asyncio.events.new_event_loop()
NUMBER_OF_MESSAGES_TO_CACHE = 10
MESSAGE_CACHE = []

def write_details_to_disk(resp: LoginResponse, homeserver, conf_dir) -> None:
    with open(f'{conf_dir}/{CONFIG_FILE}', "w") as f:
        json.dump(
            {
                "homeserver": homeserver,
                "user_id": resp.user_id,
                "device_id": resp.device_id,
                "access_token": resp.access_token,
            },
            f,
        )


async def initializeClient(homeserver, bot_user_id, device_name, bot_password, room_id, conf_dir) -> None:
    global client
    global room
    if not os.path.exists(f'{conf_dir}/{CONFIG_FILE}'):
        print(
            "First time use. Did not find credential file. Asking for "
            "homeserver, user, and password to create credential file."
        )

        if not (homeserver.startswith("https://") or homeserver.startswith("http://")):
            homeserver = "https://" + homeserver

        user_id = bot_user_id
        room = room_id
        client = AsyncClient(homeserver, user_id,store_path = f'{conf_dir}/store/', config=ClientConfig(encryption_enabled=True,store_sync_tokens=True))
        pw = bot_password

        resp = await client.login(pw, device_name=device_name)

        if isinstance(resp, LoginResponse):
            write_details_to_disk(resp, homeserver, conf_dir)
        else:
            print(f'homeserver = "{homeserver}"; user = "{user_id}"')
            print(f"Failed to log in: {resp}")
            sys.exit(1)
    else:
        with open(f'{conf_dir}/{CONFIG_FILE}', "r") as f:
            config = json.load(f)
            client = AsyncClient(config["homeserver"],config["user_id"],device_id=config["device_id"],store_path = f'{conf_dir}/store/', config=ClientConfig(encryption_enabled=True,store_sync_tokens=True))
            room = room_id
            client.access_token = config["access_token"]
            client.user_id = config["user_id"]
            client.device_id = config["device_id"]
            client.load_store()
    client.add_event_callback(store_recent_messages,RoomMessageText)
    async def after_first_sync():
        print("Awaiting sync")
        await client.synced.wait()
        print("Sync completed")
        APP.event_loop = EVENT_LOOP
        ThreadPoolExecutor().submit(lambda _:APP.run(host="0.0.0.0",port=5000,debug=False))
    after_first_sync_task = asyncio.ensure_future(after_first_sync())
    sync_forever_task = asyncio.ensure_future(
        client.sync_forever(30000, full_state=True)
    )
    await asyncio.gather(
        after_first_sync_task,
        sync_forever_task,
    )

async def store_recent_messages(room: MatrixRoom, event: RoomMessageText):
    if event.sender == client.user :
        return
    if event.decrypted:
        encrypted_symbol = "🛡 "
    else:
        encrypted_symbol = "⚠️ "
    MESSAGE_CACHE.append({
        "roomName": room.display_name,
        "isEncrpted": event.decrypted,
        "user_name": room.user_name(event.sender),
        "message": event.body,
        "message_received_ts": time.time(),
    })
    if len(MESSAGE_CACHE)>NUMBER_OF_MESSAGES_TO_CACHE :
        for _ in range(0,len(MESSAGE_CACHE)-NUMBER_OF_MESSAGES_TO_CACHE) :
            MESSAGE_CACHE.pop(0)

def trust_devices(user_id):
     print(f"{user_id}'s device store: {client.device_store[user_id]}")
     for device_id, olm_device in client.device_store[user_id].items():
            if user_id == client.user_id and device_id == client.device_id:
                continue
            client.verify_device(olm_device)
            print(f"Trusting {device_id} from user {user_id}")

@APP.route('/message', methods=['GET','POST'])
async def message_handler():
 if request.method == 'POST':
    EVENT_LOOP.create_task(send_message(request.get_json()))
    return jsonify("{'data':'Done!'}")
 elif request.method == 'GET':
    return get_message_cache()

def get_message_cache():
    return jsonify(MESSAGE_CACHE)

async def send_message(message_to_send):
    print(f"sending to {room} message {message_to_send['body']}")
    try:
        await client.room_send(
                room,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": message_to_send['body']},
                ignore_unverified_devices=True,
            )
    except exceptions.OlmUnverifiedDeviceError as err:
        print("These are all known devices:")
        for device in client.device_store:
            print(
                f"\t{device.user_id}\t {device.device_id}\t {device.trust_state}\t  {device.display_name}"
            )
    return {"message":"Done!"}

def main() -> None:
    parser = argparse.ArgumentParser(description='A rest server that proxies to matrix with e2e encryption')
    parser.add_argument('--homeserver', help='The homeserver ie. https://cake.example.org', required=True)
    parser.add_argument('--bot_uid', help='The bot userid only required for the initial run ie. @cookieMonster:cake.example.org', required=False)
    parser.add_argument('--device_name', help='The device name ie. ARowBot', required=True)
    parser.add_argument('--bot_pwd', help='The password for the bot only required for the initial run', required=False)
    parser.add_argument('--room_id', help='The room this bot is monitoring ie. !BotParty:cake.example.org', required=True)
    parser.add_argument('--conf_dir', help='Configuration directory', required=True)

    print("encryption library:")
    print(util.find_spec("olm"))
    args = parser.parse_args()
    asyncio.set_event_loop(EVENT_LOOP)
    EVENT_LOOP.run_until_complete(initializeClient(args.homeserver, args.bot_uid, args.device_name, args.bot_pwd, args.room_id, args.conf_dir))
