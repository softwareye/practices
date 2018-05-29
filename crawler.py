import aiohttp
import asyncio
import aiofiles
import os
import logging
import copy
import time
#  from urllib.parse import urljoin
from yarl import URL
from lxml import etree

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(filename)s] %(levelname)s: %(message)s'
)
log = logging.getLogger(__name__)


class Crawler(object):
    def __init__(self, root, *, max_tasks=10, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self._root = URL(root)
        self._q = asyncio.LifoQueue(loop=self._loop)
        self._max_tasks = max_tasks
        self._session = aiohttp.ClientSession(loop=self._loop)
        self._fetched_url_num = 0

    async def run(self):
        log.info('Start crawling page tasks')
        t0 = time.time()
        self._q.put_nowait((self._root, {}, self.parse_novel))
        tasks = [asyncio.Task(self.worker(), loop=self._loop)
                 for _ in range(self._max_tasks)]
        await self._q.join()
        for task in tasks:
            task.cancel()
        t1 = time.time()
        log.info('Tasks completed,crawled {0:d} pages,\
             using {1:.2f} seconds'.format(self._fetched_url_num, t1-t0))

    async def worker(self):
        try:
            while True:
                url, meta, callback = await self._q.get()
                assert callable(callback)
                if url:
                    await self.crawl(url, callback, meta)
                else:
                    await callback(meta)
                self._q.task_done()
        except asyncio.CancelledError:
            pass

    async def crawl(self, url, callback, meta):
        try:
            async with self._session.get(url) as resp:
                if resp.status == 200:
                    await callback(resp, meta)
                    log.debug(f'Crawing {url}')
                    self._fetched_url_num += 1
        except aiohttp.ClientError:
            log.error(f'Crawling {url} got a error')

    async def parse_novel(self, resp, meta):
        html = etree.HTML(await resp.read())
        base = resp.url
        for tr in html.xpath('//dl[@id="content"]//tr[position()>1]'):
            novel_name = tr.xpath('td[1]/a/text()')[0]
            url = base.join(URL(tr.xpath('td[2]/a/@href')[0]))
            _meta = copy.copy(dict(meta))
            _meta.update({'novel_name': novel_name})
            callback = self.parse_chapter
            self._q.put_nowait((url, _meta, callback))
        #  links = html.xpath(
            #  '//div[@id="pagelink"]/a[@class="next"]/@href'
        #  )
        #  if links:
            #  next_page = base.join(URL(links[0]))
            #  callback = self.parse_novel
            #  self._q.put_nowait((next_page, {}, callback))

    async def parse_chapter(self, resp, meta):
        html = etree.HTML(await resp.read())
        base = resp.url
        for link in html.xpath('//table[@id="at"]//a'):
            chapter_name = link.text
            url = base.join(URL(link.get('href')))
            _meta = copy.copy(dict(meta))
            _meta.update({'chapter_name': chapter_name})
            callback = self.parse_content
            self._q.put_nowait((url, _meta, callback))

    async def parse_content(self, resp, meta):
        html = etree.HTML(await resp.read())
        chapter_content = html.xpath('//dd[@id="contents"]//text()')
        meta = dict(meta)
        meta.update({'chapter_content': chapter_content})
        callback = self.save_novel
        self._q.put_nowait((None, meta, callback))

    async def save_novel(self, meta):
        meta = dict(meta)
        novel_name = meta['novel_name']
        chapter_name = meta['chapter_name']
        chapter_content = meta['chapter_content']
        novel_path = os.path.join(os.environ['HOME'], '顶点小说', novel_name)
        os.makedirs(novel_path, exist_ok=True)
        novel_file = os.path.join(novel_path, f"{chapter_name}.txt")
        logging.debug(f'Start saving novel {novel_name}--{chapter_name}')
        try:
            async with aiofiles.open(novel_file, 'w') as file:
                await file.writelines(chapter_content)
        except OSError:
            log.error('Saving novel got error')

    async def close(self):
        await self._session.close()


def main():
    root_url = 'http://www.23us.so/full.html'
    #  import uvloop
    #  asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.get_event_loop()
    c = Crawler(root_url, loop=loop)
    try:
        loop.run_until_complete(c.run())
    except KeyboardInterrupt:
        log.info('Crawler stopped by Ctrl-C')
        for task in asyncio.Task.all_tasks():
            task.cancel()
    finally:
        loop.run_until_complete(c.close())
        loop.close()


if __name__ == '__main__':
    main()
