'''
这是一个从cycanime.com动漫网站上主页的“新番就要追着看的”的“更多”页面上搜集新番信息的爬虫
他会从https://cycanime.com/label/weekday.html 页面从周一的番剧开始爬取一周的所有番剧的信息
具体包括番名，剧情简介，更新至第几集，每集的原视频链接。
这些信息会被存储到Redis db中，使用本地服务器的默认6379端口。
但是番剧会更新，每周（甚至每天）都必须将更新至第几集以及更新的集数的链接更新
因此此爬虫可以作为获取当前新番的初始化模块，只需在新番出来时执行依次（也就是1、4、7、10）月开始时。
'''

from cycanimescrape import *
import multiprocessing

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
        ## 如果当前动漫未放送
        if episodes_url_append==[]:
            anime_name_re='<h3 class="slide-info-title hide">(.*?)</h3>'
            anime_name=parse_html(resp.text,anime_name_re)
            anime_intro_re='简介：</em>(.*?)</li>'
            anime_intro=parse_html(resp.text,anime_intro_re)
            redis.hset(f'七月新番:{anime_name}:动漫信息',mapping={'简介':anime_intro,'集数':'即将放送'})
            logger.info(f'{anime_name}即将放送')
        else:
            ## 如果动画已放送，则遍历此动漫的所有集数的播放页
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