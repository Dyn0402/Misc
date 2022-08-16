#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on August 15 7:47 PM 2022
Created in PyCharm
Created as Misc/gym_data_converter

@author: Dylan Neff, Dyn04
"""

from datetime import datetime


def main():
    old_data_path = 'C:\\Users\\Dyn04\\Downloads\\Old_Gym_Data.txt'
    with open(old_data_path, 'r', encoding='utf-8-sig') as file:
        lines = file.readlines()
        # print(lines[:10])
        # return
        line_index = 0
        while line_index < len(lines):
            line_date = lines[line_index].strip().split()
            print(f'{line_index}  {line_date}')
            date = read_date(line_date)
            if date is not None:
                while True:
                    line_index += 1
                    line_date = lines[line_index].strip().split()
                    if read_date(line_date) is not None:
                        break
                    line_text = lines[line_index].strip('\n').lower()
                    if '* gym' in line_text:
                        line_index += 1
                        line_text = lines[line_index].strip('\n').lower()
                        while '   * ' in line_text:
                            print(line_text)
                            line_index += 1
                            line_text = lines[line_index].strip('\n').lower()
                    if line_index >= len(lines):
                        break
    print('donzo')


def read_date(line):
    date = None
    if len(line) > 0:
        try:
            date = datetime.strptime(line[0], '%m/%d/%y')
        except ValueError:
            pass

    return date


if __name__ == '__main__':
    main()
