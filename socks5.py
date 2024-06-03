import asyncio
import random
import ssl
import json
import time
import uuid
import requests
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

user_agent = UserAgent()
random_user_agent = user_agent.random

async def connect_to_wss(socks5_proxy, user_id, retry_count=3):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    proxy_ip, proxy_port = socks5_proxy.rsplit(':', 1)
    logger.info(f"Connecting with device ID: {user_id} using proxy: {proxy_ip}:{proxy_port}")
    for attempt in range(retry_count):
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {
                "User-Agent": random_user_agent,
                "Origin": "chrome-extension://ilehaonighjijnmpnagapkhpcdbhclfg"
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            uri = "wss://proxy.wynd.network:4444/"
            server_hostname = "proxy.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(f"Sending ping message to {uri} using proxy: {proxy_ip}:{proxy_port}")
                        await websocket.send(send_message)
                        await asyncio.sleep(20)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(f"Received message from {uri} using proxy: {proxy_ip}:{proxy_port}: {message}")
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "extension",
                                "version": "4.0.1"
                            }
                        }
                        logger.debug(f"Sending auth response to {uri} using proxy: {proxy_ip}:{proxy_port}: {auth_response}")
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(f"Sending pong response to {uri} using proxy: {proxy_ip}:{proxy_port}: {pong_response}")
                        await websocket.send(json.dumps(pong_response))
            break
        except Exception as e:
            logger.error(f"Error connecting with proxy {proxy_ip}:{proxy_port}: {e}")
            if attempt < retry_count - 1:
                logger.info(f"Retrying connection to WebSocket using proxy {proxy_ip}:{proxy_port}...")
                await asyncio.sleep(10)  # retry after 10 seconds
            else:
                logger.error(f"Failed to connect to WebSocket using proxy {proxy_ip}:{proxy_port} after {retry_count} attempts.")
                with open("socks5_non_working_proxies.log", "a") as f:
                    f.write(f"{socks5_proxy}\n")
                break

async def main():
    _user_id = input('Please Enter your user ID: ')
    proxy_list_url = "https://raw.githubusercontent.com/Rionaldio/proxy2/main/socks5.txt"
    r = requests.get(proxy_list_url, stream=True)
    if r.status_code == 200:
        with open('socks5.txt', 'wb') as f:
            for chunk in r:
                f.write(chunk)
        with open('socks5.txt', 'r') as file:
            socks5_proxy_list = file.read().splitlines()
    else:
        logger.error(f"Failed to retrieve proxy list from {proxy_list_url}")
        return

    tasks = []
    for proxy in socks5_proxy_list:
        proxy_ip, proxy_port = proxy.split('@')[-1].split(':')
        logger.info(f"Connecting to {proxy_ip}:{proxy_port}...")
        tasks.append(asyncio.ensure_future(connect_to_wss(f"socks5://{proxy}", _user_id)))

    await asyncio.gather(*tasks)

if __name__ == '__main__':
    logger.add("log_file_socks5.log", format="{time:MMMM D, YYYY - HH:mm:ss} | {level} | {message}", level="DEBUG")
    asyncio.run(main())