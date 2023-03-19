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


def main():
    work_experience_path = 'N:/UCLA_Microsoft/OneDrive - personalmicrosoftsoftware.ucla.edu/Post_Grad_Search/' \
                           'Job_Applications/Work Experience.txt'
    sleep(2)
    pg_find_test()

    print('donzo')


class Experience:
    def __int__(self):
        pass


def read_work_experience(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    print(lines)


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
