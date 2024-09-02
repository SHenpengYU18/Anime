'''
此模块使用playwright包对cyanime.com中的动漫进行异步爬取
爬取过程为: 周页（7页）->动漫详情页->动漫播放页->视频链接页
'''

import re
import time
import json
import asyncio
import multiprocessing
from urllib.parse import urljoin
from playwright.async_api import async_playwright

BASE_URL='https://cycanime.com'
ANIME_QUEUE=[]

async def anime_video(anime_info:dict,browser):
    video_resps={}
    if anime_info.get('动漫集数'):
        for i in range(1,anime_info.get('动漫集数')+1):
            try:
                video_link=await video_links(urljoin(BASE_URL,f'/watch/{anime_info.get('动漫ID')}/1/{i}.html'),browser)
            except Exception as e:
                print(f'获取视频链接出错: {e}')
            else:
                video_resps[f'第{i}集']=video_link
    else:
        print(f'{anime_info.get('番名')}未开播或已完结')
    anime_info['视频链接']=video_resps
    return anime_info

def on_response_video(video_link_container):
    async def video_link_get(response):
        if 'video/mp4' in response.headers.get('content-type'):
            # print(response.status)
            video_link_container.append(response.url)
    return video_link_get

async def video_links(watch_episode_url,browser):
    video_link_container=[]
    try:
        page=await browser.new_page()
        page.on('response',on_response_video(video_link_container))
        await page.goto(watch_episode_url)
        await page.wait_for_load_state('load')
    except Exception as e:
        print(f'打开视频页面出错: {e}')
    return video_link_container[0]
    
async def handle_json(json_data):
    anime_num=json_data.get('total')
    for anime in json_data.get('list'):
        anime_id=anime.get('vod_id')
        anime_name=anime.get('vod_name')
        anime_pic=anime.get('vod_pic')
        anime_class=anime.get('vod_class')
        anime_remark=anime.get('vod_remarks')
        anime_episode=re.search(r"\d+",anime_remark).group() if re.search(r"\d+",anime_remark) else None
        anime_episode=int(anime_episode) if anime_episode else None
        anime_blurb=anime.get('vod_blurb')
        anime_info={
            '番名':anime_name,
            '动漫ID':anime_id,
            '宣传图像':anime_pic,
            '番剧类别':anime_class,
            '动漫集数':anime_episode,
            '剧情简介':anime_blurb
        }
        ANIME_QUEUE.append(anime_info)

async def handle_response(response):
    if 'api' in response.url and response.status==200:
        try:
            json_data= await response.json()
            try:
                await handle_json(json_data)
            except Exception as e:
                print(f'JSON数据处理出错:{e}')
        except Exception as e:
            print(f'监听响应JSON数据出错:{e}')

async def anime_main(weekday):
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        page=await browser.new_page()
        
        page.on('response',handle_response)
        await page.goto(urljoin(BASE_URL,'/label/weekday.html'))

        await page.click(f'a.week-key{weekday}')
        await page.wait_for_load_state('load')
        time.sleep(0.5)
        # await page.click('a.week-key2')
        # await page.wait_for_load_state('networkidle')

        tasks=[asyncio.create_task(anime_video(anime_info,browser)) for anime_info in ANIME_QUEUE]
        tasks_ret=await asyncio.gather(*tasks)
        with open('task_res','a',encoding='utf-8') as f:
            for res in tasks_ret:
                json.dump(res,f,ensure_ascii=False,indent=2)
        
def run_async_muiltiprocessing(weekday):
    asyncio.run(anime_main(weekday))

if __name__=='__main__':
    s=time.time()
    try:
        with multiprocessing.Pool() as pool:
            weekdays=range(1,8)
            pool.map(run_async_muiltiprocessing,weekdays)
    except Exception as e:
        print('多进程出错: {e}')
    e=time.time()
    print('所用时间:',round(e-s,3))