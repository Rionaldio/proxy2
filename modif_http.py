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

# Set up logging
logger.add("http_proxy_log.log", format="{time:MMMM D, YYYY HH:mm:ss} | {level} | {message}", level="INFO")

async def connect_to_wss(socks5_proxy, user_id, retry_count=3):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(f"Connecting with device ID: {device_id} using proxy: {socks5_proxy}")
    
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
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(20)

                # asyncio.create_task(send_http_request_every_10_seconds(socks5_proxy, device_id))
                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)
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
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))
            break
        except Exception as e:
            logger.error(f"Error connecting to WebSocket using proxy {socks5_proxy}: {e}")
            if attempt < retry_count - 1:
                logger.info(f"Retrying connection to WebSocket using proxy {socks5_proxy}...")
            else:
                logger.error(f"Failed to connect to WebSocket using proxy {socks5_proxy} after {retry_count} attempts.")
                with open("http_non_working_proxies.log", "a") as f:
                    f.write(f"{socks5_proxy}\n")
                break

async def main():
    _user_id = input('Please Enter your user ID: ')
    r = requests.get("https://raw.githubusercontent.com/Rionaldio/proxy2/main/http.txt", stream=True)
    if r.status_code == 200:
        with open('http.txt', 'wb') as f:
            for chunk in r:
                f.write(chunk)
        with open('http.txt', 'r') as file:
            socks5_proxy_list = file.read().splitlines()
    
    tasks = [asyncio.ensure_future(connect_to_wss('http://'+i, _user_id)) for i in socks5_proxy_list]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())