import base64
import sys
import logging
import jwt
import requests
from machaao import Machaao
# from pyngrok import ngrok
import json
import os
from flask import Flask, request, send_file
# from optimizedSD.optimized_sd import OptimizedModel
import torch
from ldm.generate import Generate

app = Flask(__name__)

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

base_url = os.environ.get("BASE_URL", "https://ganglia.machaao.com")
print(f"mps available: {torch.has_mps}, cuda: {torch.has_cuda}")
g = Generate()
g.load_model()


@app.route('/get_image/<path:img_url>', methods=['GET'])
def get_image(img_url):
    # names = img_url.split("-")
    # img_dest = os.path.join(*names)
    ret = None
    try:
        img_dest = os.path.join(sys.path[0], img_url)
        print(f"image dest: {img_dest}")

        if os.path.exists(img_dest):
            ret = send_file(img_dest, mimetype='image/png')
    except Exception as e:
        print(f"error in get_image: {e}")

    return ret


def extract_message(req, api_token):
    # try:
    """
    Decrypts the request body, and parses the incoming message
    """
    # print(api_token)
    decoded_jwt = None
    body = req.json
    if body and body["raw"]:
        decoded_jwt = jwt.decode(body["raw"], api_token, algorithms=['HS512'],
                                 options={'verify_signature': False, 'verify_aud': False, 'verify_nbf': False})
    text = decoded_jwt["sub"]
    if type(text) == str:
        text = json.loads(decoded_jwt["sub"])

    return text["messaging"][0]["message_data"]["text"]
    # except Exception as e:
    #     exception_handler(e)


@app.route('/webhooks/machaao/incoming', methods=['GET', 'POST'])
def receive():
    api_token = request.headers["api_token"]
    user_id = request.headers["user_id"]
    recv_text = extract_message(request, api_token)

    if str.lower(recv_text) == "hi":
        send_reply(api_token, user_id,
                   "Hi, I am a sample image generation chatbot based on Stable Diffusion\n"
                   "Please type your image generation prompt...")
    else:
        img_path = g.txt2img(recv_text)

        if len(img_path) > 0:
            img_path = img_path[0]

            if len(img_path) > 0:
                img_path = img_path[0]

        print(f"generated image @ {sys.path[0]}, {img_path}")
        img_url = f"http://localhost:5000/get_image/{img_path}"
        print(f"got a new url: {img_url}")

        send_reply(api_token, user_id, f"Here is your requested file", img_url)

    return " "


def send_reply(api_token, user_id, text, img_url=None):
    if img_url:
        msg = {
            "users": [user_id],
            "identifier": "BROADCAST_FB_TEMPLATE_GENERIC",
            "notificationType": "REGULAR",
            "source": "firebase",
            "message": {
                "text": text,
                "attachment": {
                    "type": "image",
                    "payload": {
                        "url": img_url
                    }
                },
                "quick_replies": []
            }
        }
    else:
        msg = {
            "users": [user_id],
            "identifier": "BROADCAST_FB_TEMPLATE_GENERIC",
            "notificationType": "REGULAR",
            "source": "firebase",
            "message": {
                "text": text
            },
            "quick_replies": []
        }

    machaao = Machaao(api_token, base_url)
    machaao.send_message(payload=msg)

    # read more @ https://messengerx.rtfd.io


def exception_handler(exception):
    # noinspection PyProtectedMember
    caller = sys._getframe(1).f_code.co_name
    print(f"{caller} function failed")
    if hasattr(exception, 'message'):
        print(exception.message)
    else:
        print("Unexpected error: ", sys.exc_info()[0])


if __name__ == '__main__':
    # sd_obj = OptimizedModel()
    app.run(port=5000)
