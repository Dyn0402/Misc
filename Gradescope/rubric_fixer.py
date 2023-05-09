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
    assignment_name = '5C Lab 5'
    question_name = 'LED'
    old_text = 'Linear fit clearly bad or fit using all points'
    section_flags = ['5CL-G']
    rubric_fixer = GsRF()
    for section in rubric_fixer.get_sections():
        if any(flag in section for flag in section_flags):
            print(f'\n{section}')
            rubric_fixer.fix_rubric_item(section, assignment_name, question_name, old_text, new_text=None,
                                         new_score='-0.25')
    print('donzo')


if __name__ == '__main__':
    main()
