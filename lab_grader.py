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


if __name__ == '__main__':
    main()
