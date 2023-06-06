#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on April 25 8:21 PM 2023
Created in PyCharm
Created as Misc/rubric_fixer

@author: Dylan Neff, Dylan
"""

import numpy as np
import matplotlib.pyplot as plt

from GradescopeNavigator import GradescopeRubricFixer as GsRF


def main():
    # fix_rubric_item()
    remove_outline_question()
    print('donzo')


def fix_rubric_item():
    assignment_name = '5C Lab 6'
    question_name = 'Capacitors in Parallel'
    old_text = 'Correctly identify capacitors in series decreases capacitance'
    new_text = 'Correctly identified capacitors in parallel increases capacitance'
    # new_text = None
    # new_score = '+2.6'
    new_score = None
    section_flags = ['5CL-G']
    rubric_fixer = GsRF()
    for section in rubric_fixer.get_sections():
        if any(flag in section for flag in section_flags):
            print(f'\n{section}')
            rubric_fixer.fix_rubric_item(section, assignment_name, question_name, old_text,
                                         new_text=new_text, new_score=new_score)


def remove_outline_question():
    assignment_name = 'Attendance/Participation/LA Survey Adjustments'
    question_name = 'End-Quarter LA Survey (Extra Credit)'
    section_flags = ['5BL-G', '5AL-G']
    rubric_fixer = GsRF()
    for section in rubric_fixer.get_sections(section_flags):
        if any(flag in section for flag in section_flags):
            print(f'\n{section}')
            rubric_fixer.remove_outline_question(section, assignment_name, question_name)


if __name__ == '__main__':
    main()
