#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on March 18 6:37 PM 2023
Created in PyCharm
Created as Misc/apply_llnl

@author: Dylan Neff, Dylan
"""

# from selenium import webdriver

from time import sleep

import pyautogui as pg
import pyscreeze as psz

from pynput import keyboard


def main():
    helper = AppHelper()
    helper.reverse_lists()
    helper.start_listening()
    print(f'Press {helper.experience_key} to enter an Experience')
    print(f'Press {helper.education_key} to enter an Education')
    while True:
        sleep(1)
        if len(helper.experience_list) == len(helper.education_list) == 0:
            sleep(5)
            break

    print('donzo')


class AppHelper:
    def __init__(self):
        self.work_experience_path = 'N:/UCLA_Microsoft/OneDrive - personalmicrosoftsoftware.ucla.edu/Post_Grad_Search/' \
                                    'Job_Applications/Work Experience.txt'
        self.experience_key = keyboard.Key.right
        self.education_key = keyboard.Key.left

        # pg.PAUSE = 0.1  # s How long to pause after each call

        self.experience_list, self.education_list = read_work_experience(self.work_experience_path)
        self.experience_listener = keyboard.Listener(on_press=self.write_experience_list)
        self.education_listener = keyboard.Listener(on_press=self.write_education_list)

    def test(self):
        print(self.experience_key)
        print(self.experience_list[0])
        print(dir(self.experience_list[0]))
        print(self.experience_list[0].job_title)

    def start_listening(self):
        self.experience_listener.start()
        self.education_listener.start()
        print('Listening for key press...')

    def reverse_lists(self):
        self.experience_list = list(reversed(self.experience_list))
        self.education_list = list(reversed(self.education_list))

    def write_experience_list(self, key):
        if key == self.experience_key:
            experience = self.experience_list.pop(0)
            print('Writing Experience...')
            print(f'Start Date: {experience.start_date}')
            print(f'End Date: {experience.end_date}')
            pg.write(experience.job_title)
            pg.press('tab')
            pg.write(experience.company)
            pg.press('tab')
            pg.write(experience.location)
            sleep(1)
            pg.press('down')
            pg.press('enter')
            sleep(0.5)
            pg.press('tab')
            pg.write(experience.description)
            print(f'{len(self.experience_list)} remaining Experience entries.')

    def write_education_list(self, key):
        if key == self.education_key:
            education = self.education_list.pop(0)
            print('Writing Education...')
            print(f'Start Date: {education.start_date}')
            print(f'End Date: {education.end_date}')
            pg.write(education.institution)
            pg.press('tab')
            pg.write(education.major)
            pg.press('tab')
            pg.write(education.degree)
            pg.press('tab')
            pg.write(education.location)
            sleep(1)
            pg.press('down')
            pg.press('enter')
            print(f'{len(self.education_list)} remaining Education entries.')


class Experience:
    def __init__(self):
        self.company = None
        self.job_title = None
        self.location = None
        self.description = None
        self.start_date = None
        self.end_date = None


class Education:
    def __init__(self):
        self.institution = None
        self.major = None
        self.degree = None
        self.location = None
        self.start_date = None
        self.end_date = None


def read_work_experience(file_path):
    experience_list, education_list = [], []
    with open(file_path, 'r') as file:
        text = file.read()

    entry_type = None
    for entry in text.split('\n\n'):
        if 'Work Experience\n' in entry:
            entry_type = 'Work Experience'
            entry = entry.replace('Work Experience\n', '')
        elif 'Education\n' in entry:
            entry_type = 'Education'
            entry = entry.replace('Education\n', '')
        elif 'Skills\n' in entry:
            entry_type = 'Skills'
            entry = entry.replace('Skills:\n', '')

        entry_lines = entry.split('\n')
        if entry_type == 'Work Experience':
            new_experience = Experience()
            for line in entry_lines:
                if 'Company Name: ' in line:
                    new_experience.company = line.replace('Company Name: ', '')
                elif 'Job Title: ' in line:
                    new_experience.job_title = line.replace('Job Title: ', '')
                elif 'Location: ' in line:
                    new_experience.location = line.replace('Location: ', '')
                elif 'Description: ' in line:
                    new_experience.description = line.replace('Description: ', '')
                elif 'Start Date: ' in line:
                    new_experience.start_date = line.replace('Start Date: ', '')
                elif 'End Date: ' in line:
                    new_experience.end_date = line.replace('End Date: ', '')
            experience_list.append(new_experience)
        elif entry_type == 'Education':
            new_education = Education()
            for line in entry_lines:
                if 'Institution: ' in line:
                    new_education.institution = line.replace('Institution: ', '')
                elif 'Major: ' in line:
                    new_education.major = line.replace('Major: ', '')
                elif 'Degree: ' in line:
                    new_education.degree = line.replace('Degree: ', '')
                elif 'Location: ' in line:
                    new_education.location = line.replace('Location: ', '')
                elif 'Start Date: ' in line:
                    new_education.start_date = line.replace('Start Date: ', '')
                elif 'End Date: ' in line:
                    new_education.end_date = line.replace('End Date: ', '')
            education_list.append(new_education)

    # print(experience_list, education_list)
    return experience_list, education_list


def pg_write_test():
    # Works
    sleep(5)
    pg.write('test')
    pg.press('tab')
    pg.write('test2')


def pg_find_test():
    x, y = psz.locateCenterOnScreen('C:/Users/Dyn04/Desktop/llnl_apply_images/from_date.png')
    pg.click(x=x, y=y)
    x, y = psz.locateCenterOnScreen('C:/Users/Dyn04/Desktop/llnl_apply_images/2012.png')
    pg.click(x=x, y=y)
    x, y = psz.locateCenterOnScreen('C:/Users/Dyn04/Desktop/llnl_apply_images/July.png')
    pg.click(x=x, y=y)
    # pg.moveTo(x, y)
    # print(psz.locateOnScreen('C:/Users/Dylan/Desktop/llnl_s/big_test.png'))
    # print(psz.locateOnScreen('C:/Users/Dylan/Desktop/llnl_shots/big_test.png', region=(280, 107, 1561, 1029),
    #       grayscale=True))

    print(pg.position())


# def selenium_test():
#     # Selenium got blocked after first couple tests, even when I did Captchas
#     driver_path = 'chromedriver/chromedriver_win.exe'
#     application_url = 'https://jobs.smartrecruiters.com/oneclick-ui/company/LLNL/publication/' \
#                       '2520cbac-db03-4c65-9541-a7aee2d6c26f?dcr_ci=LLNL&sid=2d92f286-613b-4daf-9dfa-6340ffbecf73'
#     driver = webdriver.Chrome(executable_path=driver_path)
#     driver.get(application_url)
#     # driver.find_element(By.XPATH, '//*[@id="first-name-input"]').send_keys('Test')
#     sleep(15)
#     driver.close()
#     driver.quit()


if __name__ == '__main__':
    main()
