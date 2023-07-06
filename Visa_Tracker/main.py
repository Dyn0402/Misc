#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on July 05 6:29 PM 2023
Created in PyCharm
Created as Misc/main

@author: Dylan Neff, Dylan
"""

from VisaTracker import VisaTracker


def main():
    tracker = VisaTracker()
    tracker.start_new_booking()
    tracker.check_appointment()


if __name__ == '__main__':
    main()
