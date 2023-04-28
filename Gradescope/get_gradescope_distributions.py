#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on April 14 8:24 PM 2023
Created in PyCharm
Created as Misc/get_gradescope_distributions

@author: Dylan Neff, Dylan
"""

import time
from time import sleep

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

import selenium.common.exceptions
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from GradescopeNavigator import GradescopeDistributionGetter as GsDG


def main():
    # selenium_test()
    gsn_get_distribution()
    # plot_lab('C:/Users/Dylan/Desktop/lab2_dists.csv')
    print('donzo')


def gsn_get_distribution():
    csv_path = 'C:/Users/Dylan/Desktop/prelab2_dists.csv'
    section_flags = ['5CL-G']
    # assignment_name = 'Week 1 Assignment & Lab Credit'
    assignment_name = '5C Pre-Lab 2'
    prelab = True
    assignment_name_alt = 'lab 1'
    distribution_getter = GsDG()
    # distribution_getter = GsDG('C:/Users/Dyn04/Desktop/Creds/gradescope_creds.txt')
    df = []
    for section in distribution_getter.get_sections():
        if any(flag in section for flag in section_flags):
            print(section)
            df_section = distribution_getter.get_distribution(section, assignment_name)
            if len(df_section) == 0:
                df_section = distribution_getter.get_distribution(section, assignment_name_alt)
            df.extend(df_section)
    distribution_getter.close()
    df = pd.DataFrame(df)
    # df.to_csv('C:/Users/Dylan/Desktop/prelab2_dists.csv', index=False)
    df.to_csv(csv_path, index=False, mode='w')
    plot_lab(csv_path, prelab)


def plot_lab(path=None, prelab=False):
    if path is None:
        path = 'C:/Users/Dylan/Desktop/lab1_dists.csv'
    df = pd.read_csv(path)

    min_grade = 0
    max_grade = 8 if prelab else 20

    fig_ungraded, ax_ungraded = plt.subplots(dpi=144)
    sns.countplot(x='ta', data=df[~df['graded']])
    ax_ungraded.set_title('Number Ungraded')

    # df = df[df['section'] != '5CL-G30']
    fig_tas, ax_tas = plt.subplots(dpi=144)
    sns.histplot(data=df, x='score', hue='ta', multiple='stack')
    ax_tas.set_title('All Grades')
    df = df[(df['score'] != min_grade) & (df['score'] != max_grade) & df['graded']]
    # df = df[(df['score'] != 0) & (df['score'] != 20)]
    # print(df[df['ta'] == 'Dylan'])
    fig_coures, ax_courses = plt.subplots(dpi=144)
    sns.histplot(data=df, x='score', hue='section')
    ax_courses.set_title('No Min/Max Grades')
    fig_coures, ax_courses = plt.subplots(dpi=144)
    sns.kdeplot(data=df, x='score', hue='section')
    sns.rugplot(data=df, x='score', hue='section')
    # for section in pd.unique(df['section']):
    #     df_section = df[df['section'] == section]
    #     sns.histplot(df_section['score'], label=section)
    # plt.legend()

    fig_tas, ax_tas = plt.subplots(dpi=144)
    sns.histplot(data=df, x='score', hue='ta', multiple='stack')
    ax_tas.set_title('No Min/Max Grades')
    fig_tas, ax_tas = plt.subplots(dpi=144)
    sns.kdeplot(data=df, x='score', hue='ta')
    sns.rugplot(data=df, x='score', hue='ta')
    # for ta_name in pd.unique(df['ta']):
    #     df_ta = df[df['ta'] == ta_name]
    #     sns.histplot(df_ta['score'], label=ta_name)
    # plt.legend()

    plt.show()


if __name__ == '__main__':
    main()
