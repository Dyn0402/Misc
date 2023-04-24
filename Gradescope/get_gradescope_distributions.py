#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on April 14 8:24 PM 2023
Created in PyCharm
Created as Misc/get_gradescope_distributions

@author: Dylan Neff, Dylan
"""

import time
from time import sleep

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

import selenium.common.exceptions
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from GradescopeNavigator import GradescopeDistributionGetter as GsDG


def main():
    selenium_test()
    plot_lab1()
    print('donzo')


def selenium_test():  # Old assignments go away on dashboard. Need to use assignments page when put in GsDG class
    assignment_name = ['Week 1', 'lab 1']
    section_ta_map = get_section_ta_map()
    good_course_include_flags = ['5CL-G']
    # good_course_include_flags = ['5CL-G4', '5CL-G5', '5CL-G12', '5CL-G13']
    wait_time_for_page_element = 1  # s
    window_width, window_height = 1200, 800  # Pixels
    uname, pword = read_credentials('C:/Users/Dylan/Desktop/Creds/gradescope_creds.txt')

    driver_path = '../chromedriver/chromedriver_win.exe'
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

    df = []
    course_index = 1
    while course_index is not None:
        try:
            course_name = driver.find_element(By.XPATH, f'//*[@id="account-show"]/div/div[2]/a[{course_index}]/h3').text
            if any(flag in course_name for flag in good_course_include_flags):
                driver.find_element(By.XPATH, f'//*[@id="account-show"]/div/div[2]/a[{course_index}]/div[2]').click()
                assign_index = 1
                while True:
                    # This path can be bad if only one assignment. Then tr[i]/ -> tr/
                    assign_xpath = f'//*[@id="assignments-instructor-table"]/tbody/tr[{assign_index}]/td[1]/div/div/a'
                    try:
                        assign_button = driver.find_element(By.XPATH, assign_xpath)
                        if any(ass_name in assign_button.text for ass_name in assignment_name):
                            assign_button.click()
                            review = driver.find_element(By.XPATH, '/html/body/nav[1]/div[1]/ul[1]/li[5]/a/div[2]')
                            if 'Review Grades' in review.text:
                                review.click()
                            else:
                                print('Don\'t see "Review Grades" option?')
                                sleep(5)
                            student_index = 1
                            while True:
                                try:
                                    score_xpath = f'//*[@id="DataTables_Table_0"]/tbody/tr[{student_index}]/td[3]'
                                    try:
                                        score = float(driver.find_element(By.XPATH, score_xpath).text)
                                        name_xpath = f'//*[@id="DataTables_Table_0"]/tbody/tr[{student_index}]/td[1]/a'
                                        student_name = driver.find_element(By.XPATH, name_xpath).text
                                        df.append({'section': course_name, 'ta': section_ta_map[course_name],
                                                   'student_name': student_name, 'score': score})
                                    except ValueError:
                                        pass
                                    student_index += 1
                                except NoSuchElementException:
                                    print(f'End of course {course_name}')
                                    break
                            break
                    except NoSuchElementException:
                        print('Couldn\'t find right assignment')
                        break
                    assign_index += 1
                driver.find_element(By.XPATH, '/html/body/nav[1]/div[1]/div[2]/div[1]/a/img').click()  # Return to main
            course_index += 1

        except NoSuchElementException:
            print('Finished parsing courses')
            course_index = None

        # course_index = None

    df = pd.DataFrame(df)
    df.to_csv('C:/Users/Dylan/Desktop/lab1_dists.csv', index=False)
    # print(df)
    # sleep(2)
    driver.close()
    driver.quit()


def plot_lab1():
    df = pd.read_csv('C:/Users/Dylan/Desktop/lab1_dists.csv')
    # df = df[df['section'] != '5CL-G30']
    df = df[(df['score'] != 0) & (df['score'] != 20)]
    print(df)
    fig_coures, ax_courses = plt.subplots(dpi=144)
    sns.histplot(data=df, x='score', hue='section')
    fig_coures, ax_courses = plt.subplots(dpi=144)
    sns.kdeplot(data=df, x='score', hue='section')
    sns.rugplot(data=df, x='score', hue='section')
    # for section in pd.unique(df['section']):
    #     df_section = df[df['section'] == section]
    #     sns.histplot(df_section['score'], label=section)
    # plt.legend()

    fig_tas, ax_tas = plt.subplots(dpi=144)
    sns.histplot(data=df, x='score', hue='ta', multiple='stack')
    fig_tas, ax_tas = plt.subplots(dpi=144)
    sns.kdeplot(data=df, x='score', hue='ta')
    sns.rugplot(data=df, x='score', hue='ta')
    # for ta_name in pd.unique(df['ta']):
    #     df_ta = df[df['ta'] == ta_name]
    #     sns.histplot(df_ta['score'], label=ta_name)
    # plt.legend()

    plt.show()


def get_section_ta_map(prefix='5CL-G'):
    ta_sections = {
        'Tianci': [1, 2, 3],
        'Dylan': [4, 5],
        'Casey': [6, 7, 14],
        'Andrew': [8, 9, 10],
        'Mianzhi': [11, 29],
        'J': [12, 13, 22],
        'Jacob T': [15, 16],
        'Jared': [17, 18, 19],
        'Fidele': [21, 20, 25],
        'Jacob S': [23, 24, 30],
        'Kate': [26, 27, 28],
    }

    section_ta_map = {f'{prefix}{section}': name for name, sections in ta_sections.items() for section in sections}

    return section_ta_map


def read_credentials(path):
    with open(path, 'r') as file:
        lines = file.readlines()

    return [line.strip() for line in lines]


if __name__ == '__main__':
    main()
