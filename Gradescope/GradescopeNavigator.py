#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on April 19 6:31 PM 2023
Created in PyCharm
Created as Misc/GradescopeNavigator

@author: Dylan Neff, Dylan
"""

from datetime import datetime, timedelta
from pynput import keyboard
from time import sleep

from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


class GradescopeNavigator:
    def __init__(self, cred_path=None):
        if cred_path is None:
            self.cred_path = 'C:/Users/Dylan/Desktop/Creds/gradescope_creds.txt'
        else:
            self.cred_path = cred_path
        self.driver = None
        self.section_id_map = get_section_id_map()

        self.wait_time_for_page_element = 1  # s Time to wait for element to appear

        self.start_driver()
        self.log_in()

    def __del__(self):
        self.driver.close()
        self.driver.quit()

    def start_driver(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(f'--start-maximized')
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(self.wait_time_for_page_element)

    def log_in(self):
        gradescope_log_url = 'https://www.gradescope.com/login'
        uname, pword = read_credentials(self.cred_path)
        self.driver.get(gradescope_log_url)
        self.driver.find_element(By.XPATH, '//*[@id="session_email"]').send_keys(uname)
        self.driver.find_element(By.XPATH, '//*[@id="session_password"]').send_keys(pword)
        self.driver.find_element(By.XPATH, '/html/body/div[1]/main/div[2]/div/section/form/div[4]/input').click()

    def open_section(self, section_name):
        self.driver.get(f'https://www.gradescope.com/courses/{self.section_id_map[section_name]}')

    def open_section_assignments(self, section_name):
        self.driver.get(f'https://www.gradescope.com/courses/{self.section_id_map[section_name]}/assignments')

    def open_section_assignment(self, section, assignment_name, page=''):
        assignment_id = self.find_assignment_id(section, assignment_name)
        if assignment_id is not None:
            section_id = self.section_id_map[section]
            assignment_url = f'https://www.gradescope.com/courses/{section_id}/assignments/{assignment_id}/{page}'
            self.driver.get(assignment_url)
            return True
        else:
            return False

    def find_assignment_id(self, section_name, assignment_name):
        self.open_section_assignments(section_name)
        assign_index = 1
        while True:
            # This path can be bad if only one assignment. Then tr[i]/ -> tr/
            assign_xpath = f'//*[@id="assignments-instructor-table"]/tbody/tr[{assign_index}]/td[1]/div/div/a'
            try:
                assign_button = self.driver.find_element(By.XPATH, assign_xpath)
                if assignment_name in assign_button.text:
                    assign_button.click()
                    assignment_id = self.driver.current_url.split('/')[-2]
                    return assignment_id
            except NoSuchElementException:
                return None
            assign_index += 1

    def get_url_id(self, id_type='questions'):
        url = self.driver.current_url
        id_flag = f'/{id_type}/'
        id_index = url.find(id_flag)
        if id_index > 0:
            url_id = int(url[id_index + len(id_flag):].split('/')[0])
        else:
            url_id = None

        return url_id

    def get_page(self):
        return self.driver.current_url.split('/')[-1]

    def get_sections(self):
        return self.section_id_map.keys()


class GradescopeAssignmentDuplicator(GradescopeNavigator):
    def __init__(self, cred_path=None):
        self.section_time_map = get_section_time_map()

        GradescopeNavigator.__init__(self, cred_path)

    def duplicate_assignment(self, copy_to_section, copy_from_section, assignment_name):
        if self.find_assignment_id(copy_to_section, assignment_name):
            print(f'Assignment {assignment_name} already in {copy_to_section}')
            return False
        self.open_section_assignments(copy_to_section)
        self.driver.find_element(By.XPATH, '//*[@id="main-content"]/section/ul/li[3]/a').click()  # Duplicate
        course_drop = self.driver.find_element(By.XPATH, f'//*[@id="course-{self.section_id_map[copy_from_section]}"]')
        course_drop.click()
        course_drop_parent = course_drop.find_element(By.XPATH, '..')
        for dup_assignment in course_drop_parent.find_elements(By.XPATH, './ul/*'):
            if assignment_name in dup_assignment.text:
                dup_assignment.click()
                self.driver.find_element(By.XPATH, '//*[@id="duplicate-btn"]').click()
                return True

    def set_assignment_due_date(self, section, assignment_name, week):
        if self.open_section_assignment(section, assignment_name, page='edit'):  # Settings
            due_date_entry = self.driver.find_element(By.XPATH, '//*[@id="assignment_due_date_string"]')  # Due Date
            due_date_entry.clear()
            due_date = self.get_due_date(section, week, assignment_name)
            due_date_entry.send_keys(due_date.strftime('%b %d %Y %H:%M %p'))
            self.driver.find_element(By.XPATH, '//*[@id="assignment-actions"]/input').click()
        else:
            print('Can\'t find assignment')

    def get_due_date(self, section, week, assign_name='5C Pre-Lab'):
        due_date = self.section_time_map[section] + timedelta(weeks=week - 1)
        if 'Pre-Lab' in assign_name:
            due_date -= timedelta(hours=1)
        elif 'Lab' in assign_name:
            due_date += timedelta(days=2)
        else:
            print('Don\'t recognize assignment?', assign_name)
            due_date = None

        return due_date


class GradescopeGrader(GradescopeNavigator):
    def __init__(self, cred_path=None):
        self.pause = False
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()

        self.question_check_time = 1

        GradescopeNavigator.__init__(self, cred_path)

    def __del__(self):
        self.listener.join()

    def on_press(self, key):
        if key == keyboard.Key.space:
            self.pause = False if self.pause else True
            if self.pause:
                print('Pausing')
            else:
                print('Resuming')

    def grade_assignment(self, assignment_name, sections, rubric_numbers):
        if type(sections) != list:
            sections = [sections]
        statuses = {section: '' for section in sections}
        while any([status != 'All Graded' for status in statuses.values()]):
            for section in sections:
                if self.open_section_assignment(section, assignment_name, page='grade'):
                    statuses[section] = self.grade_next_question(rubric_numbers)
                else:
                    print(f'Couldn\'t open assignment. {section} {assignment_name}')

    def get_next_question(self):
        if self.get_page() != 'grade':
            print('Not on Grading Dashboard!')
            return
        self.driver.find_element(By.XPATH, '//*[@id="main-content"]/section/ul/li[2]/a').click()  # Next Question
        if self.get_page() == 'review_grades':
            return 'Finished'

        section_id = self.get_url_id('courses')
        question_id = self.get_url_id('questions')
        self.driver.get(f'https://www.gradescope.com/courses/{section_id}/questions/{question_id}/submissions/')
        self.driver.find_element(By.XPATH, '//*[@id="question_submissions"]/tbody/tr[1]/td[2]/a').click()

    def grade_next_question(self, rubric_numbers, grade_all_questions=False):
        if self.get_next_question() == 'Finished':
            return

        while True:
            try:
                sleep(self.question_check_time / 2)
                for rubric_number in rubric_numbers:
                    rubric_xpath = f'//*[@id="main-content"]/div/main/div[3]/div[2]/' \
                                   f'div/div[2]/div[1]/ol/li[{rubric_number}]/div/div/button'
                    self.driver.find_element(By.XPATH, rubric_xpath).click()
                sleep(self.question_check_time / 2)
                while self.pause:  # If space bar was clicked
                    sleep(0.1)  # Wait for space bar to be clicked again
                self.driver.find_element(By.XPATH,
                                    '//*[@id="main-content"]/div/main/section/ul/li[5]/button/span/span/span').click()
            except NoSuchElementException:
                sleep(1)
                page = self.get_page()
                if page == 'grade':
                    if grade_all_questions:  # Next Question
                        self.driver.find_element(By.XPATH, '//*[@id="main-content"]/section/ul/li[2]/a').click()
                    else:
                        return 'Question Graded'
                elif page == 'review_grades':
                    return 'All Graded'
                else:
                    print(f'Don\'t know where we are? {page}')
                    return 'Lost'


class GradescopeDistributionGetter(GradescopeNavigator):
    def __init__(self, cred_path=None):
        GradescopeNavigator.__init__(self, cred_path)




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

    return [line.strip() for line in lines]