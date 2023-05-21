# -*- coding: utf-8 -*-
"""
Created on Tue Apr 03 13:54:50 2018

@author: Dyn04
"""


import pyautogui as pg
from pynput import keyboard
import time
from time import sleep

from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from GradescopeNavigator import GradescopeGrader as GsG


pause = False


def main():
    # pars = initialize()
    # grade(pars)
    # selenium_test()
    # grade_gsg()
    grade_attendance()
    # grade_lab_attendance()
    print('donzo')


def grade_gsg():
    # sections = ['5CL-G4', '5CL-G5']
    sections = ['5CL-G5']
    assignment_name = 'Pre-Lab 2'
    rubric_numbers = [1]
    grader = GsG()
    grader.grade_assignment(assignment_name, sections, rubric_numbers)


def grade_attendance():
    assignment_name = 'Attendance/Participation/LA Survey Adjustments'
    # question_rubrics = {1: [1], 2: [1], 3: [1], 4: [1], 5: [1], 6: [1], 7: [1], 8: [1]}
    # question_rubrics = {1: [1], 2: [1], 3: [1], 4: [1], 5: [1], 6: [1], 9: [1]}
    question_rubrics = {1: [1], 2: [1], 3: [1], 4: [1], 5: [1], 8: [1]}
    # question_rubrics = {5: [1]}
    grader = GsG(listener=False)
    sections = grader.get_sections('5BL-G')
    # print(sections)
    # sections = ['5CL-G3']
    grader.grade_assignment_questions(assignment_name, sections, question_rubrics)
    grader.close()


def grade_lab_attendance():
    assignment_name = '5C Lab 6'
    # question_rubrics = {1: [1], 2: [1], 3: [1], 4: [1], 5: [1], 6: [1], 7: [1], 8: [1]}
    # question_rubrics = {1: [1], 2: [1], 3: [1], 4: [1], 5: [1], 9: [1]}
    question_rubrics = {1: [1]}
    grader = GsG(listener=False)
    sections = grader.get_sections('5CL-G')
    # print(sections)
    # sections = ['5CL-G3']
    grader.grade_assignment_questions(assignment_name, sections, question_rubrics)
    grader.close()


def on_press(key):
    if key == keyboard.Key.space:
        global pause
        pause = False if pause else True
        if pause:
            print('Pausing')
        else:
            print('Resuming')


def selenium_test():
    rubric_numbers = [1]
    wait_time_for_page_element = 1  # s
    question_check_time = 1  # s
    # window_width, window_height = 1200, 100  # Pixels
    uname, pword = read_credentials('C:/Users/Dylan/Desktop/Creds/gradescope_creds.txt')

    application_url = 'https://www.gradescope.com/courses/526872/questions/22701604/submissions/' \
                      '1523798748/grade?not_grouped=true'
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f'--start-maximized')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(wait_time_for_page_element)
    driver.get(application_url)
    driver.find_element(By.XPATH, '//*[@id="session_email"]').send_keys(uname)
    driver.find_element(By.XPATH, '//*[@id="session_password"]').send_keys(pword)
    driver.find_element(By.XPATH, '/html/body/div[1]/main/div[2]/div/section/form/div[4]/input').click()

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    while True:
        print('Here')
        try:
            sleep(question_check_time / 2)
            for rubric_number in rubric_numbers:
                rubric_xpath = f'//*[@id="main-content"]/div/main/div[3]/div[2]/' \
                               f'div/div[2]/div[1]/ol/li[{rubric_number}]/div/div/button'
                driver.find_element(By.XPATH, rubric_xpath).click()
            sleep(question_check_time / 2)
            while pause:  # If space bar was clicked
                sleep(0.1)  # Wait for space bar to be clicked again
            driver.find_element(By.XPATH,
                                '//*[@id="main-content"]/div/main/section/ul/li[5]/button/span/span/span').click()
        except NoSuchElementException:
            sleep(2)
            page_class = driver.find_element(By.XPATH, '//*[@id="main-content"]/div[2]/div/div').get_attribute('class')
            if page_class == 'gradingDashboard':
                driver.find_element(By.XPATH, '//*[@id="main-content"]/section/ul/li[2]/a').click()  # Next Question
            else:
                break

    print('Finished')
    listener.join()
    sleep(5)
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


def get_section_id_map(prefix='5CL-G'):
    section_ids = {
        1: 526869,
        2: 526870,
        3: 526871,
        4: 526872,
        5: 526874,
        6: 526875,
        7: 526878,
        8: 526879,
        9: 526880,
        10: 526881,
        11: 526882,
        12: 526883,
        13: 526884,
        14: 526888,
        15: 526889,
        16: 526891,
        17: 526892,
        18: 526893,
        19: 526894,
        20: 526895,
        21: 526896,
        22: 526897,
        23: 526898,
        24: 526901,
        25: 526902,
        26: 526906,
        27: 526907,
        28: 526909,
        29: 526910,
        30: 526915,
    }

    section_id_map = {f'{prefix}{section}': section_id for section, section_id in section_ids.items()}

    return section_id_map


def read_credentials(path):
    with open(path, 'r') as file:
        lines = file.readlines()

    return [line.strip() for line in lines]


if __name__ == '__main__':
    main()
