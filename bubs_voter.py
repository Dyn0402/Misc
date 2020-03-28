#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on March 28 1:51 PM 2020
Created in PyCharm
Created as Misc/bubs_voter

@author: Dylan Neff, Dyn04
"""


import pyautogui as pg
import webbrowser
from time import sleep


def main():
    open_site()
    click_vote()
    make_account()
    vote()
    close()
    print('donzo')


def open_site():
    url = 'https://www.cincinnatimagazine.com/pizzamadness/'
    chrome_path = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s'
    webbrowser.get(chrome_path).open(url, new=1, autoraise=True)


def click_vote():
    bubs_button = find_bubs_button()
    print(bubs_button)
    # print("Here0")
    # bubs_button = pg.locateOnScreen('bubs_vote_button.png', grayscale=True)
    # print("Here1")
    # print(bubs_button)


def find_bubs_button():
    sleep(3)
    for i in range(4):
        pg.press('pagedown')
    sleep(0.5)
    bubs_button = pg.locateCenterOnScreen('bubs_vote_button.png')
    # while bubs_button is None:
    #     pg.press('pagedown')
    #     sleep(0.2)
    #     bubs_button = pg.locateCenterOnScreen('bubs_vote_button.png')

    return bubs_button


def make_account():
    pass


def vote():
    pass


def close():
    pass


if __name__ == '__main__':
    main()
