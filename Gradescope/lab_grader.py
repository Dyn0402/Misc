# -*- coding: utf-8 -*-
"""
Created on Tue Apr 03 13:54:50 2018

@author: Dyn04
"""


import pyautogui as pg
import time
from time import sleep

from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


def main():
    # pars = initialize()
    # grade(pars)
    selenium_test()
    print('donzo')


def selenium_test():
    wait_time_for_page_element = 1  # s
    window_width, window_height = 1200, 800  # Pixels
    uname, pword = read_credentials('C:/Users/Dylan/Desktop/Creds/gradescope_creds.txt')

    application_url = 'https://www.gradescope.com/login'
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f'--window-size={window_width},{window_height}')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(wait_time_for_page_element)
    driver.get(application_url)
    driver.find_element(By.XPATH, '//*[@id="session_email"]').send_keys(uname)
    driver.find_element(By.XPATH, '//*[@id="session_password"]').send_keys(pword)
    driver.find_element(By.XPATH, '/html/body/div[1]/main/div[2]/div/section/form/div[4]/input').click()

    while True:
        try:
            for rubric_number in rubric_numbers:
                rubric_xpath = f'//*[@id="main-content"]/div/main/div[3]/div[2]/' \
                               f'div/div[2]/div[1]/ol/li[{rubric_number}]/div/div/button'
                driver.find_element(By.XPATH, rubric_xpath).click()
            driver.find_element(By.XPATH,
                                '//*[@id="main-content"]/div/main/section/ul/li[5]/button/span/span/span').click()
        except NoSuchElementException:
            sleep(2)
            print(driver.find_element(By.XPATH, '//*[@id="main-content"]/div[2]/div/div').get_attribute('class'))
            break

    sleep(15)
    driver.close()
    driver.quit()

    
def initialize():
    submissions = [32, 28, 29]  # Number of submissions
    # submissions = [32, 30, 32]
    tabs = 3  # Number of lab sections and therefore browser tabs.
    # questions = [['1','2','3','4','5'],
    #             ['1','2','3','4','5']] #Key stokes for each question
    # questions = [['1', '4']]
    # questions = [['1']]
    questions = [['1'],
                 ['1'],
                 ['1'],
                 ['1'],
                 ['1'],
                 ['1'],
                 ['1'],
                 ['1'],
                 ['1']]
    wait_time = 0.6  # seconds to delay for next question/submission to load
    next_sub = 'z'  # Hotkey for next ungraded exam
    next_q = '.'  # Hotkey for next question
    tab_hot_key = ['ctrl', 'tab']  # Hotkey for next browser tab.
    x = 600  # -200  # Initilizing click x position
    y = 250  # Initilizing click y position
    ask_for_next_q = False
    
    pars = {'Submissions': submissions, 'Questions': questions,
            'WaitTime': wait_time, 'NextSub': next_sub, 'Tabs': tabs,
            'TabHotKey': tab_hot_key, 'NextQ': next_q,
            'AskForNextQ': ask_for_next_q, 'x': x, 'y': y}
    
    return pars


def grade(pars):
    if not pars['AskForNextQ']:
        pg.click(x=pars['x'], y=pars['y'])

    for question in pars['Questions']:
        if pars['AskForNextQ']:
            line = input('Press enter to start next question, enter number for speed in seconds: ')
            try:
                pars['WaitTime'] = float(line.strip())
            except ValueError:
                pass
            pg.click(x=pars['x'], y=pars['y'])
        for subs in pars['Submissions']:
            for i in range(subs):
                time.sleep(pars['WaitTime'])
                qstring = get_question_key_string(question)
                pg.typewrite(qstring)
                if i < subs-1:
                    pg.press(pars['NextSub'])
            pg.typewrite(pars['NextQ'])
            pg.hotkey(pars['TabHotKey'][0], pars['TabHotKey'][1])
        

def get_question_key_string(question):
    qstring = ''
    for stroke in question:
        qstring += str(stroke)

    return qstring


def read_credentials(path):
    with open(path, 'r') as file:
        lines = file.readlines()

    return lines


if __name__ == '__main__':
    main()
