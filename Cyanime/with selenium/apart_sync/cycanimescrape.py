'''
此模块是个函数包，包含了cyanime_main和cyanime_update所需的函数、宏和一些设置
'''

import os
import re
import redis
import logging
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL='https://cycanime.com'
USER_AGENT='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'

filepath = __file__
filename_with_extension = os.path.basename(filepath)
filename_no_extension = os.path.splitext(filename_with_extension)[0]

logging.basicConfig(filename=f'{filename_no_extension}.log',  # 日志文件名
                    level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    encoding='utf-8')

logger = logging.getLogger(__name__)

## connect to a redis db
redis=redis.Redis('localhost','6379',db=0)

def browser_wait(browser,ATTRS,attrs,ismany=False):
    '''function to wait for one or more certain elements on the browser to appear'''
    wait=WebDriverWait(browser,10)
    if ismany:
        try:
            wait=wait.until(EC.presence_of_all_elements_located((ATTRS,attrs)))
        except:
            logger.error(f'Error in waiting {attrs} on the browser\n')
        else:
            return wait
    else:
        try:
            wait=wait.until(EC.presence_of_element_located((ATTRS,attrs)))
        except:
            logger.error(f'Error in waiting {attrs}\n')
        else:
            return wait   

def parse_html(html,regex,ismany=False):
    '''parse the html with given regular expression'''
    pattern=re.compile(regex,re.S)
    if ismany:
        return re.findall(pattern,html)
    else:
        return re.search(pattern,html).group(1).strip() if re.search(pattern,html) else None


def download_video(video,filename):
    '''download a video with the given video link'''
    if video:
        video_response = requests.get(video, stream=True)
        if video_response.status_code == 200:
            # 提取文件名
            with open(filename, 'wb') as f:
                for chunk in video_response.iter_content(chunk_size=1024):
                    f.write(chunk)
            
            print(f'Successfully downloaded {filename}')
        else:
            print(f'Failed to download the video. Status code: {video_response.status_code}')

def GET(url,headers=None):
    '''request the webpage with certain url'''
    try:
        response=requests.get(url,headers=headers)
    except(ConnectionError):
        logger.error(f'ConnectionError in requesting {url}')
    else:
        return response

def browser_init():
    '''initialize the browser object'''
    options=webdriver.ChromeOptions()
    options.add_argument('--headless')
    return webdriver.Chrome(options=options)
