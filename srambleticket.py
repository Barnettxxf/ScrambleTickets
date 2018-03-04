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

FROM_STATION_NAME = '广州东'
TO_STATION_NAME = '深圳'
TRAIN_DATE = '2018-2-19'
TRAIN_TIME = '14:36'
TRAIN_TIME_THRESOLD = 1
FROM_STATION_NO = station[FROM_STATION_NAME]
TO_STATION_NO = station[TO_STATION_NAME]


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


def post_urls(url, data):
    data_encode = parse.urlencode(data).encode()
    req = request.Request(url, data_encode)
    response = opener.open(req)
    return response


def check_tickets():
    # It will raise Json error if there is no data returned because of slow network, should solve it tomorrow!
    url = 'https://kyfw.12306.cn/otn/leftTicket/log?leftTicketDTO.train_date={}&leftTicketDTO.from_sta\
    tion={}&leftTicketDTO.to_station={}&purpose_codes=ADULT'.format(train_date, from_station_no, to_station_no)
    response = opener.open(url)
    print(response.status)

    try:
        status = loads(response.read().decode())
    except JSONDecodeError:
        print('Return nothing, try reconneting...')
        time.sleep(1)
        check_tickets()

    if status['status']:
        print('Query left tickets suceeded...')

    url = 'https://kyfw.12306.cn/otn/leftTicket/queryZ?leftTicketDTO.train_date={}&leftTicketDTO.\
    from_station={}&leftTicketDTO.to_station={}&purpose_codes=ADULT'.format(TRAIN_DATE, FROM_STATION_NO, TO_STATION_NO)
    response = opener.open(url)
    status = loads(response.read(), encoding='utf-8')
    results = status['data']['result']
    # [3] train number
    # [7] From station
    # [6] To station
    # [8] start time
    # [9] end time
    # [10] cost time
    # [13] train data
    # [23] cushioned berths
    # [28] semi-cushioned berths
    # [26] cushioned seat
    # [29] semi-cushioned seat
    cols = ['train_number', 'from_station', 'to_station', 'start_time', 'end_time', 'cost_time',
            'train_data', 'cushioned_berths', 'semi-cushioned_berths', 'cushioned_seat', 'semi-cushioned_seat', 'secretStr']
    visualdata = pd.DataFrame(columns=cols)
    index = 0

    for result in results:
        ticketsdata = result.split('|')
        li = [ticketsdata[3], ticketsdata[7], ticketsdata[6], ticketsdata[8], ticketsdata[9], ticketsdata[10],
              ticketsdata[13], ticketsdata[23], ticketsdata[28], ticketsdata[26], ticketsdata[29], ticketsdata[0]]
        for col, colvalue in zip(cols, li):
            visualdata.loc[index, col] = colvalue
        index += 1

    if len(visualdata) > 0:
        print('Get data in need')
    else:
        print('Fail to getting data in need')
    return visualdata


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


def _login_init():
    url = 'https://kyfw.12306.cn/passport/web/login'
    data = {
        'username': '1306513796@qq.com',
        'appid': 'otn',
        'password': 'xxf15218842016',
    }
    html = post_urls(url, data)
    result = html.read().decode()
    # print(10001, result)
    if result.startswith('\ufeff'):
        result = result[3:]
    result = loads(result)
    if result['result_code'] == 0:
        print('Username and password are both correct!')
    else:
        print('ERROR!Pls check usename or password')

    url = 'https://kyfw.12306.cn/otn/login/userLogin'
    data = {
        '_json_att': '',
    }
    post_urls(url, data=data)

    url = 'https://kyfw.12306.cn/otn/passport?redirect=/otn/login/userLogin'
    opener.open(url)

    url = 'https://kyfw.12306.cn/passport/web/auth/uamtk'
    data = {
        'appid': 'otn',
    }
    html = post_urls(url, data=data)
    result = html.read().decode()
    # print(10002, result)
    if result.startswith('\ufeff'):
        result = result[3:]
    result = loads(result)
    newapptk = result['newapptk']

    url = 'https://kyfw.12306.cn/otn/uamauthclient'
    data = {
        'tk': newapptk,
    }
    html = post_urls(url, data)
    # print(10003, result)
    result = html.read().decode()
    if result.startswith('\ufeff'):
        result = result[3:]
    result = loads(result)
    if result['result_code'] == 0:
        print('-' * 10 + 'login secceeded' + '-' * 10)
        print(' '*10, '你好，{}！'.format(result['username']))
        print('-' * 10 + 'login secceeded' + '-' * 10)


def login():
    try:
        _verification_code()
        _login_init()
    except JSONDecodeError as e:
        print('JSONDecodeError!', e)
        time.sleep(3)
        print('*********Network failed, try again!*********')
        login()
    except HTTPError as e:
        print('HTTPError!', e)
        print('*********Network failed, try again!*********')
        time.sleep(3)
        login()
    except URLError as e:
        print('URLError!', e)
        print('*********Network failed, try again!*********')
        time.sleep(3)
        login()
    except TimeoutError as e:
        print('TimeoutError!', e)
        print('*********Network failed, try again!*********')
        time.sleep(3)
        login()


def pay(secretStr):

    # url = 'https://ad.12306.cn/res/0004.html'
    # response = opener.open(url)
    # billMaterialsId = re.findall(r'billMaterialsId = "(\w+)"', response)
    #
    # url = 'https://ad.12306.cn/sdk/webservice/rest/appService/getAdAppInfo.json?placementNo=0004&clientType=2&billMaterialsId={}'.format(billMaterialsId[0])
    # response = opener.open(url)

    url = 'https://kyfw.12306.cn/otn/login/checkUser'
    data = {
        '_json_att': '',
    }
    html = post_urls(url, data)
    result = html.read().decode()
    if result.startswith('\ufeff'):
        result = result[3:]
    result = loads(result)
    if int(result['httpstatus']) == 200:
        print('Login status is remain')

    url = 'https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest'
    data = {
        'secretStr': parse.urlencode(secretStr),
        'query_to_station_name': TO_STATION_NAME,
        'query_from_station_name': FROM_STATION_NAME,
        'purpose_codes': 'ADULT',
        'back_train_date': '2018-01-16',
        'undefined': '',
        'train_date': '2018-01-13',
        'tour_flag': 'dc',
    }
    html = post_urls(url, data)
    result = html.read().decode()
    if result.startswith('\ufeff'):
        result = result[3:]
    result = loads(result)
    if int(result['httpstatus']) == 200:
        print('Date & distination are submited successfully!')

    url = 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
    data = {
        '_json_att': '',
    }
    html = post_urls(url, data)
    train_date_transfrom = time.asctime(time.strptime(TRAIN_DATE, '%Y-%m-%d'))
    t_li = train_date_transfrom.split(' ')
    t_li[3], t_li[4] = t_li[4], t_li[3]
    t_li.append('GMT+0800 (中国标准时间)')
    # get parameters
    train_date_transfrom = ' '.join(t_li)
    to_station_telecode = re.findall("'to_station_telecode':'(.*?)'", html)
    station_train_code = re.findall("'station_train_code':'(.*?)'", html)
    leftTicketStr = re.findall("'leftTicketStr':'(.*?)'", html)
    purpose_codes = re.findall("'purpose_codes':'(.*?)'", html)
    train_no = re.findall("'train_no':'(.*?)'", html)
    train_location = re.findall("'train_location':'(.*?)'")
    globalRepeatSubmitToken = re.findall("globalRepeatSubmitToken = '(.*?)'", html)
    from_station_telecode = re.findall("'from_station_telecode':'(.*?)'", html)
    seat_type = 3
    key_check_isChange = re.findall("'key_check_isChange':'(.*?)'", html)


    url = 'https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs'
    data = {
        'REPEAT_SUBMIT_TOKEN': globalRepeatSubmitToken,
        '_json_att': '',
    }
    html = post_urls(url, data)
    result = html.read().decode()
    if result.startswith('\ufeff'):
        result = result[3:]
    result = loads(result)
    presonal_msg = result['data']['normal_passengers'][0]

    url = 'https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo'
    data = {
        'whatsSelect': '1',
        'tour_flag': 'dc',
        'REPEAT_SUBMIT_TOKEN': globalRepeatSubmitToken,
        'randCode': '',
        'passengerTicketStr': '3,0,1,徐雄峰,1,440182199307033011,,N',
        'oldPassengerStr': '徐雄峰,1,440182199307033011,1_',
        'cancel_flag': '2',
        'bed_level_order_num': '000000000000000000000000000000',
        '_json_att': '',
    }
    post_urls(url, data)

    url = 'https://kyfw.12306.cn/otn/confirmPassenger/getQueueCount'
    data = {
        'train_no': train_no,
        'train_location': train_location,
        'train_date': train_date_transfrom,
        'toStationTelecode': to_station_telecode,
        'stationTrainCode': station_train_code,
        'seatType': seat_type,
        'REPEAT_SUBMIT_TOKEN': globalRepeatSubmitToken,
        'purpose_codes': purpose_codes,
        'leftTicket': leftTicketStr,
        'fromStationTelecode': from_station_telecode,
        '_json_att': '',
    }
    html = post_urls(url, data)
    result = html.read().decode()
    if result.startswith('\ufeff'):
        result = result[3:]
    result = loads(result)
    if int(result['httpstatus']) == 200:
        print('GetQueueCount successfully!')

    url = 'https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue'
    data = {
        'randCode': '',
        '_json_att': '',
        'choose_seats': '',
        'roomType': '00',
        'purpose_codes': '00',
        'seatDetailType': '000',
        'whatsSelect': '1',
        'passengerTicketStr': '3,0,1,徐雄峰,1,440182199307033011,,N',
        'key_check_isChange': key_check_isChange,
        'REPEAT_SUBMIT_TOKEN': globalRepeatSubmitToken,
        'dwAll': 'N',
        'leftTicketStr': leftTicketStr,
        'train_location': train_location,
        'oldPassengerStr': '徐雄峰,1,440182199307033011,1_',
    }
    html = post_urls(url, data)
    result = html.read().decode()
    if result.startswith('\ufeff'):
        result = result[3:]
    result = loads(result)
    if int(result['httpstatus']) == 200:
        print('ConfirmSingleForQueue successfully!')

    url = 'https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime?random=1515844038507&tourFlag=dc&_json_att=&REPEAT_SUBMIT_TOKEN={}'.format(globalRepeatSubmitToken)
    html = opener.open(url)
    orderSequence_no = re.findall('"orderId":"(.*?)"')

    url = 'https://kyfw.12306.cn/otn/confirmPassenger/resultOrderForDcQueue'
    data = {
        '_json_att': '',
        'REPEAT_SUBMIT_TOKEN': globalRepeatSubmitToken,
        'orderSequence_no': orderSequence_no,
    }
    html = post_urls(url, data)
    result = html.read().decode()
    if result.startswith('\ufeff'):
        result = result[3:]
    result = loads(result)
    if int(result['httpstatus']) == 200:
        print('ResultOrderForDcQueue successfully!')

    url = 'https://kyfw.12306.cn/otn//payOrder/init?random=1515844040803'
    data = {
        'REPEAT_SUBMIT_TOKEN': globalRepeatSubmitToken,
        '_json_att': '',
    }
    print('Pls pay for the train tickets in 30 mins')


def ticket_choose(data):

    def seat_choose(data):
        data_list = []
        for each_type in SEAT_TYPE:
            acception_data = data.ix[data[each_type] != '无', :]
            data_list.append(acception_data)
        concat_data = pd.DataFrame()
        for each in data_list:
            concat_data = pd.concat([concat_data, each])
        concat_data = concat_data.drop_duplicates(['train_number'])

        return concat_data

    def time_choose(data):
        if TRAIN_TIME == None:
            return data
        for index, value in enumerate(data['start_time']):
            data.loc[index, 'start_time_hour'] = int(value.split(':')[0])
        hour = int(TRAIN_TIME.split(':')[0])
        thresold_up = hour + TRAIN_TIME_THRESOLD + .1
        thresold_down = hour - TRAIN_TIME_THRESOLD - .1
        acception_data = data.ix[data['start_time_hour'] > thresold_down, :]
        acception_data = acception_data.ix[acception_data['start_time_hour'] < thresold_up, :]
        return acception_data

    chozen_data = time_choose(data)
    if len(chozen_data['train_number']) < 1:
        print('There is no train time meeting acauirements, pls reset train_time')
        global TRAIN_TIME
        TRAIN_TIME = input('Pls input new train time(format: xx:xx)>>>')
        ticket_choose(data)
    chozen_data = seat_choose(chozen_data)

    if len(chozen_data['train_number']) < 1:
        print('There is no one met acquirements, pls reset seat type')
        global SEAT_TYPE
        SEAT_TYPE = input('''
                            Pls choose seat type and input its number:
                            1.cushioned_berths
                            2.semi-cushioned_berths
                            3.cushioned_seat
                            4.semi-cushioned_seat
                            >>>
                            ''')
        ticket_choose(data)

    return chozen_data.loc[1, 'secretStr']


def main():
    print('Login...')
    login()
    print('Checking tickets')
    data = check_tickets()
    print('Choosing tickets')
    secretStr = ticket_choose(data)
    print('Booking tickets')
    pay(secretStr=secretStr)
    print('Pls pay in 30 minutes in 12306.com!')
    # sentTo()

if __name__ == '__main__':
    main()
