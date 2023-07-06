#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on July 05 1:45 PM 2023
Created in PyCharm
Created as Misc/vsf_global_selenium_test

@author: Dylan Neff, Dylan
"""

import numpy as np
import matplotlib.pyplot as plt
from time import sleep
# from pyinput.keyboard import Key, Listener

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import WebDriverException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from VisaTracker import VisaTracker
from WAMessenger import WAMessenger


def main():
    test_wa_messenger('Testing for visa tracker')
    # test_vfs_selenium()
    # visatracker_test()
    print('donzo')


def visatracker_test():
    tracker = VisaTracker()
    tracker.start_new_booking()
    tracker.check_appointment()


def test_wa_messenger(message):
    messenger = WAMessenger()
    res = messenger.send_message(message)


def test_vfs_selenium():
    uname = 'Dyn0402@hotmail.com'
    pword = 'JXMG9$jw*D5#k$U'

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f'--start-maximized')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get('https://visa.vfsglobal.com/usa/en/fra/login')
    driver.implicitly_wait(10)
    # sleep(15)
    # frame = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, 'iframe')))
    # loading = True
    # while loading:
    #     try:
    #         driver.find_element(By.XPATH, '//*[@id="mat-input-0"]').send_keys(uname)
    #         loading = False
    #     except NoSuchElementException:
    #         print('Still loading')
    #         sleep(1)
    sleep(1)
    driver.find_element(By.XPATH, '//*[@id="mat-input-0"]').send_keys(uname)
    sleep(1)
    driver.find_element(By.XPATH, '//*[@id="mat-input-1"]').send_keys(pword)
    # captcha_frame = driver.find_element(By.XPATH, '//*[@id="rc-anchor-container"]')
    # captcha_frame = driver.find_element(By.XPATH, '/html/body/div[2]/div[3]')
    # driver.switch_to.frame(captcha_frame)
    driver.switch_to.frame(driver.find_element(By.CSS_SELECTOR, 'iframe[title="reCAPTCHA"]'))
    sleep(1)
    captcha_button = driver.find_element(By.XPATH, '//*[@id="recaptcha-anchor"]')

    # wait = WebDriverWait(driver, 120)
    # wait.until(EC.element_to_be_clickable())

    clicked = False
    while not clicked:
        try:
            captcha_button.click()
            clicked = True
        except StaleElementReferenceException:
            print('captcha button stale, trying again')
            sleep(1)
    # driver.switch_to.default_content()
    solving = True
    while solving:
        print('Looks like solving, waiting till finished...')
        sleep(3)
        checked = captcha_button.get_attribute('aria-checked')
        print(f'checked {checked}')
        solving = True if checked == 'false' else False
        print(f'solving {solving}')
    print('Looks like reCAPTCHA was solved. Continuing autonomously from here.')
        # try:
        #     # driver.find_element(By.CSS_SELECTOR, 'iframe[title="recaptcha challenge expires in two minutes"]')
        #     # driver.find_element(By.CSS_SELECTOR, 'iframe[title="recaptcha challenge expires in two minutes"]')
        #     print('Looks like still solving, waiting till finished...')
        #     sleep(3)
        # except NoSuchElementException:
        #     print('Looks like reCAPTCHA was solved. Continuing autonomously from here.')
        #     solving = False
    # with Listener(on_press=on_press) as listener:
    #     listener.join()
    # sleep(45)
    driver.switch_to.default_content()
    # driver.find_element(By.XPATH, '/html/body/div[2]/div[3]')
    driver.find_element(By.XPATH, '/html/body/app-root/div/app-login/section/div/div/mat-card/form/button').click()
    # sleep(45)

    # Start new booking
    # sleep(5)
    # book_button = driver.find_element(By.XPATH, '/html/body/app-root/div/app-dashboard/section[1]/div/div[2]/button')
    loader_xpath = '/html/body/app-root/ngx-ui-loader'
    WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.XPATH, loader_xpath)))
    book_xpath = '/html/body/app-root/div/app-dashboard/section[1]/div/div[2]/button'
    book_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, book_xpath)))
    book_button.click()

    # Select Center
    # sleep(5)
    WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.XPATH, loader_xpath)))
    center_dropdown_xpath = '//*[@id="mat-select-0"]'
    center_dropdown_ele = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, center_dropdown_xpath)))
    center_dropdown_ele.click()
    option_text = "France Visa Application Center-Los Angeles"
    option_locator = f'//mat-option/span[contains(text(),"{option_text}")]'
    option_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, option_locator)))
    option_element.click()
    # center_dropdown_obj = Select(center_dropdown_ele)
    # center_dropdown_obj.select_by_visible_text('France Visa Application Center-Los Angeles')

    # Select Category
    # sleep(5)
    WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.XPATH, loader_xpath)))
    cat_dropdown_xpath = '//*[@id="mat-select-2"]'
    cat_dropdown_ele = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, cat_dropdown_xpath)))
    cat_dropdown_ele.click()
    # cat_dropdown_ele = driver.find_element(By.XPATH, '//*[@id="mat-select-2"]')
    # cat_dropdown_ele.click()
    option_text = "Long Stay (> 90 days)"
    option_locator = f'//mat-option/span[contains(text(),"{option_text}")]'
    option_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, option_locator)))
    option_element.click()

    # Select Sub-Category
    # sleep(5)
    WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.XPATH, loader_xpath)))
    scat_dropdown_xpath = '//*[@id="mat-select-4"]'
    scat_dropdown_ele = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, scat_dropdown_xpath)))
    scat_dropdown_ele.click()
    # scat_dropdown_ele = driver.find_element(By.XPATH, '//*[@id="mat-select-4"]')
    # scat_dropdown_ele.click()
    option_text = "Long Stay - Any other visa category"
    option_locator = f'//mat-option/span[contains(text(),"{option_text}")]'
    option_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, option_locator)))
    option_element.click()

    # sleep(5)
    WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.XPATH, loader_xpath)))
    result_xpath = '/html/body/app-root/div/app-eligibility-criteria/section/form/mat-card[1]/form/div[4]/div'
    result_text = driver.find_element(By.XPATH, result_xpath).text
    print(result_text)
    no_appointments_text = 'We are sorry but no appointment slots are currently available. ' \
                           'New slots open at regular intervals, please try again later'
    if result_text == no_appointments_text:
        print('No appointments')
    else:
        print('Appointments available')

    driver.close()


if __name__ == '__main__':
    main()
