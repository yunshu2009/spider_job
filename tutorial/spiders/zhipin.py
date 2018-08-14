import scrapy
from tutorial.items import TutorialItem
from scrapy.http import Request
from scrapy.selector import Selector
import  json
import  time
import  random
import redis
from scrapy.conf import settings

# zhipin 爬虫
class ZhipinSpider(scrapy.Spider):

    name = "boss"
    allowed_domains = ["www.zhipin.com"]

    boss_config = settings.get('BOSS_SPIDER_CONFIG')
    current_page = boss_config['min_page'] #开始页码
    max_page = boss_config['max_page'] #最大页码
    start_urls = [
        "https://www.zhipin.com/mobile/jobs.json?city={city}&query={query}".format(city=boss_config['city'], query=boss_config['query']),
    ]
    custom_settings = {
        "ITEM_PIPELINES":{
            'tutorial.pipelines.ZhipinPipeline': 300,
        },
        "DOWNLOADER_MIDDLEWARES":{
            'tutorial.middlewares.ZhipinMiddleware': 299,
         #   'tutorial.middlewares.ProxyMiddleware':301
        },
        "DEFAULT_REQUEST_HEADERS":{
            'Accept': 'application/json',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'User-Agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
            'Referer':'https://www.zhipin.com',
            'X-Requested-With':"XMLHttpRequest",
            "cookie":settings.get('BOSS_COOKIE')
        }
    }
    def parse(self, response):
        js = json.loads(response.body)
        html = js['html']

        q = Selector(text=html)


        items = q.css(".item")

        host = 'https://www.zhipin.com'
        x = 1
        for item in items:
            url = host + item.xpath('//a/@href').extract_first()

            position_name = item.css('h4::text').extract_first() #职位名称
            salary = item.css('.salary::text').extract_first() or  '' #薪资
            work_year = item.css('.msg em:nth-child(2)::text').extract_first() or '不限' #工作年限
            educational = item.css('.msg em:nth-child(3)::text').extract_first() #教育程度
            meta = {
                "position_name":position_name,
                "salary":salary,
                "work_year":work_year,
                "educational":educational
            }

            time.sleep(int(random.uniform(50, 70)))
            #初始化redis
            pool= redis.ConnectionPool(host='localhost',port=6379,decode_responses=True)
            r=redis.Redis(connection_pool=pool)
            key = settings.get('REDIS_POSITION_KEY')
            position_id = url.split("/")[-1].split('.')[0]
            if (r.sadd(key,position_id)) == 1:
                yield Request(url,callback=self.parse_item,meta=meta)

        if self.current_page < self.max_page:
            self.current_page += 1
            api_url = "https://www.zhipin.com/mobile/jobs.json?city={city}&query={query}&page={page}".format(city=self.boss_config['city'], query=self.boss_config['query'], page=self.current_page)
            time.sleep(int(random.uniform(50, 70)))
            yield  Request(api_url,callback=self.parse)
        pass

    def parse_item(self,response):
        item = TutorialItem()
        q = response.css
        item['address'] = q('.location-address::text').extract_first()
        item['create_time'] = q('.job-tags .time::text').extract_first()
        item['body'] = q('.text').xpath('string(.)').extract_first()
        item['company_name']  = q('.business-info h4::text').extract_first()
        item['postion_id'] = response.url.split("/")[-1].split('.')[0]
        item = dict(item, **response.meta )
        yield  item
