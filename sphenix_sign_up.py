#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on December 16 05:20 2024
Created in PyCharm
Created as Misc/sphenix_sign_up

@author: Dylan Neff, dn277127
"""

import requests
from time import sleep
from datetime import datetime, timedelta
import pytz


def define_people_shifts():
    people = {
        'Dylan Neff': {
        'Institution': 'CEA Saclay',
        'Shifts': [
            {'Week Number': 13, 'Position': 'DAQ', 'Time': 'Night'},
            {'Week Number': 14, 'Position': 'DAQ', 'Time': 'Night'},
            {'Week Number': 15, 'Position': 'DAQ', 'Time': 'Night'},]
        },
        'Virgile Mahaut': {
            'Institution': 'CEA Saclay',
            'Shifts': [
                {'Week Number': 13, 'Position': 'DM', 'Time': 'Night'},
                {'Week Number': 14, 'Position': 'DO', 'Time': 'Night'},
                {'Week Number': 15, 'Position': 'DO', 'Time': 'Night'}, ]
        },
        'Nicole D\'Hose': {
        'Institution': 'CEA Saclay',
        'Shifts': [
            {'Week Number': 8, 'Position': 'DM', 'Time': 'Day'},]
        },
        'Audrey Francisco': {
        'Institution': 'CEA Saclay',
        'Shifts': [
            {'Week Number': 7, 'Position': 'SL', 'Time': 'Day'},
            {'Week Number': 8, 'Position': 'SL', 'Time': 'Day'},]
        },
        'Maxence Vandenbroucke': {
        'Institution': 'CEA Saclay',
        'Shifts': [
            {'Week Number': 7, 'Position': 'DO', 'Time': 'Day'},]
        },
    }
    return people


def main():
    """
    Sign up for shifts on the Sphenix Shift Signup website.
    :return:
    """
    url_base = 'https://www.sphenix.bnl.gov/ShiftSignupRun3/index.php?do=shifttable'
    start_checking_datetime = datetime(2025, 1, 6, 10, 58, 0, 0)
    nominal_start_datetime = datetime(2025, 1, 6, 12, 0, 0, 0)
    # start_checking_datetime = datetime(2025, 1, 3, 11, 10, 0, 0)
    # nominal_start_datetime = datetime(2025, 1, 3, 11, 15, 0, 0)
    start_checking_datetime = pytz.timezone('US/Eastern').localize(start_checking_datetime)
    nominal_start_datetime = pytz.timezone('US/Eastern').localize(nominal_start_datetime)

    # Wait times (seconds) depending on minutes till nominal start {min: sec}. Once the time is less than the key, wait
    # the value. If the time is greater than the largest key, wait the value of the largest key.
    failure_wait_times = {120: 5 * 60, 10.0: 2 * 60, 5.0: 60, 2.0: 20, 30.0 / 60: 5, 10.0 / 60: 2, 3.0 / 60: 1}

    shift_map = {'Position': {'SL': 20, 'DO': 30, 'DAQ': 40, 'DM': 50},
                 'Time': {'Owl': 0, 'Day': 1, 'Night': 2},
                 'Person': {'Dylan Neff': 556, 'Nicole D\'Hose': 436, 'Audrey Francisco': 435, 'Virgile Mahaut': 555,
                            'Maxence Vandenbroucke': 257},
                 'Institution': {'CEA Saclay': 'i_67'}}
    first_form_flag = '<input type=submit name="store" value="Store Results">'
    second_form_flag = '<input type="button" value="Return to Shift Signup form"'

    people_shifts = define_people_shifts()
    wait_till_checking_time(start_checking_datetime)  # Wait until the start time to start checking

    print('Starting sign up process.')
    for person, person_info in people_shifts.items():
        success = False
        while not success:
            institution_name = person_info['Institution']
            shifts = person_info['Shifts']

            person_id = shift_map['Person'][person]
            institution_id = shift_map['Institution'][institution_name]
            url = make_url(url_base, institution_id, person_id)

            shift_form_data = {}
            for shift in shifts:
                key = f"week[{shift['Week Number']}]"
                value = f"{shift_map['Position'][shift['Position']]}{shift_map['Time'][shift['Time']]}"
                shift_form_data[key] = value

            form_data = {
                "personID": person_id,
                "personName": person,
                "institutionID": institution_id.replace('i_', ''),
                "institutionName": institution_name,
                "do": "submitsignup",
                "signupType": "0",
                "signup": f"Submit Signup for {person}"  # Submit button value
            }
            form_data.update(shift_form_data)  # Add shift data to form data

            try:
                # seconds_till_nom_start = (nominal_start_datetime - datetime.now(pytz.timezone('US/Eastern'))).total_seconds()
                # if seconds_till_nom_start > 0:
                #     raise Exception(f"Too early to sign up for {person}. {seconds_till_nom_start} seconds until nominal start.")
                session = requests.Session()  # Start a session

                response = session.post(url, data=form_data)  # Submit the first form

                if response.status_code != 200 or first_form_flag not in response.text:
                    print(f"Failed to submit the first form. \nStatus code: {response.status_code}\n"
                          f"Response text:\n{response.text}")
                    raise Exception('Failed to submit first form.')  # If failed, go to wait and try again
                else:
                    print(f"First form submitted successfully for {person}!")

                del form_data['signupType']  # Remove signupType from form data and add new button for second form
                form_data['do'] = 'finalizesignup'  # Other elements are the same as the first form
                form_data['store'] = 'Store Results'

                response = session.post(url, data=form_data)  # Submit the second form

                if response.status_code != 200 or second_form_flag not in response.text:
                    print(f"Failed to submit the second form. \nStatus code: {response.status_code}\n"
                          f"Response text:\n{response.text}")
                    raise Exception('Failed to submit second form.')  # If failed, go to wait and try again
                else:
                    success = True  # If successful, move on to the next person
                    print(f"Second form submitted successfully for {person}!")
            except Exception as e:
                print(f"Exception occurred: {e}")
                wait_for_next_try(nominal_start_datetime, failure_wait_times)
                continue

    print('donzo')


def make_url(url_base, institution_id, person_id):
    return f'{url_base}&sel1={institution_id}&sel2={person_id}'


def wait_till_checking_time(start_checking_datetime):
    """
    Wait until the start checking time. Don't want to just check every second, that's a waste of resources. Instead,
    calculate how many seconds until the start time. Wait only 90% of that time, since the sleep might not be exact.
    Repeat until the current time is past the start time. Should be good to within a second or two.
    :param start_checking_datetime:
    :return:
    """
    fraction_of_full_time = 0.9
    now_eastern = datetime.now(pytz.timezone('US/Eastern'))
    print(f'{now_eastern.strftime("%Y-%m-%d %H:%M:%S")} waiting until {start_checking_datetime.strftime("%Y-%m-%d %H:%M:%S")}...')
    while datetime.now(pytz.timezone('US/Eastern')) < start_checking_datetime:
        time_till_checking = start_checking_datetime - datetime.now(pytz.timezone('US/Eastern'))
        seconds_till_recalc = int(time_till_checking.total_seconds() * fraction_of_full_time + 0.5)

        if seconds_till_recalc >= 1:
            formatted_now = datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S')
            then = datetime.now(pytz.timezone('US/Eastern')) + timedelta(seconds=seconds_till_recalc)
            formatted_then = then.strftime('%Y-%m-%d %H:%M:%S')
            print(f'{formatted_now} Waiting {seconds_till_recalc} seconds until {formatted_then}.\n')
        sleep(seconds_till_recalc)


def wait_for_next_try(nominal_start_time, failure_wait_times):
    """
    Get the wait time for a failure based on the time until nominal start time and then wait.
    :param nominal_start_time:
    :param failure_wait_times:
    :return:
    """
    time_till_nom_start = nominal_start_time - datetime.now(pytz.timezone('US/Eastern'))
    min_till_nom_start = time_till_nom_start.total_seconds() / 60

    # Get the largest key that is less than the time till nominal start
    nom_start_key = min((k for k in failure_wait_times.keys() if k >= min_till_nom_start),
                        default=max(failure_wait_times.keys()))

    wait_time = failure_wait_times[nom_start_key]

    now_eastern = datetime.now(pytz.timezone('US/Eastern'))
    now_formatted = now_eastern.strftime('%Y-%m-%d %H:%M:%S')
    print(f'{now_formatted} Failed. Minutes till nominal start: {min_till_nom_start}\n'
          f'Waiting {wait_time} seconds before trying again.\n')

    sleep(wait_time)


if __name__ == '__main__':
    main()
