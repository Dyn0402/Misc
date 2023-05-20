#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on April 16 3:03 PM 2023
Created in PyCharm
Created as Misc/copy_assignment.py

@author: Dylan Neff, Dylan
"""

from GradescopeNavigator import GradescopeAssignmentDuplicator as GsAD
from selenium.webdriver.common.by import By


def main():
    copy_assignment_gn()
    # due_date_test()
    print('donzo')


def copy_assignment_gn():
    copy_from_section = '5CL-G4'
    week = 7
    # assignment_name = f'5C Lab {week}'
    assignment_name = f'5C Pre-Lab {week}'

    gs_duplicator = GsAD()
    for section in gs_duplicator.get_sections():
        print(section)
        # if section != '5CL-G5':
        #     continue
        if gs_duplicator.duplicate_assignment(section, copy_from_section, assignment_name):
            gs_duplicator.set_assignment_due_date(section, assignment_name, week)


def due_date_test():
    gs_dup = GsAD()
    gs_dup.set_assignment_due_date('5CL-G5', 'Pre-Lab 4', 4)


if __name__ == '__main__':
    main()
