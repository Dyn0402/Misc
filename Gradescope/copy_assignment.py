#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on April 16 3:03 PM 2023
Created in PyCharm
Created as Misc/copy_assignment.py

@author: Dylan Neff, Dylan
"""

from GradescopeNavigator import GradescopeAssignmentDuplicator as GsAD


def main():
    copy_assignment_gn()
    print('donzo')


def copy_assignment_gn():
    copy_from_section = '5CL-G4'
    assignment_name = '5C Lab 3'
    week = 3

    gs_duplicator = GsAD()
    for section in gs_duplicator.get_sections():
        print(section)
        if gs_duplicator.duplicate_assignment(section, copy_from_section, assignment_name):
            gs_duplicator.set_assignment_due_date(section, assignment_name, week)


if __name__ == '__main__':
    main()
