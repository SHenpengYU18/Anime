'''
这是一个从cycanime.com动漫网站上主页的“新番就要追着看的”的“更多”页面上搜集新番信息的爬虫
他会从https://cycanime.com/label/weekday.html 页面从周一的番剧开始爬取一周的所有番剧的信息
具体包括番名，剧情简介，更新至第几集，每集的原视频链接。
这些信息会被存储到Redis db中，使用本地服务器的默认6379端口。
但是番剧会更新，每周（甚至每天）都必须将更新至第几集以及更新的集数的链接更新
因此此爬虫可以作为获取当前新番的初始化模块，只需在新番出来时执行依次（也就是1、4、7、10）月开始时。
'''
import os
import re
import redis
import logging
import requests
import multiprocessing
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL='https://cycanime.com'
USER_AGENT='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'


filepath = __file__
filename_with_extension = os.path.basename(filepath)
filename_no_extension = os.path.splitext(filename_with_extension)[0]

# print(f"当前文件的名称（去除后缀）是: {filename_no_extension}")


logging.basicConfig(filename=f'{filename_no_extension}.log',  # 日志文件名
                    level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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


def main(weekday):
    '''the main function to search the weekday page 
    to find all the animes recently updated. It will
    store their information in redis on the localhost port
    '''
    browser=browser_init()
    browser.get(BASE_URL+'/label/weekday.html')
    class_name=f'week-key{weekday}'
    element=browser_wait(browser,By.CLASS_NAME,class_name)
    element.click()
    browser_wait(browser, By.CSS_SELECTOR, f'#week-list{weekday} .lazy',ismany=True)
    ele2=browser_wait(browser, By.CSS_SELECTOR, f'#week-list{weekday} .public-list-exp',ismany=True)
    html='\n'.join([ele2[weekday].get_attribute('outerHTML') for weekday in range(len(ele2))])
    regex='href="(.*?)"'
    anime_urls_append=parse_html(html,regex,ismany=True)

    ## 遍历周页（weekday）中的每个动漫的介绍页
    for anime_url_append in anime_urls_append:
        intro_url=BASE_URL+anime_url_append
        headers=headers = {'User-Agent': USER_AGENT}
        resp=GET(intro_url,headers=headers)
        regex2='<a class="hide" href="(.*?)">'
        episodes_url_append=parse_html(resp.text,regex2,ismany=True)

        ## 遍历此动漫的所有集数的播放页
        anime_name=''
        for episode in range(1,len(episodes_url_append)):

            episode_url=BASE_URL+episodes_url_append[episode]
            browser.get(episode_url)
            element=browser_wait(browser,By.CLASS_NAME,'player-vod-no1')
            
            if episode==1:
                intro_html=element.get_attribute('outerHTML')
                anime_name=parse_html(intro_html,'"javascript:">(.*?)</a>')
                episode_num=parse_html(intro_html,'px">(.*?)</p>')
                anime_intro=parse_html(intro_html,'"card-text">(.*?)</div>')
                redis.hset(f'七月新番:{anime_name}:动漫信息',mapping={'集数':episode_num,'简介':anime_intro})

            ## 下面获取video链接
            element=browser_wait(browser,By.ID,'playleft')
            html=element.get_attribute('outerHTML')
            regex3='<iframe width=.*? src="(.*?)" frameborder'
            video_url=parse_html(html,regex3)
                ## 获取video页面
            browser.get(video_url)
            element=browser_wait(browser,By.TAG_NAME,'video')
            html=element.get_attribute('outerHTML')
            regex4='<video width.*? src="(.*?)" autoplay'
            video=parse_html(html,regex4)
            redis.hset(f'七月新番:{anime_name}:视频链接',mapping={f'第{episode}集':video})

if __name__=='__main__':
    try:
        pool=multiprocessing.Pool()
        weekdays=range(1,8)
        pool.map(main,weekdays)
        pool.close()
        pool.join()
    except Exception as e:
        logger.error(f'Error in multiprocessing: {e}')