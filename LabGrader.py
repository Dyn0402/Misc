# -*- coding: utf-8 -*-
"""
Created on Tue Apr 03 13:54:50 2018

@author: Dyn04
"""


import pyautogui as pg
import time


def main():
    pars = initialize()
    grade(pars)
    print('donzo')
    
    
def initialize():
    # submissions = [29, 29, 28]  #Number of submissions
    submissions = [10, 12, 9]
    tabs = 3  # Number of lab sections and therefore browser tabs.
    # questions = [['1','2','3','4','5'],
    #             ['1','2','3','4','5']] #Key stokes for each question
    # questions = [['1', '4']]
    questions = [['1'],
                 ['1'],
                 ['1'],
                 ['1'],
                 ['1'],
                 ['1'],
                 ['1'],
                 ['1']]
    # questions = [['3'],
    #             ['3'],
    #             ['1'],
    #             ['1'],
    #             ['1'],
    #             ['1'],
    #             ['1'],
    #             ['1'],
    #             ['1']]
    wait_time = 2.5  # seconds to delay for next question/submission to load
    next_sub = 'z'  # Hotkey for next ungraded exam
    next_q = '.'  # Hotkey for next question
    tab_hot_key = ['ctrl', 'tab']  # Hotkey for next browser tab.
    x = 300  # Initilizing click x position
    y = 200  # Initilizing click y position
    
    pars = {'Submissions': submissions, 'Questions': questions,
            'WaitTime': wait_time, 'NextSub': next_sub, 'Tabs': tabs,
            'TabHotKey': tab_hot_key, 'NextQ': next_q, 'x': x, 'y': y}
    
    return pars


def grade(pars):
    pg.click(x=pars['x'], y=pars['y'])
    
    for subs in pars['Submissions']:
        for question in pars['Questions']:
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


if __name__ == '__main__':
    main()
