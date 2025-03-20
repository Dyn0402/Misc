#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on March 20 15:22 2025
Created in PyCharm
Created as Misc/search_indico

@author: Dylan Neff, dn277127
"""

import numpy as np
import matplotlib.pyplot as plt

import requests


def main():
    for i in range(20000, 27124):
        base_url = f'https://indico.bnl.gov/event/{i}/'
        # Request page and print html
        page = requests.get(base_url)
        # print(page)
        # Print html content
        # print(page.content)
        speaker = 'Oskar Hartbrich'

        # Find speaker in html
        if speaker in page.content.decode('utf-8'):
            print(f'{speaker} is speaking at this event {i}.')
        else:
            print(f'{speaker} is not speaking at this event {i}.')
    print('donzo')


if __name__ == '__main__':
    main()
