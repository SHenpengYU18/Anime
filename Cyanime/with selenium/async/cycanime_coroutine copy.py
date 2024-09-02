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
import aiohttp,asyncio
import json
import logging
import time
import requests
import multiprocessing
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL='https://cycanime.com'
USER_AGENT='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'

## 把日志输出到当前文件夹的文件中，名称为所执行的py文件的文件名
filepath = __file__
filename_with_extension = os.path.basename(filepath)
filename_no_extension = os.path.splitext(filename_with_extension)[0]


logging.basicConfig(filename=f'd:/_code/python/scraper/log/{filename_no_extension}.log',  # 日志文件名
                    level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

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

async def request_get(url,session,headers=None):
    '''request the webpage with certain url'''
    try:
        response=await session.get(url,headers=headers)
    except(ConnectionError):
        logger.error(f'ConnectionError in requesting {url}')
    else:
        regex2='<a class="hide" href="(.*?)">'
        episodes_url_append=parse_html(await response.text(),regex2,ismany=True)
        return episodes_url_append

def browser_init():
    '''initialize the browser object'''
    options=webdriver.ChromeOptions()
    options.add_argument('--headless')
    return webdriver.Chrome(options=options)

async def anime_main(weekday):

    browser=browser_init()
    browser.get(BASE_URL+'/label/weekday.html')
    class_name=f'week-key{weekday}'
    element=browser_wait(browser,By.CLASS_NAME,class_name)
    element.click()
    browser_wait(browser, By.CSS_SELECTOR, f'#week-list{weekday} .lazy',ismany=True)
    ele2=browser_wait(browser, By.CSS_SELECTOR, f'#week-list{weekday} .public-list-exp',ismany=True)
    html='\n'.join([ele2[weekday].get_attribute('outerHTML') for weekday in range(len(ele2))])
    regex='href="(.*?)"'
    intro_page_urls_append=parse_html(html,regex,ismany=True)

    ## 遍历周页（weekday）中的每个动漫的介绍页
    headers=headers = {'User-Agent': USER_AGENT}

    async with aiohttp.ClientSession() as session:
        intro_page_parse_tasks=[asyncio.create_task(
            request_get(BASE_URL+intro_page_url_append,session,headers) 
            ) for intro_page_url_append in intro_page_urls_append]
        resp_of_episodes=await asyncio.gather(*intro_page_parse_tasks)

    # print(resp_of_episodes[1])
    for episodes_url_append in resp_of_episodes:
        ## 遍历此动漫的所有集数的播放页
        anime_name=''
        for episode in range(1,len(episodes_url_append)):
        # for episode in range(1,2):
            episode_url=BASE_URL+episodes_url_append[episode]
            browser.get(episode_url)
            element=browser_wait(browser,By.CLASS_NAME,'player-vod-no1')
            
            if episode==1:
                intro_html=element.get_attribute('outerHTML')
                anime_name=parse_html(intro_html,'"javascript:">(.*?)</a>')
                episode_num=parse_html(intro_html,'px">(.*?)</p>')
                anime_intro=parse_html(intro_html,'"card-text">(.*?)</div>')
                anime_info={
                    '名称':anime_name,
                    '集数':episode_num,
                    '介绍':anime_intro
                }
                filename=f'D:/_code/python/scraper/scrape_results/{anime_name}_info_corountine_multipro'
                with open(file=filename,mode='a',encoding='utf-8') as f:
                    json.dump(anime_info,f,ensure_ascii=False,indent=2)

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
            video_info={f'第{episode}集视频链接':video}
            with open(file=filename,mode='a',encoding='utf-8') as f:
                    json.dump(video_info,f,ensure_ascii=False,indent=2)

def run_async_in_multiprocessing(weekday):
    return asyncio.run(anime_main(weekday))

if __name__=='__main__':
    try:
        start=time.time()
        pool=multiprocessing.Pool()
        weekdays=range(1,8)
        pool.map(run_async_in_multiprocessing,weekdays)
        pool.close()
        pool.join()
        end=time.time()
        logger.info('Time used:%s',round(end-start,3))
    except Exception as e:
        logger.error(f'Error in multiprocessing: {e}')