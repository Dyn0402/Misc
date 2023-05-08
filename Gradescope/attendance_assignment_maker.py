#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on May 02 2:51 PM 2023
Created in PyCharm
Created as Misc/attendance_assignment_maker

@author: Dylan Neff, Dylan
"""

import numpy as np
import matplotlib.pyplot as plt
import os
import shutil
from time import sleep
import pandas as pd

import docx
from docx2pdf import convert

from GradescopeNavigator import GradescopeAssignmentDuplicator as GsAD


def main():
    # section_open_check()
    # get_roster_check()
    make_attendance_assignments()
    print('donzo')


def make_attendance_assignments():
    copy_from_section = '5CL-G4'
    assignment_name = 'Attendance/Participation/LA Survey Adjustments'
    pdf_repo_path = 'C:/Users/Dylan/Desktop/gradescope_pdfs/'
    nav = GsAD()
    for section in nav.get_sections(['5BL-G', '5CL-G']):
        # if section == '5CL-G5':
        print(f'Starting {section}...')
        if nav.duplicate_assignment(section, copy_from_section, assignment_name):
            roster = pd.DataFrame(nav.get_roster(section, False))
            roster = roster[roster['role'] == 'Student']
            section_pdf_path = f'{pdf_repo_path}{section}/'
            make_pdfs(roster, section_pdf_path, False)
            nav.upload_submissions(section, assignment_name, section_pdf_path, roster.name)
        print(f'Finished {section}\n')


def make_pdfs(roster, pdf_repo_path, write_student_id=True):
    # Delete the directory if it exists
    if os.path.exists(pdf_repo_path):
        shutil.rmtree(pdf_repo_path)

    # Recreate the directory
    os.mkdir(pdf_repo_path)

    for index, row in roster.iterrows():
        # Create a new Word document
        name = row['name']
        if write_student_id:
            student_id = row['student_id']
        doc_path = f'{pdf_repo_path}{name}.docx'
        document = docx.Document()

        # Add a centered heading to the document
        content = f'{name}\n\n{student_id}' if write_student_id else name
        heading = document.add_paragraph(content)
        heading.alignment = docx.enum.text.WD_ALIGN_PARAGRAPH.CENTER
        heading.style = document.styles['Normal']

        # Modify the font settings of the heading
        heading_font = heading.style.font
        heading_font.size = docx.shared.Pt(20)
        # heading_font.name = 'Bradley Hand ITC'
        heading_font.bold = False

        # Save the document
        document.save(doc_path)

    convert(pdf_repo_path)


def section_open_check():
    nav = GsAD()
    nav.open_section('5CL-G1', 'memberships')
    sleep(5)


def get_roster_check():
    nav = GsAD()
    df = nav.get_roster('5CL-G1')
    print(pd.DataFrame(df))


if __name__ == '__main__':
    main()
