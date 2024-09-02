'''
此模块用于更新番剧，会获取所有新番最近更新的集数，和对应的视频链接
'''

import datetime
from cycanimescrape import *


def main_update():
    current_datetime=datetime.datetime.now()
    weekday=current_datetime.weekday()+1

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
        if episodes_url_append==[]:## 如果当前动漫未更新
            anime_name_re='<h3 class="slide-info-title hide">(.*?)</h3>'
            anime_name=parse_html(resp.text,anime_name_re)
            anime_intro_re='简介：</em>(.*?)</li>'
            anime_intro=parse_html(resp.text,anime_intro_re)
            redis.hset(f'七月新番:{anime_name}:动漫信息',mapping={'简介':anime_intro,'集数':'即将放送'})
            logger.info(f'{anime_name}即将放送')
            
        else:
            ## 遍历此动漫的新更新集数的播放页
            episode=len(episodes_url_append)
            episode_url=BASE_URL+episodes_url_append[episode-1]
            browser.get(episode_url)
            element=browser_wait(browser,By.CLASS_NAME,'player-vod-no1')
            ## 更新集数信息
            intro_html=element.get_attribute('outerHTML')
            anime_name=parse_html(intro_html,'"javascript:">(.*?)</a>')
            episode_num=parse_html(intro_html,'px">(.*?)</p>')
            hashname=f'七月新番:{anime_name}:动漫信息'
            old_episode_num=redis.hget(hashname,'集数')
            if episode_num!=old_episode_num:
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
                if episode_num==None:
                    redis.hset(hashname,mapping={'集数':'已完结'})
                    redis.hset(f'七月新番:{anime_name}:视频链接',mapping={f'第{episode}集':video})
                    logger.info(f'{anime_name}已完结')
                else:
                    redis.hset(hashname,mapping={'集数':episode_num})
                    redis.hset(f'七月新番:{anime_name}:视频链接',mapping={f'第{episode}集':video})
                    logger.info(f'{anime_name}{episode_num}')
            else:
                logger.info(f'周{weekday}番剧{anime_name}未更新')

if __name__=='__main__':
    main_update()



