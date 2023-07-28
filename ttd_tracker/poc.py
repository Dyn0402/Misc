#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on July 27 8:36 PM 2023
Created in PyCharm
Created as Misc/poc.py

@author: Dylan Neff, Dylan
"""

import numpy as np
import matplotlib.pyplot as plt
from time import sleep
from datetime import datetime
# from pyinput.keyboard import Key, Listener

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import WebDriverException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from WAMessengerttd import WAMessengerttd


def main():
    # selenium_test()
    simple_full_test()
    print('donzo')


def selenium_test():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f'--start-maximized')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(1)
    driver.get('https://ttp.dhs.gov/schedulerui/schedule-interview/location?lang=en&vo=true&returnUrl=ttp-external'
               '&service=up')

    sleep(2)

    '//*[@id="centerDetailsUS160"]'  # Erlanger
    '//*[@id="centerDetailsUS40"]'  # Denver
    '//*[@id="centerDetailsUS332"]'  # Dayton

    '//*[@id="centerDetailsUS83"]'  # Miami
    '//*[@id="btnChooseLocation"]'  # Choose Location Button

    '//*[@id="popoverUS160"]/div/div/div'  # Next appointment big box
    '//*[@id="popoverUS160"]/div/div/div/strong'

    '//*[@id="popoverUS83"]/div/div/div[1]/span'  # Date box
    '//*[@id="monthSpan"]'
    '//*[@id="popoverUS83"]/div/div/div[1]/span/text()'

    loc_code_dict = {'Erlanger': 160, 'Denver': 40, 'Dayton': 332, 'Miami': 83}

    driver.find_element(By.XPATH, '//*[@id="centerDetailsUS160"]').click()
    sleep(3)
    print(driver.find_element(By.XPATH, '//*[@id="popoverUS160"]/div/div/div/strong').text)

    sleep(2)

    driver.find_element(By.XPATH, '//*[@id="centerDetailsUS83"]').click()
    sleep(3)
    print(driver.find_element(By.XPATH, '//*[@id="popoverUS83"]/div/div/div/strong').text)
    print(driver.find_element(By.XPATH, '//*[@id="popoverUS83"]/div/div/div[1]/span').text)

    sleep(5)


def simple_full_test():
    messenger = WAMessengerttd()

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f'--start-maximized')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(1)
    driver.get('https://ttp.dhs.gov/schedulerui/schedule-interview/location?lang=en&vo=true&returnUrl=ttp-external'
               '&service=up')

    sleep(2)

    loc_date_dict = {'Erlanger': 'December 20, 2023', 'Denver': 'December 20, 2023', 'Dayton': 'October 12, 2023',
                     'Miami': 'October 12, 2023'}
    loc_date_dict = {loc: datetime.strptime(x, '%B %d, %Y') for loc, x in loc_date_dict.items()}
    loc_code_dict = {'Erlanger': 160, 'Denver': 40, 'Dayton': 332, 'Miami': 83}
    locs = ['Erlanger', 'Denver', 'Dayton']

    recycle_wait = 60  # s

    i = 0
    while True:
        print(i)
        for loc in locs:
            code = loc_code_dict[loc]
            driver.find_element(By.XPATH, f'//*[@id="centerDetailsUS{code}"]').click()  # Click location
            sleep(2)
            available = driver.find_element(By.XPATH, f'//*[@id="popoverUS{code}"]/div/div/div/strong').text

            log_text = [loc]
            if 'Next Available Appointment' == available:
                date_available = driver.find_element(By.XPATH, f'//*[@id="popoverUS{code}"]/div/div/div[1]/span').text
                date_available = datetime.strptime(date_available, '%B %d, %Y')
                log_text.append(f'Available! {date_available}')
                if date_available < loc_date_dict[loc]:
                    log_text.append('Available in time!')
                    messenger.send_message(f'{loc} {date_available}', receive_name='dylan')
                else:
                    log_text.append('Available too late')
            else:
                log_text.append('Not available')
            print('  '.join(log_text))
            sleep(2)
        i += 1
        print()
        sleep(recycle_wait)


if __name__ == '__main__':
    main()
