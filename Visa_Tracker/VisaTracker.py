#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on July 05 4:31 PM 2023
Created in PyCharm
Created as Misc/VisaTracker

@author: Dylan Neff, Dylan
"""

from time import sleep

from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, \
    ElementClickInterceptedException
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from WAMessenger import WAMessenger


class VisaTracker:
    def __init__(self):
        self.uname = 'Dyn0402@hotmail.com'
        self.pword = 'JXMG9$jw*D5#k$U'
        self.driver = None
        self.wait_time_for_page_element = 10  # s Time to wait for element to appear
        self.loader_xpath = '/html/body/app-root/ngx-ui-loader'

        self.messenger = WAMessenger()

        self.start_driver()
        self.log_in()

    def __del__(self):
        self.close()

    def close(self):
        if self.driver is not None:
            self.driver.close()
            self.driver.quit()

    def start_driver(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(f'--start-maximized')
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(self.wait_time_for_page_element)

    def log_in(self):
        vfs_global_log_url = 'https://visa.vfsglobal.com/usa/en/fra/login'
        self.driver.get(vfs_global_log_url)

        self.driver.find_element(By.XPATH, '//*[@id="mat-input-0"]').send_keys(self.uname)
        self.driver.find_element(By.XPATH, '//*[@id="mat-input-1"]').send_keys(self.pword)

        self.solve_captcha()

        log_in_button_xpath = '/html/body/app-root/div/app-login/section/div/div/mat-card/form/button'
        self.driver.find_element(By.XPATH, log_in_button_xpath).click()

    def solve_captcha(self):
        """
        Open captcha and wait until solved before continuing
        :return:
        """
        sleep(1)
        self.driver.switch_to.frame(self.driver.find_element(By.CSS_SELECTOR, 'iframe[title="reCAPTCHA"]'))
        sleep(1)
        captcha_button = self.driver.find_element(By.XPATH, '//*[@id="recaptcha-anchor"]')

        clicked = False
        while not clicked:
            try:
                captcha_button.click()
                clicked = True
            except StaleElementReferenceException:
                print('captcha button stale, trying again')
                sleep(1)
        solving = True
        while solving:
            print('Looks like solving, waiting till finished...')
            sleep(3)
            checked = captcha_button.get_attribute('aria-checked')
            solving = True if checked == 'false' else False
        print('Appears reCAPTCHA was solved. Proceeding autonomously from here.')
        self.driver.switch_to.default_content()

    def start_new_booking(self):
        book_xpath = '/html/body/app-root/div/app-dashboard/section[1]/div/div[2]/button'
        self.click(book_xpath)

    def check_appointment(self):
        # Select Center
        center_dropdown_xpath = '//*[@id="mat-select-0"]'
        self.click(center_dropdown_xpath)
        center_option_text = "France Visa Application Center-Los Angeles"
        center_option_locator = f'//mat-option/span[contains(text(),"{center_option_text}")]'
        self.click(center_option_locator)

        # Select Category
        cat_dropdown_xpath = '//*[@id="mat-select-2"]'
        self.click(cat_dropdown_xpath)
        cat_option_text = "Long Stay (> 90 days)"
        cat_option_locator = f'//mat-option/span[contains(text(),"{cat_option_text}")]'
        self.click(cat_option_locator)

        # Select Sub-Category
        scat_dropdown_xpath = '//*[@id="mat-select-4"]'
        self.click(scat_dropdown_xpath)
        scat_option_text = "Long Stay - Any other visa category"
        scat_option_locator = f'//mat-option/span[contains(text(),"{scat_option_text}")]'
        self.click(scat_option_locator)

        # Read result
        sleep(3)
        result_xpath = '/html/body/app-root/div/app-eligibility-criteria/section/form/mat-card[1]/form/div[4]/div'
        result_element = self.driver.find_element(By.XPATH, result_xpath)
        result_text = result_element.text
        print(result_text)
        no_appointments_text = 'We are sorry but no appointment slots are currently available. ' \
                               'New slots open at regular intervals, please try again later'
        if result_text == no_appointments_text:
            print('No appointments')
            # self.messenger.send_message('No appointments')
        else:
            print('\n\n\nAppointments available! \nSending a message to Dylan.')
            self.messenger.send_message('Appointments available')

    def click(self, xpath):
        clicked = False
        while not clicked:
            try:
                button = self.driver.find_element(By.XPATH, xpath)
                button.click()
                clicked = True
            except (NoSuchElementException, ElementClickInterceptedException) as e:
                sleep(1)
