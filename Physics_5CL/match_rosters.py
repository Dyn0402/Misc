#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on June 13 3:47 PM 2023
Created in PyCharm
Created as Misc/match_rosters

@author: Dylan Neff, Dylan
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


def main():
    base_path = 'N:/UCLA_Microsoft/OneDrive - personalmicrosoftsoftware.ucla.edu/Tablet_Store/UCLA/TA/Phys 5CL/' \
                'Spring_2023/Final_Grades/'
    section = 5
    roster_file = f'5CL_G0{section}.xlsx'
    roster_sheet = f'G0{section}'
    grade_file = f'5CL-G{section}_Spring_2023_grades.xlsx'
    grade_sheet = 'Name_Grade'

    match_threshold = 0.51  # Percentage of names matching above which to declare a match

    df_roster = pd.read_excel(f'{base_path}{roster_file}', sheet_name=roster_sheet, header=1)
    df_grade = pd.read_excel(f'{base_path}{grade_file}', sheet_name=grade_sheet)

    unmatch_warnings = []
    for index_grade, row_grade in df_grade.iterrows():
        matched = False
        name_grade = row_grade['Name']
        name_grade_set = set([x.strip(',').lower() for x in name_grade.split()])
        for index_roster, row_roster in df_roster.iterrows():
            name_roster = row_roster['Name (Last, First)']
            name_roster_set = set([x.strip(',').lower() for x in name_roster.split()])
            common_words = len(name_grade_set.intersection(name_roster_set))
            match_percent = float(common_words) / min(len(name_grade_set), len(name_roster_set))
            if match_percent > match_threshold:
                df_roster.at[index_roster, 'Grade'] = row_grade['Grade']
                matched = True
                break
        if not matched:
            unmatch_warnings.append(f'{name_grade} not matched! {row_grade["Grade"]}')

    print(df_grade)
    print(df_roster)
    print()

    for index_roster, row_roster in df_roster.iterrows():
        print(row_roster['Grade'])

    print()
    for warn in unmatch_warnings:
        print(warn)

    print('donzo')


if __name__ == '__main__':
    main()
