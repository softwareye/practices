# -*- coding=utf-8 -*-

import re
import time
from selenium import webdriver
from collections import namedtuple
from itertools import chain

Lecture = namedtuple(
    'Lecture',
    ['platform','name','teacher','all_time','learned_time','url']
)


class Masgb(object):
    def __init__(self):
        options=webdriver.ChromeOptions()
        options.set_headless()
        self.browser=webdriver.Chrome(chrome_options=options)
        self.login_url='http://www.masgb.gov.cn/masgbjy/login.aspx'
        self.main_url='http://www.masgb.gov.cn/masgbjy/Default.aspx'
        self.mas_lec_url='http://www.masgb.gov.cn/masgbjy/Train/Elective.aspx'
        self.ah_url='http://lms.ahgbjy.gov.cn/LMS/'
        self.user='34022119820513385X'
        self.passwd='6740169'
        self.logined = False

    @staticmethod
    def __text2time(text):
        text=text.strip()
        if re.match(r'^\d+$',text):
            return int(text)
        m=re.match(r'^(\d+)分钟',text)
        if m:
            return int(m.group(1))
        m=re.match(r'^(\d+)小时$',text)
        if m:
            return int(m.group(1))
        m=re.match(r'^(\d+)小时(\d+)分钟',text)
        if m:
            return int(m.group(1))*60+int(m.group(2))
        return 0

    @staticmethod
    def __resolve_url(elem,platform='MAS'):
        if platform=='MAS':
            patt=r"window\.open\('([^']+)'"
            attr=elem.get_attribute('onclick')
            m=re.match(patt,attr)
            if m:
                return f'http://www.masgb.gov.cn/masgbjy/Train/{m.group(1)}'
        elif platform=='AH':
            patt=r"javascript:openCourse\('([^']+)','([^']+)'\);"
            attr=elem.get_attribute('href')
            m=re.match(patt,attr)
            if m:
                return f'http://static.ahgbjy.gov.cn/LMS/CoursePlayer1.aspx?bcid={m.group(1)}&cid={m.group(2)}'
        return ''

    def login(self):
        browser=self.browser
        browser.get(self.login_url)
        user_field=browser.find_element_by_id('p_UserName')
        user_field.send_keys(self.user)
        pass_field=browser.find_element_by_id('p_Pwd')
        pass_field.send_keys(self.passwd)
        login_btn=browser.find_element_by_xpath("//div[@class='btnareas']/a")
        login_btn.click()
        if browser.current_url==self.main_url:
            print(f'[+]User {self.user} login successfully!')
            self.logined = True
        else:
            print(f'[-]User {self.user} login failed!')
            self.logined = False

    def mas_lecs(self):
        assert self.logined
        browser=self.browser
        browser.get(self.mas_lec_url)
        rows=browser.find_elements_by_xpath("//table[@class='listtable']/tbody/tr")
        for row in rows[2:]:
            tds=row.find_elements_by_tag_name('td')
            name=tds[0].text.strip()
            teacher=tds[1].text.strip()
            all_time=self.__text2time(tds[3].text)
            learned_time=self.__text2time(tds[4].text)
            url=self.__resolve_url(tds[7].find_element_by_tag_name('input'))
            if learned_time < all_time:
                yield Lecture('MAS',name,teacher,all_time,learned_time,url)

    def ah_lecs(self):
        assert self.logined
        browser=self.browser
        browser.get(self.main_url)
        browser.find_element_by_xpath(\
            "//div[child::text()='安徽干部教育在线平台']").click()
        handle=browser.window_handles[1]
        browser.switch_to.window(handle)
        browser.get(self.ah_url)
        links=[elem.get_attribute('href') for elem in browser.find_elements_by_xpath("//a[@style='color:Black;']")]
        for link in links:
            browser.get(link)
            trs=browser.find_elements_by_xpath("//table[@class='comments_on']/tbody/tr")
            for tr in trs[1:]:
                tds=tr.find_elements_by_tag_name('td')
                name=tds[1].text.strip()
                teacher='Unknown'
                all_time=self.__text2time(tds[2].text.strip())
                learned_time=self.__text2time(tds[4].text.strip())
                url=self.__resolve_url(tds[6].find_element_by_tag_name('a'),platform='AH')
                if learned_time < all_time:
                    yield Lecture('AH',name,teacher,all_time,learned_time,url)

    def learn(self):
        assert self.logined
        for lec in chain(self.mas_lecs(),self.ah_lecs()):
            self.__learn(lec, lec.platform)

    def __learn(self,lec,platform):
        if platform == 'MAS':
            self.__learn_mas_lec(lec)
        elif platform == 'AH':
            self._learn_ah_lec(lec)

    def __learn_mas_lec(self,lec):
        browser=self.browser
        print(f"[*]{lec.name}({lec.teacher})...",end='',flush=True)
        browser.get(lec.url)
        browser.find_element_by_id(
            'GridView_Learning1_ctl02_Study'
        ).find_element_by_tag_name('a').click()
        browser.switch_to.window(browser.window_handles[-1])
        t=(lec.all_time-lec.learned_time)*60
        id=browser.find_element_by_id('txtLoginInfoId').get_attribute('value')
        browser.execute_script(
            f"document.getElementById('scSetTime').src='SetTime.ashx?LoginInfoId={id}&pTime={t}';"
        )
        print('done.')
        browser.close()
        browser.switch_to.window(browser.window_handles[-1])

    def __learn_ah_lec(self,lec):
        browser=self.browser
        print(f"[*]{lec.name}...",end='',flush=True)
        browser.execute_script(f'window.open("{lec.url}");')
        browser.switch_to.window(browser.window_handles[-1])
        browser.switch_to.frame('main')
        try:
            link=browser.find_element_by_class_name('c_learn')
            link.click()
        except Exception:
            pass
        browser.switch_to.default_content()
        t=(lec.all_time-lec.learned_time)*2
        for i in range(0,t):
            if browser.find_element_by_id('dialog').is_displayed():
                browser.find_element_by_xpath(
                    "//div[@id='dialog']/following-sibling::div[1]"
                ).click()
                time.sleep(30)
                print('done.')
                browser.close()
                browser.switch_to.window(browser.window_handles[-1])

    def quit(self):
        self.browser.quit()


def main():
    m=Masgb()
    try:
        m.login()
        m.learn()
    finally:
        m.quit()

if __name__=='__main__':
    main()
