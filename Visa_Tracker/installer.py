#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on July 05 6:28 PM 2023
Created in PyCharm
Created as Misc/installer

@author: Dylan Neff, Dylan
"""

import PyInstaller.__main__
import shutil


def main():
    # Using pyinstaller 5.11.0
    version_name = 'visa_tracker_v1'
    PyInstaller.__main__.run([
        'main.py',
        '-y',
        f'-n {version_name}'
    ])

    try:
        shutil.rmtree(f'./dist/{version_name}')
    except FileNotFoundError:
        pass
    shutil.move(f'./dist/ {version_name}', f'./dist/{version_name}')  # Get rid of pyinstaller weird space
    shutil.copy('C:/Users/Dylan/Desktop/wamessenger_data.txt', f'./dist/{version_name}/wamessenger_data.txt')

    print('donzo')


if __name__ == '__main__':
    main()
