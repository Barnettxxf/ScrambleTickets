# -*- coding:utf-8 -*-
'''
author: Barnett
'''
from urllib import request, parse
from http import cookiejar
import re
import ssl
from json import loads, JSONDecodeError, load
import pandas as pd
import time
from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
from config import *
from urllib.error import HTTPError, URLError

# loads station infomation
with open('station.json', 'r', encoding='utf-8') as f:
    station = load(f)

# not warning on unverified http/https
ssl._create_default_https_context = ssl._create_unverified_context

# create a cookie respoitory
header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36'
}
jar = cookiejar.LWPCookieJar()
cookie = request.HTTPCookieProcessor(jar)
opener = request.build_opener(cookie)
opener.addheaders = [(key, value) for key, value in header.items()]
request.install_opener(opener)

def post_urls(url, data):
    data_encode = parse.urlencode(data).encode()
    req = request.Request(url, data_encode)
    response = opener.open(req)
    return response


def input_location():
    img = np.array(Image.open('img_for_identify.png'))
    fig = plt.figure(1)
    plt.imshow(img)
    coor = []

    def on_click(event):
        ix = str(int(event.xdata)+5)
        iy = str(int(event.ydata)-25)
        coor.append(ix)
        coor.append(iy)

    fig.canvas.mpl_connect('button_press_event', on_click)
    plt.show()
    result = coor
    coor = []
    # print(','.join(result))
    return ','.join(result)

def _verification_code():
    # get verification code image and input
    img_url = 'https://kyfw.12306.cn/passport/captcha/captcha-image?login_site=E&module=login&rand=sjrand&0.6565497217868979'
    response = opener.open(img_url).read()
    with open('img_for_identify.png', 'wb') as f:
        f.write(response)

    # location = input('Pls input coordinates of  verification code:')
    location = input_location()
    data = {
        'answer': location,
        'login_site': 'E',
        'rand': 'sjrand',
    }
    url = 'https://kyfw.12306.cn/passport/captcha/captcha-check'
    html = post_urls(url, data=data)
    result = loads(html.read().decode())
    if int(result['result_code']) == 4:
        print('verification code is correct!')
    else:
        print('verification code is wrong, pls try again.')
        print("notes:don't input space after number")
        time.sleep(0.5)
        _verification_code()

_verification_code()


