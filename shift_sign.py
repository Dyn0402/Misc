#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on October 18 3:26 PM 2021
Created in PyCharm
Created as QGP_Scripts/shift_sign

@author: Dylan Neff, dylan
"""

import numpy as np
import matplotlib.pyplot as plt
import pyautogui as pg
from time import sleep
from pynput import keyboard
from pynput import mouse


def main():
    with keyboard.Listener(on_press=u_press) as listener:
        listener.join()
    with mouse.Listener(on_click=click) as listener:
        listener.join()
    with mouse.Listener(on_click=click) as listener:
        listener.join()

    print('donzo')


def u_press(key):
    try:
        print(f'key is {key.char}')
        if key.char == 'u':
            navigate()
            return False
    except AttributeError:
        pass
        # print('bad key')


def click(x, y, button, pressed):
    sign_up()
    return False


def navigate():
    pg.press('down', presses=3)
    # pg.press('down')
    # pg.press('down')
    pg.press('tab')
    pg.press('tab')
    pg.press('down', presses=5)
    # pg.press('down')
    # pg.press('down')
    # pg.press('down')
    # pg.press('down')
    pg.press('tab', presses=2)
    # pg.press('tab')
    pg.press('enter')
    # sleep(1)
    # pg.press('pagedown', presses=5)


def sign_up():
    pg.press('tab', presses=2)
    pg.press('space')


if __name__ == '__main__':
    main()
