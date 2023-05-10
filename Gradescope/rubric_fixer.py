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
    assignment_name = '5C Lab 4'
    question_name = 'Parallel Circuit'
    old_text = 'Discussion of current conservation (all current measurements the same)'
    new_text = 'Discussion of current conservation (sum of light bulb currents equal to current through power supply)'
    # new_text = None
    # new_score = '-0.25'
    new_score = None
    section_flags = ['5CL-G']
    rubric_fixer = GsRF()
    for section in rubric_fixer.get_sections():
        if any(flag in section for flag in section_flags):
            print(f'\n{section}')
            rubric_fixer.fix_rubric_item(section, assignment_name, question_name, old_text,
                                         new_text=new_text, new_score=new_score)
    print('donzo')


if __name__ == '__main__':
    main()
