#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on April 16 3:03 PM 2023
Created in PyCharm
Created as Misc/copy_assignment.py

@author: Dylan Neff, Dylan
"""

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from time import sleep

from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


def main():
    copy_assignment()
    print('donzo')


def copy_assignment():
    assignment_name = '5C Lab 2'
    week = 2
    # good_course_include_flags = ['5CL-G']
    section_time_map = get_section_time_map()
    section_id_map = get_section_id_map()
    good_course_include_flags = ['5CL-G']
    copy_course = '5CL-G4'
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
                        if assignment_name in assign_button.text:
                            print(f'{course_name} {assignment_name} already here')
                            break
                    except NoSuchElementException:
                        duplicate_assignment(driver, assignment_name, section_id_map, copy_course)
                        set_assignment_due_date(driver, assignment_name, course_name, week, section_time_map)
                        print(f'{course_name} {assignment_name} copied and due date updated')
                        break
                    assign_index += 1
                driver.find_element(By.XPATH, '/html/body/nav[1]/div[1]/div[2]/div[1]/a/img').click()  # Return to main
            course_index += 1
        except NoSuchElementException:
            print('No more courses')
            break
    sleep(2)


def duplicate_assignment(driver, assignment_name, section_id_map, copy_course):
    # Assignments
    driver.find_element(By.XPATH, '/html/body/nav[1]/div[1]/ul[1]/li[2]/a/div[2]').click()
    # Duplicate
    driver.find_element(By.XPATH, '//*[@id="main-content"]/section/ul/li[3]/a').click()
    course_drop = driver.find_element(By.XPATH, f'//*[@id="course-{section_id_map[copy_course]}"]')
    course_drop.click()
    course_drop_parent = course_drop.find_element(By.XPATH, '..')
    for dup_assignment in course_drop_parent.find_elements(By.XPATH, './ul/*'):
        if assignment_name in dup_assignment.text:
            dup_assignment.click()
            driver.find_element(By.XPATH, '//*[@id="duplicate-btn"]').click()
            break


def set_assignment_due_date(driver, assignment_name, course_name, week, section_time_map):
    assign_dup_index = 1
    while True:
        # This path can be bad if only one assignment. Then tr[i]/ -> tr/
        assign_xpath = f'//*[@id="assignments-instructor-table"]/tbody/' \
                       f'tr[{assign_dup_index}]/td[1]/div/div/a'
        try:
            assign_button = driver.find_element(By.XPATH, assign_xpath)
            if assignment_name in assign_button.text:
                assign_button.click()
                driver.find_element(By.XPATH,
                                    '/html/body/nav[1]/div[1]/ul[2]/li[4]/a/div[2]').click()
                due_date_entry = driver.find_element(By.XPATH,
                                                     '//*[@id="assignment_due_date_string"]')
                due_date_entry.clear()
                due_date = get_due_date(course_name, week, section_time_map, assignment_name)
                due_date_entry.send_keys(due_date.strftime('%b %d %Y %H:%M %p'))
                driver.find_element(By.XPATH, '//*[@id="assignment-actions"]/input').click()
                break
        except NoSuchElementException:
            print('Duplication bad')
            break
        assign_dup_index += 1


def get_due_date(course_name, week, section_time_map, assign_name='5C Pre-Lab'):
    due_date = section_time_map[course_name] + timedelta(weeks=week - 1)
    if 'Pre-Lab' in assign_name:
        due_date -= timedelta(hours=1)
    elif 'Lab' in assign_name:
        due_date += timedelta(days=2)
    else:
        print('Don\'t recognize assignment?', assign_name)
        due_date = None

    return due_date


def get_section_time_map(prefix='5CL-G'):
    section_times = {
        1: datetime(2023, 4, 10, 8, 0, 0),
        2: datetime(2023, 4, 10, 9, 30, 0),
        3: datetime(2023, 4, 10, 11, 0, 0),
        4: datetime(2023, 4, 10, 12, 30, 0),
        5: datetime(2023, 4, 10, 14, 0, 0),
        6: datetime(2023, 4, 10, 15, 30, 0),
        7: datetime(2023, 4, 10, 17, 0, 0),
        8: datetime(2023, 4, 10, 18, 30, 0),
        9: datetime(2023, 4, 11, 8, 0, 0),
        10: datetime(2023, 4, 11, 9, 30, 0),
        11: datetime(2023, 4, 11, 11, 0, 0),
        12: datetime(2023, 4, 11, 12, 30, 0),
        13: datetime(2023, 4, 11, 14, 0, 0),
        14: datetime(2023, 4, 11, 15, 30, 0),
        15: datetime(2023, 4, 11, 17, 0, 0),
        16: datetime(2023, 4, 11, 18, 30, 0),
        17: datetime(2023, 4, 12, 8, 0, 0),
        18: datetime(2023, 4, 12, 9, 30, 0),
        19: datetime(2023, 4, 12, 11, 0, 0),
        20: datetime(2023, 4, 12, 12, 30, 0),
        21: datetime(2023, 4, 12, 14, 0, 0),
        22: datetime(2023, 4, 12, 15, 30, 0),
        23: datetime(2023, 4, 12, 17, 0, 0),
        24: datetime(2023, 4, 12, 18, 30, 0),
        25: datetime(2023, 4, 13, 8, 0, 0),
        26: datetime(2023, 4, 13, 9, 30, 0),
        27: datetime(2023, 4, 13, 11, 0, 0),
        28: datetime(2023, 4, 13, 12, 30, 0),
        29: datetime(2023, 4, 13, 14, 0, 0),
        30: datetime(2023, 4, 13, 15, 30, 0),
    }

    section_time_map = {f'{prefix}{section}': first_time for section, first_time in section_times.items()}

    return section_time_map


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

    return lines


if __name__ == '__main__':
    main()
