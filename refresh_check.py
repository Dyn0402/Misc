#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on November 21 10:19 PM 2020
Created in PyCharm
Created as Misc/refresh_check

@author: Dylan Neff, Dylan
"""


import pyautogui
import win32clipboard as winclip
from time import sleep
from winsound import Beep


def main():
    sleep(3)
    stop = False
    iters = 0
    while not stop:
        sleep(2)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.hotkey('ctrl', 'c')
        sleep(0.1)
        winclip.OpenClipboard()
        page = str(winclip.GetClipboardData())
        winclip.CloseClipboard()
        str_start = page.find('$399.99')
        str_range = page[str_start:str_start+30]
        if 'new at target' in str_range:
            print(f'yes {iters}')
        else:
            print('no')
            stop = True
            Beep(1000, 5000)
        iters += 1
        pyautogui.press('f5')
    print('donzo')


if __name__ == '__main__':
    main()
