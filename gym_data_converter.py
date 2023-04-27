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
    exercise_map, category_map = define_maps()
    with open(old_data_path, 'r', encoding='utf-8-sig') as file:
        lines = file.readlines()
        # print(lines[:10])
        # return
        line_index = 0
        exercises = []
        unmatched_exercises = []
        fit_notes_out = []
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
                    line_text = lines[line_index].strip('\n')
                    if '* gym' in line_text.lower():
                        line_index += 1
                        if line_index >= len(lines):
                            break
                        line_text = lines[line_index].strip('\n')
                        while '   * ' in line_text:
                            exercise, exercise_fitnotes, sets, notes, bad_read = \
                                read_exercise_line(line_text, exercise_map)
                            if bad_read:
                                # print(f'Bad read: {line_text}')
                                # print(exercise, exercise_fitnotes, weight, reps, notes)
                                # print()
                                pass
                            else:
                                if exercise_fitnotes is None:
                                    unmatched_exercises.append(exercise)
                                else:
                                    category = category_map[exercise_fitnotes]
                                    notes = ', '.join(notes)
                                    sets = [(set_weight[0], rep) for set_weight in sets for rep in set_weight[1]]
                                    for set_index, (weight, rep) in enumerate(sets):
                                        distance, distance_unit, time = '', '', ''
                                        if weight is None:
                                            weight = ''
                                        if set_index != len(sets) - 1:
                                            comment = ''
                                        else:
                                            comment = notes
                                        print('\t'.join([date.strftime('%m/%d/%Y'), exercise_fitnotes, category,
                                                         str(weight), str(rep), distance, distance_unit, time,
                                                         comment]))
                            line_index += 1
                            if line_index >= len(lines):
                                break
                            line_text = lines[line_index].strip('\n')
                    if line_index >= len(lines):
                        break

    unmatched_exercises = pd.Series(unmatched_exercises).value_counts(sort=False)
    # print(unmatched_exercises)
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


def read_exercise_line(line_text, exercise_map):
    exercise, exercise_fitnotes, sets, notes, bad_read = None, None, [], [], False
    first_digit = re.search(r'\d', line_text)
    if not first_digit:
        print(f'No digits found in line! {line_text}')
        bad_read = True
    else:
        exercise = line_text[:first_digit.start()].strip(' *-').lower()
        for exercise_name, name_list in exercise_map.items():
            if exercise in name_list:
                exercise_fitnotes = exercise_name
        if exercise_fitnotes is not None:
            line_tail = line_text[first_digit.start():]
            for ele in line_tail.split(', '):
                if '-' in ele:
                    weight, reps, angle, rep_bad_read = read_rep_weight(ele)
                    sets.append([weight, reps])
                    bad_read = bad_read or rep_bad_read
                    if angle is not None:
                        notes.append(angle)
                elif is_weightless_rep(ele):
                    reps, rep_bad_read = read_reps(ele)
                    sets.append([None, reps])
                    bad_read = bad_read or rep_bad_read
                else:
                    notes.append(ele)

    return exercise, exercise_fitnotes, sets, notes, bad_read


def read_rep_weight(rep_weight_string):
    angle, weight, rep_ints, bad_read = None, None, [], False
    rep_weights = rep_weight_string.split('-')
    if len(rep_weights) != 2:
        print(f'Double "-" in line! {rep_weight_string}')
        bad_read = True
    else:
        weight_string = rep_weights[1].strip()
        weight, angle = read_weight(weight_string)

        reps_string = rep_weights[0].strip()
        rep_ints, rep_bad_read = read_reps(reps_string)
        bad_read = bad_read or rep_bad_read

    return weight, rep_ints, angle, bad_read


def read_weight(weight_string):
    weight, angle = None, None
    if '@' in weight_string:
        weight_string, angle = weight_string.split('@')
        weight_string = weight_string.strip()
        angle = angle.strip()
    if '/side' in weight_string:
        weight = 2 * float(weight_string.strip('/side'))
    elif '/handle' in weight_string:
        weight = 2 * float(weight_string.strip('/handle'))
    elif '+' in weight_string:
        weight_string = weight_string.split('+')
        if len(weight_string) == 2:
            weight = float(weight_string[0]) + float(weight_string[1])
    else:
        weight = float(weight_string)

    return weight, angle


def read_reps(reps_string):
    rep_ints, bad_read = [], False
    reps = reps_string.split(',')
    for rep in reps:
        if 'x' in rep.lower():
            rep_x = rep.lower().split('x')
            if len(rep_x) != 2:
                print(f'Too many "x"s rep split! {reps_string}')
                bad_read = True
            try:
                sets = int(rep_x[1])
                reps = int(rep_x[0])
                for i in range(sets):
                    rep_ints.append(reps)
            except ValueError:
                print(f'Bad "x" rep/set read! {reps_string}')
                bad_read = True
        else:
            try:
                rep_ints.append(int(rep))
            except ValueError:
                print(f'bad solo rep read: {reps_string}')
                bad_read = True

    return rep_ints, bad_read


def is_weightless_rep(rep_string):
    is_res = False
    if 'x' in rep_string.lower():
        rep_string = rep_string.lower().split('x')
        try:
            reps = int(rep_string[0])
            sets = int(rep_string[1])
            is_res = True
        except ValueError:
            pass

    return is_res


def define_maps():
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

    category_map = {
        'Flat Barbell Bench Press': 'Chest',
        'Overhead Press': 'Shoulders',
        'Seated Machine Fly': 'Chest',
        'Lying Triceps Extension': 'Triceps',
        'EZ-Bar Curl': 'Biceps',
        'Deadlift': 'Back',
        'Back Extension': 'Back',
        'Barbell Row': 'Back',
        'Seated Row Machine Overhand': 'Back',
        'Seated Row Machine Underhand': 'Back',
        'Rear Deltoid Machine': 'Back',
        'Dumbbell Shrug': 'Back',
        'Leg Press': 'Legs',
        'Linear Leg Press': 'Legs',
        'Lateral Dumbbell Raise': 'Shoulders',
        'Seated Leg Curl Machine': 'Legs',
        'Hanging Knee Raise': 'Abs',
        'Hanging Leg Raise': 'Abs',
        'Captain\'s Chair Leg Raises': 'Abs',
        'Captain\'s Chair Knee Raises': 'Abs',
        'Dumbbell Row': 'Back',
        'Barbell Row': 'Back',
        'Lat Pulldown': 'Back',
        'Dumbbell Curl': 'Biceps',
        'Dumbbell Concentration Curl': 'Biceps',
        'Dumbbell Hammer Curl': 'Biceps',
        'Crossbody Dumbbell Hammer Curl': 'Biceps',
        'EZ-Bar Preacher Curl': 'Biceps',
        'Flat Dumbbell Bench Press': 'Chest',
        'Flat Dumbbell Fly': 'Chest',
        'Incline Dumbbell Bench Press': 'Chest',
        'Barbell Squat': 'Legs',
        'Leg Extension Machine': 'Legs',
        'Romanian Deadlift': 'Legs',
        'Standing Calf Raise Machine': 'Legs',
        'Seated Calf Raise Machine': 'Legs',
        'Seated Dumbbell Press': 'Shoulders',
        'Seated Shoulder Press Machine': 'Shoulders',
        'Dumbbell Overhead Triceps Extension': 'Triceps',
        'EZ-Bar Skullcrusher': 'Triceps',
        'Parallel Bar Triceps Dip': 'Triceps',
        # '': [],
    }

    for key in exercise_map:
        exercise_map[key].append(key.lower())

    return exercise_map, category_map


if __name__ == '__main__':
    main()
