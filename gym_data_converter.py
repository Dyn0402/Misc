#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on August 15 7:47 PM 2022
Created in PyCharm
Created as Misc/gym_data_converter

@author: Dylan Neff, Dyn04
"""

from datetime import datetime
import re
import pandas as pd
import matplotlib.pyplot as plt


def main():
    old_data_path = 'E:\\Transfer\\Old_Gym_Data.txt'
    exercise_map = define_exercise_map()
    with open(old_data_path, 'r', encoding='utf-8-sig') as file:
        lines = file.readlines()
        # print(lines[:10])
        # return
        line_index = 0
        exercises = []
        unmatched_exercises = []
        while line_index < len(lines):
            line_date = lines[line_index].strip().split()
            # print(f'{line_index}  {line_date}')
            date = read_date(line_date)
            if date is not None:
                while True:
                    line_index += 1
                    if line_index >= len(lines):
                        break
                    line_date = lines[line_index].strip().split()
                    if read_date(line_date) is not None:
                        break
                    line_text = lines[line_index].strip('\n').lower()
                    if '* gym' in line_text:
                        line_index += 1
                        if line_index >= len(lines):
                            break
                        line_text = lines[line_index].strip('\n').lower()
                        while '   * ' in line_text:
                            first_digit = re.search(r'\d', line_text)
                            if first_digit:
                                exercise = line_text[:first_digit.start()].strip(' *-')
                                matched = False
                                for exercise_name, name_list in exercise_map.items():
                                    if exercise in name_list:
                                        matched = True
                                        line_tail = line_text[first_digit.start():]
                                        # print(f'{exercise_name} {exercise}')
                                        # print(line_tail.split(', '))
                                        for ele in line_tail.split(', '):
                                            if '-' in ele:
                                                ele = ele.split('-')
                                                rep_ints = []
                                                if len(ele) == 2:
                                                    reps = ele[0].strip()
                                                    reps = reps.split(',')
                                                    for rep in reps:
                                                        if 'x' in rep:
                                                            rep_x = rep.split('x')
                                                            if len(rep_x) == 2:
                                                                try:
                                                                    int(rep_x[1])
                                                                except ValueError:
                                                                    print(line_text)
                                                                for i in range(int(rep_x[1])):
                                                                    try:
                                                                        rep_ints.append(int(rep_x[0]))
                                                                    except ValueError:
                                                                        print(f'Bad comma rep read: {line_text}')
                                                        else:
                                                            try:
                                                                rep_ints.append(int(rep))
                                                            except ValueError:
                                                                print(f'bad solo rep read: {line_text}')
                                                    # print(rep_ints)

                                                    weight = ele[1].strip()
                                                    angle = None
                                                    if '@' in weight:
                                                        weight, angle = weight.split('@')
                                                        weight = weight.strip()
                                                        angle = angle.strip()
                                                    if '/side' in weight:
                                                        weight = 2 * float(weight.strip('/side'))
                                                    elif '/handle' in weight:
                                                        weight = 2 * float(weight.strip('/handle'))
                                                    elif '+' in weight:
                                                        weight = weight.split('+')
                                                        if len(weight) == 2:
                                                            weight = float(weight[0]) + float(weight[1])
                                                    else:
                                                        weight = float(weight)
                                                print(rep_ints, weight)
                                        break
                                if not matched:
                                    unmatched_exercises.append(exercise)
                            else:
                                print(f'No Digit Found!  {line_text}')
                            # print(line_text)
                            line_index += 1
                            if line_index >= len(lines):
                                break
                            line_text = lines[line_index].strip('\n').lower()
                    if line_index >= len(lines):
                        break

    unmatched_exercises = pd.Series(unmatched_exercises).value_counts(sort=False)
    print(unmatched_exercises)
    unmatched_exercises.plot(kind='barh')

    plt.show()
    print('donzo')


def read_date(line):
    date = None
    if len(line) > 0:
        try:
            date = datetime.strptime(line[0], '%m/%d/%y')
        except ValueError:
            pass

    return date


def define_exercise_map():
    exercise_map = {
        'Flat Barbell Bench Press': ['bench'],
        'Overhead Press': [],
        'Seated Machine Fly': ['pectoral fly machine', 'pectoral fly machine max'],
        'Lying Triceps Extension': [],
        'EZ-Bar Curl': ['barbell curl'],
        'Deadlift': ['dead lift'],
        'Back Extension': ['back extensions'],
        'Barbell Row': [],
        'Seated Row Machine Overhand': ['seated row overhand'],
        'Seated Row Machine Underhand': ['seated row underhand'],
        'Rear Deltoid Machine': ['rear deltoid'],
        'Dumbbell Shrug': ['shrugs'],
        'Leg Press': ['seated leg press'],
        'Linear Leg Press': [],
        'Lateral Dumbbell Raise': ['lateral raise'],
        'Seated Leg Curl Machine': ['leg curls', 'seated leg curl', 'leg curl machine'],
        'Hanging Knee Raise': [],
        'Hanging Leg Raise': [],
        'Captain\'s Chair Leg Raises': [],
        'Captain\'s Chair Knee Raises': ['captain\'s chair weighted knee raise'],
        'Dumbbell Row': ['dumbbell rows'],
        'Barbell Row': ['barbell rows'],
        'Lat Pulldown': [],
        'Dumbbell Curl': [],
        'Dumbbell Concentration Curl': ['concentration curl'],
        'Dumbbell Hammer Curl': ['hammer curl'],
        'Crossbody Dumbbell Hammer Curl': ['crossbody hammer curl'],
        'EZ-Bar Preacher Curl': ['preacher curl'],
        'Flat Dumbbell Bench Press': ['dumbbell flat bench press'],
        'Flat Dumbbell Fly': ['dumbbell fly'],
        'Incline Dumbbell Bench Press': ['dumbbell incline bench press'],
        'Barbell Squat': ['squats'],
        'Leg Extension Machine': ['leg extensions'],
        'Romanian Deadlift': [],
        'Standing Calf Raise Machine': ['standing calf raise'],
        'Seated Calf Raise Machine': ['horizontal calf machine'],
        'Seated Dumbbell Press': ['dumbbell shoulder press'],
        'Seated Shoulder Press Machine': ['dumbbell shoulder press machine', 'shoulder press machine'],
        'Dumbbell Overhead Triceps Extension': ['overhead extension'],
        'EZ-Bar Skullcrusher': ['lying tri extensions'],
        'Parallel Bar Triceps Dip': ['dips'],
        # '': [],
    }

    for key in exercise_map:
        exercise_map[key].append(key.lower())

    return exercise_map


if __name__ == '__main__':
    main()
