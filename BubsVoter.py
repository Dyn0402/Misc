#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on March 30 1:42 PM 2020
Created in PyCharm
Created as Misc/BubsVoter.py

@author: Dylan Neff, dylan
"""

from time import sleep
from selenium import webdriver
import datetime as dt
import platform


class BubsVoter:
    # Attributes
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('disable-infobars')
    exe_path = ''
    page_url = 'https://www.cincinnatimagazine.com/pizzamadness/'
    imp_wait_time = 10
    name_pre = 'gary'
    email_suf = '@gmail.com'
    driver = None

    def __init__(self, path=''):
        self.mins_id = gen_id()
        if path != '':
            self.exe_path = path
        if platform.system().lower() == 'windows':
            self.exe_path = 'chromedriver/chromedriver_win.exe'
        elif platform.system().lower() == 'linux':
            self.exe_path = 'chromedriver/chromedriver_lin'

    def vote(self):
        self.start_driver()
        self.get_page()
        self.switch_to_iframe()
        self.vote_bubs()
        self.make_account()
        self.close_driver()

    def start_driver(self):
        self.driver = webdriver.Chrome(self.exe_path)
        self.driver.implicitly_wait(self.imp_wait_time)

    def close_driver(self):
        sleep(self.imp_wait_time)
        self.driver.quit()

    def get_page(self):
        self.driver.get(self.page_url)

    def switch_to_iframe(self):
        iframe_xpath = "//iframe[@id='iFrameResizer0']"
        iframe = self.get_element(iframe_xpath, 'Iframe')
        if iframe is not None:
            self.driver.switch_to.frame(iframe)

    def vote_bubs(self):
        bubs_button_xpath = "//html//body//div[1]//div[1]//div[7]//div[1]//div[2]//div//div[4]//form[2]//div[1]//" \
                            "div[2]//div[1]//div[2]//div[7]//div//div[2]//button"
        bubs_button = self.get_element(bubs_button_xpath, 'Bubs Button')
        if bubs_button is not None:
            bubs_button.click()

    def make_account(self):
        self.fill_uid()
        self.fill_email()
        self.fill_pass()
        self.submit_account()

    def fill_uid(self):
        uid_xpath = '//*[@id="register-username"]'
        uid = self.name_pre + str(self.mins_id)
        uid_input = self.get_element(uid_xpath, 'User Id Input')
        if uid_input is not None:
            uid_input.clear()
            uid_input.send_keys(uid)

    def fill_email(self):
        email_xpath = '//*[@id="register-email"]'
        email = self.name_pre + str(self.mins_id) + self.email_suf
        email_input = self.get_element(email_xpath, 'Email Input')
        if email_input is not None:
            email_input.clear()
            email_input.send_keys(email)

    def fill_pass(self):
        pass_xpath = '//*[@id="register-password"]'
        pwrd = 4*self.name_pre
        pwrd_input = self.get_element(pass_xpath, 'Password Input')
        if pwrd_input is not None:
            pwrd_input.clear()
            pwrd_input.send_keys(pwrd)

    def submit_account(self):
        submit_xpath = "//html//body//div[1]//div[1]//div[7]//div[1]//div[3]//form//div[6]//div//div[2]//button"
        submit_button = self.get_element(submit_xpath, 'Submit Button')
        if submit_button is not None:
            submit_button.click()

    def get_element(self, xpath, name='element'):
        ele = self.driver.find_elements_by_xpath(xpath)
        if len(ele) < 1:
            print(f'{name} not found')
            return None
        else:
            if len(ele) > 1:
                print(f'{len(ele)} {name}s found, using the first.')
            return ele[0]


def gen_id():
    epoch = dt.datetime(2020, 3, 29, 23, 59, 59)
    now = dt.datetime.now()
    seconds = (now - epoch).total_seconds()
    unique_id = int(seconds/60)*100 + int(seconds) % 60

    return unique_id
