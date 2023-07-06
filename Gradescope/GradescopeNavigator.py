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

from selenium.common.exceptions import WebDriverException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
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

    # def open_section_assignment(self, section, assignment_name):
    #     self.open_section_assignments(section)
    #     assign_index = 1
    #     while True:
    #         # This path can be bad if only one assignment. Then tr[i]/ -> tr/
    #         assign_xpath = f'//*[@id="assignments-instructor-table"]/tbody/tr[{assign_index}]/td[1]/div/div/a'
    #         try:
    #             assign_button = self.driver.find_element(By.XPATH, assign_xpath)
    #             if assignment_name in assign_button.text:
    #                 assign_button.click()
    #                 page = self.get_page()
    #                 if page == 'grade':
    #                     return True
    #                 elif page == 'review_grades':
    #                     print(f'{section} {assignment_name} already graded')
    #                     return False
    #         except NoSuchElementException:
    #             print(f'{section} {assignment_name} couldn\'t find assignment button')
    #             return False
    #         assign_index += 1

    def open_section(self, section, page=''):
        section_id = self.section_id_map[section]
        assignment_url = f'https://www.gradescope.com/courses/{section_id}/{page}'
        self.driver.get(assignment_url)

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

    def get_sections(self, prefixes=None):
        if prefixes is not None:
            self.section_id_map = get_section_id_map(prefixes)
        return list(self.section_id_map.keys())

    def get_roster(self, section, get_student_id=True):
        self.open_section(section, 'memberships')
        df = []
        member_index = 1
        while True:
            name_xpath = f'//*[@id="DataTables_Table_0"]/tbody/tr[{member_index}]/td[1]'
            role_xpath = f'//*[@id="DataTables_Table_0"]/tbody/tr[{member_index}]/td[3]/select'
            edit_xpath = f'//*[@id="DataTables_Table_0"]/tbody/tr[{member_index}]/td[5]/button'
            id_xpath = '//*[@id="course_membership_sid"]'
            cancel_xpath = '//*[@id="edit-member-modal"]/div/div[2]/form/div[7]/button'
            try:
                name = self.driver.find_element(By.XPATH, name_xpath).text
                if name[-5:] == ' Edit':
                    name = name[:-5]
                role_drop = Select(self.driver.find_element(By.XPATH, role_xpath))
                role = role_drop.first_selected_option.text
                df.append({'name': name, 'role': role})
                if get_student_id:
                    self.driver.find_element(By.XPATH, edit_xpath).click()
                    student_id = self.driver.find_element(By.XPATH, id_xpath).get_attribute('value')
                    self.driver.find_element(By.XPATH, cancel_xpath).click()
                    df[-1].update({'student_id': student_id})
            except NoSuchElementException:
                break
            member_index += 1

        return df

    def upload_scans(self, section, assignment_name, scans_directory):
        if self.open_section_assignment(section, assignment_name, 'submission_batches'):
            print(self.driver.window_handles)
            select_pdf_files_xpath = '//*[@id="main-content"]/div/main/div[3]/div/div/div/div[1]/div[2]/div/button/span'
            select_pdf_files_button = self.driver.find_element(By.XPATH, select_pdf_files_xpath)
            select_pdf_files_button.click()
            sleep(1)
            key_control = keyboard.Controller()
            print(scans_directory.replace('/', '\\'))
            key_control.type(scans_directory.replace('/', '\\'))
            key_control.press(keyboard.Key.enter)
            key_control.release(keyboard.Key.enter)
            for i in range(11):
                key_control.press(keyboard.Key.tab)
                key_control.release(keyboard.Key.tab)
                sleep(0.5)
            key_control.press(keyboard.Key.ctrl)
            key_control.press('a')
            key_control.release(keyboard.Key.ctrl)
            key_control.release('a')
            key_control.press(keyboard.Key.enter)
            key_control.release(keyboard.Key.enter)
            sleep(5)

        else:
            print(f'Couldn\'t open {section} {assignment_name}')

    def upload_submissions(self, section, assignment_name, scans_directory, roster):
        if self.open_section_assignment(section, assignment_name, 'submissions'):
            upload_sub_xpath = '//*[@id="actionBar"]/ul/button'
            student_name_xpath = '//*[@id="owner_id-selectized"]'
            select_file_xpath = '//*[@id="submissions-manager-upload-form"]/div[2]/label/span[2]/span'
            upload_xpath = '//*[@id="submit"]'
            for name in roster:
                self.driver.find_element(By.XPATH, upload_sub_xpath).click()
                student_name_entry = self.driver.find_element(By.XPATH, student_name_xpath)
                student_name_entry.clear()
                student_name_entry.send_keys(name + '\n')
                self.driver.find_element(By.XPATH, select_file_xpath).click()
                sleep(0.5)
                key_control = keyboard.Controller()
                key_control.type(scans_directory.replace('/', '\\') + name + '.pdf\n')
                sleep(0.5)
                self.driver.find_element(By.XPATH, upload_xpath).click()
        else:
            print(f'Couldn\'t open {section} {assignment_name}')


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
            for date_field in '%m %d %Y %H %M %p'.split():
                due_date_entry.send_keys(due_date.strftime(date_field))
            self.driver.find_element(By.XPATH, '//*[@id="assignment-actions"]/input').click()
        else:
            print('Can\'t find assignment')

    def get_due_date(self, section, week, assign_name='5C Pre-Lab'):
        due_date = self.section_time_map[section] + timedelta(weeks=week - 1)
        if 'Pre-Lab' in assign_name:
            due_date -= timedelta(hours=1)
        elif 'Lab' in assign_name:
            due_date += timedelta(days=2, hours=1.5)
        else:
            print('Don\'t recognize assignment?', assign_name)
            due_date = None

        return due_date


class GradescopeGrader(GradescopeNavigator):
    def __init__(self, cred_path=None, listener=True):
        self.pause = False
        self.listener = None
        if listener:
            self.start_listener()

        self.question_check_time = 0.4

        GradescopeNavigator.__init__(self, cred_path)

    def __del__(self):
        self.close()

    def close(self):
        if self.listener is not None:
            self.listener.stop()
            self.listener.join()

    def start_listener(self):
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()

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

    def grade_assignment_questions(self, assignment_name, sections, question_rubrics):
        if type(sections) != list:
            sections = [sections]
        for section in sections:
            print(f'\nStarting {section}...')
            self.open_section_assignment(section, assignment_name, page='grade')
            for question_number, rubric_items in question_rubrics.items():
                if self.get_page() == 'grade':
                    self.grade_question(question_number, rubric_items)
                elif self.open_section_assignment(section, assignment_name, page='grade'):
                    self.grade_question(question_number, rubric_items)
                else:
                    print(f'Couldn\'t open assignment. {section} {assignment_name}')

    def grade_question(self, question_number, rubric_items):
        if self.get_question(question_number):
            print(f'Got question {question_number}')
            while True:
                try:
                    sleep(self.question_check_time)
                    for rubric_number in rubric_items:
                        rubric_xpath = f'//*[@id="main-content"]/div/main/div[3]/div[2]/' \
                                       f'div/div[2]/div[1]/ol/li[{rubric_number}]/div/div/button'
                        rubric_button = self.driver.find_element(By.XPATH, rubric_xpath)
                        if rubric_button.get_attribute('aria-pressed') == 'false':
                            self.driver.find_element(By.XPATH, rubric_xpath).click()
                    while self.pause:  # If space bar was clicked
                        sleep(0.1)  # Wait for space bar to be clicked again
                    # next_ungraded_xpath = '//*[@id="main-content"]/div/main/section/ul/li[5]/button/span/span/span'
                    next_ungraded_xpath = '//*[@id="main-content"]/div/main/section/ul/li[5]/button'
                    self.driver.find_element(By.XPATH, next_ungraded_xpath).click()
                except NoSuchElementException:
                    sleep(1)
                    page = self.get_page()
                    if page == 'grade' or page == 'review_grades':
                        return True
                    else:
                        return False
                except StaleElementReferenceException:
                    print('Stale Element, refreshing...')
                    self.driver.refresh()
                    sleep(1)
        return False

    def get_question(self, question_number):
        if self.get_page() != 'grade':
            print('Not on Grading Dashboard!')
            return False
        try:
            question_line_xpath = f'//*[@id="main-content"]/div[2]/div/div/div[{question_number + 1}]'
            question_line = self.driver.find_element(By.XPATH, question_line_xpath)
        except NoSuchElementException:
            print(f'Can\'t find question {question_number}')
            return False
        question_graded = question_line.find_element(By.XPATH, './div[3]/span').text == '100%'
        if question_graded:
            print(f'Question {question_number} already graded')
            return False
        question_line.find_element(By.XPATH, './div[1]/div/a[1]').click()
        if self.get_page() == 'answer_groups':
            grade_individually_xpath = '//*[@id="main-content"]/div/div/main/section/ul/li[2]/button'
            try:
                self.driver.find_element(By.XPATH, grade_individually_xpath).click()
                sleep(0.5)
                if self.get_page() != 'grade':
                    print(f'Question {question_number} grade individually took me to a bad place')
                    return False
            except NoSuchElementException:
                print(f'Question {question_number} can\'t click grade individually')
                return False
        return True

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
        self.section_ta_map = get_section_ta_map()

        GradescopeNavigator.__init__(self, cred_path)

    def get_distribution(self, section, assignment):
        df = []
        if self.open_section_assignment(section, assignment, 'review_grades'):
            student_index = 1
            while True:
                try:
                    score_xpath = f'//*[@id="DataTables_Table_0"]/tbody/tr[{student_index}]/td[3]'
                    graded_xpath = f'//*[@id="DataTables_Table_0"]/tbody/tr[{student_index}]/td[4]/i'
                    try:
                        score = float(self.driver.find_element(By.XPATH, score_xpath).text)
                        graded_status = self.driver.find_element(By.XPATH, graded_xpath).get_attribute('aria-label')
                        # print(graded_status)
                        graded = True if graded_status == 'Submission is graded.' else False
                        name_xpath = f'//*[@id="DataTables_Table_0"]/tbody/tr[{student_index}]/td[1]/a'
                        student_name = self.driver.find_element(By.XPATH, name_xpath).text
                        df.append({'section': section, 'ta': self.section_ta_map[section], 'assignment': assignment,
                                   'student_name': student_name, 'score': score, 'graded': graded})
                    except ValueError:
                        pass
                    student_index += 1
                except NoSuchElementException:
                    # print(f'End of course {section}')
                    break
        else:
            print(f'Couldn\'t get {section} {assignment}')

        return df


class GradescopeRubricFixer(GradescopeNavigator):
    def __init__(self, cred_path=None):
        GradescopeNavigator.__init__(self, cred_path)

    def fix_rubric_item(self, section, assignment_name, question_name, old_text, new_text=None, new_score=None):
        if self.open_section_assignment(section, assignment_name, 'rubric/edit'):
            item_index = 1
            while True:
                try:
                    item_xpath = f'//*[@id="main-content"]/div/main/div[3]/div/div/div[2]/div[{item_index}]'
                    rubric_item = self.driver.find_element(By.XPATH, item_xpath)
                    item_name = rubric_item.find_element(By.XPATH, f'./div[1]/div[1]/h2/span[2]').text
                    if item_name == question_name:
                        q_item_index = 1
                        while True:
                            try:
                                q_item_xpath = f'./div[2]/div/div[2]/div[1]/ol/li[{q_item_index}]/div/div/div[2]/div'
                                q_item_text = rubric_item.find_element(By.XPATH, q_item_xpath)
                                if q_item_text.text == f'Grading comment:\n{old_text}':
                                    if new_text is not None:
                                        q_item_text.click()
                                        question_item_text_entry = self.driver.switch_to.active_element
                                        question_item_text_entry.send_keys(Keys.CONTROL, 'a')
                                        question_item_text_entry.send_keys(Keys.DELETE)
                                        question_item_text_entry.send_keys(new_text)
                                        question_item_text_entry.send_keys(Keys.RETURN)
                                    if new_score is not None:
                                        q_item_score_xpath = f'./div[2]/div/div[2]/div[1]/ol/li[{q_item_index}]' \
                                                             f'/div/div/div[2]/button'
                                        q_item_score = rubric_item.find_element(By.XPATH, q_item_score_xpath)
                                        q_item_score.click()
                                        q_item_score_entry = self.driver.switch_to.active_element
                                        q_item_score_entry.send_keys(Keys.CONTROL, 'a')
                                        q_item_score_entry.send_keys(Keys.DELETE)
                                        q_item_score_entry.send_keys(new_score)
                                        q_item_score_entry.send_keys(Keys.RETURN)
                                    print(f'{section} - {assignment_name} - {question_name} rubric item updated: \n'
                                          f'{old_text} -> {new_text} {new_score}')
                                    break
                            except NoSuchElementException:
                                print(f'Couldn\'t find some element in rubric')
                                break
                            q_item_index += 1
                except NoSuchElementException:
                    # print(f'Didn\'t find rubric item {question_name} in {section} {assignment_name}')
                    break
                item_index += 1
        else:
            print(f'Couldn\'t get rubric for {section} {assignment_name}')

    def remove_outline_question(self, section, assignment_name, question_name):
        if self.open_section_assignment(section, assignment_name, 'outline/edit'):
            change_made = False
            item_index = 1
            while True:
                try:
                    item_xpath = f'//*[@id="main-content"]/div/main/div[3]/div[2]/div/div[2]/div[2]/div[1]/div[2]/' \
                                 f'div/div[2]/div[{item_index}]/div/div/div[2]/input'
                    question_field = self.driver.find_element(By.XPATH, item_xpath)
                    question_value = question_field.get_attribute('value')

                    if question_value == question_name:
                        question_field.click()
                        delete_xpath = f'//*[@id="main-content"]/div/main/div[3]/div[2]/div/div[2]/div[2]/div[1]/' \
                                       f'div[2]/div/div[2]/div[{item_index}]/div/div/div[4]/button[1]'
                        self.driver.find_element(By.XPATH, delete_xpath).click()
                        change_made = True
                except NoSuchElementException:
                    # print(f'Didn\'t find rubric item {question_name} in {section} {assignment_name}')
                    break
                item_index += 1
            if change_made:
                save_xpath = f'//*[@id="main-content"]/div/main/div[3]/div[2]/div/div[2]/div[2]/div[3]/button[2]'
                self.driver.find_element(By.XPATH, save_xpath).click()
                sleep(2)
        else:
            print(f'Couldn\'t get rubric for {section} {assignment_name}')


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


def get_section_id_map(prefixes=['5CL-G']):
    section_ids = {
            '5CL-G': {
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
            },
            '5AL-G': {
                1: 526796,
                2: 526799,
                3: 526800,
                4: 526801,
                5: 526805,
                6: 526806,
                7: 526807,
                8: 526809,
                9: 526812,
                10: 526813,
                11: 526814,
                12: 526815,
            },
            '5BL-G': {
                1: 526840,
                2: 526841,
                3: 526843,
                4: 526848,
                5: 526850,
                6: 526851,
                7: 526853,
                8: 526855,
                9: 526858,
                10: 526859,
                11: 526860,
                12: 526861,
                13: 526862,
                14: 526863,
                15: 526864,
                16: 526865,
                17: 526866,
                18: 526867,
                19: 526868,
            }
    }

    if type(prefixes) is not list:
        prefixes = [prefixes]

    section_id_map = {}
    for prefix in prefixes:
        section_id_map.update({f'{prefix}{section}': section_id for section, section_id in section_ids[prefix].items()})

    return section_id_map


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
