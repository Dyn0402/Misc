#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on March 16 2:12 AM 2022
Created in PyCharm
Created as Misc/daq_watch

@author: Dylan Neff, Dyn04
"""

import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from time import sleep
from winsound import Beep
from datetime import datetime as dt
from pydub import AudioSegment
from pydub.playback import play, _play_with_simpleaudio


def main():
    min_run_time = 60  # s If run not this old, don't check dead time yet
    run_stop_messages = 10  # Number of messages to check from most recent for a run stop
    run_end_window = 90  # s Consider run stopped if message no more than this old
    dead_chime = True  # If True play chime immediately after any detector goes dead, else just alarm for extended dead

    refresh_sleep = 1  # s How long to sleep at end of loop before refreshing page and checking again
    dead_thresh = 90  # % Dead time above which to consider detector dead

    beep_freq, beep_dur = 1000, 5000  # frequency (Hz) and length (ms) of beep if the script crashes
    repeat_num = 1000  # To repeat notify sound for alarm, audio buffer fails if too large, 1000 still good
    chimes = AudioSegment.from_file('C:/Windows/Media/chimes.wav')
    notify = AudioSegment.from_file('C:/Windows/Media/notify.wav') * repeat_num
    run_stop_text = 'Got the run stop request for run'
    chrome_driver_path = './chromedriver/chromedriver_win.exe'

    ser = Service(chrome_driver_path)
    op = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=ser, options=op)
    driver.get('https://online.star.bnl.gov/daq/export/daq/')
    sleep(3)  # Give some time for page to load

    xpaths = set_xpaths()
    alarm_times = set_alarm_times()

    try:  # Need audio notification if script crashes, probably a cleaner way but this works
        click_button(driver, xpaths['frames']['refresh'], xpaths['buttons']['refresh'], 8)
        alarm_playback = None
        live_det_stamps = {x: dt.now() for x in xpaths['detectors']}
        dead_det_times = {x: 0 for x in xpaths['detectors']}
        while True:
            click_button(driver, xpaths['frames']['refresh'], xpaths['buttons']['refresh'], click_pause=0.3)
            duration = read_field(driver, xpaths['frames']['header'], xpaths['info']['duration'])
            recent_run_stop = check_run_end(driver, xpaths['frames']['footer'], xpaths['info'], run_stop_text,
                                            run_end_window, run_stop_messages)
            if check_duration(duration, min_run_time) and not recent_run_stop:
                print(f'\n{dt.now()} | Running. Check dead times')
                try:
                    dets_read = read_dets(driver, xpaths['frames']['main'], xpaths['detectors'])
                except selenium.common.exceptions.StaleElementReferenceException:
                    print('Something stale in detectors?')
                    continue
                for det, dead in zip(xpaths['detectors'].keys(), dets_read):
                    dead = int(dead.strip('%'))
                    if dead > dead_thresh:
                        if dead_det_times[det] == 0 and dead_chime:
                            play(chimes)
                        dead_det_times[det] = (dt.now() - live_det_stamps[det]).total_seconds()
                    else:
                        dead_det_times[det] = 0
                        live_det_stamps[det] = dt.now()
                alarm = False
                any_dead = False
                for det, dead_time in dead_det_times.items():
                    if dead_time > 0:
                        any_dead = True
                        print(f'{det} dead for more than {dead_time}s!')
                    if dead_time > alarm_times[det]:
                        if alarm_playback is None or not alarm_playback.is_playing():
                            alarm_playback = _play_with_simpleaudio(notify)
                        alarm = True
                if not alarm:
                    if alarm_playback is not None and alarm_playback.is_playing():
                        alarm_playback.stop()
                if not any_dead:
                    print(f'All detectors alive')
            else:
                if recent_run_stop:
                    wait_reason = f'Run stopped less than {run_end_window}s ago'
                else:
                    wait_reason = f'Not running for at least {min_run_time}s yet'
                print(f'{dt.now()} | {wait_reason}, waiting...')
                if alarm_playback is not None and alarm_playback.is_playing():
                    alarm_playback.stop()
            sleep(refresh_sleep)
    except Exception as e:
        print(f'Some failure!\n{e}')
        Beep(beep_freq, beep_dur)
    sleep(2)
    driver.close()
    print('donzo')


def set_alarm_times():
    """
    Set alarm times for each detector in seconds.
    If a detector is dead for longer than its corresponding alarm time, audio alarm will sound.
    Alarm will continue until no detectors are dead.
    :return: Dictionary of alarm times
    """

    alarm_times = {
        'tof_dead': 20,
        'btow_dead': 0,
        'trigger_dead': 0,
        'etow_dead': 0,
        'esmd_dead': 0,
        'tpx_dead': 30,
        'mtd_dead': 0,
        'gmt_dead': 0,
        'l4_dead': 0,
        'etof_dead': 0,
        'itpc_dead': 30,
        'fcs_dead': 20,
        'stgc_dead': 0,
        'fst_dead': 0,
    }

    return alarm_times


def set_xpaths():
    """
    Set relevant xpaths for DAQ webpage. If webpage changes, these xpaths will have to be adjusted.
    :return: Nested dictionary of xpaths for DAQ webpage
    """

    xpaths = {
        'frames':
            {
                'refresh': '//*[@id="left"]',
                'main': '//*[@id="main"]',
                'header': '//*[@id="header"]',
                'footer': '//*[@id="footer"]',
            },
        'buttons':
            {'refresh': '//*[@id="reload"]'},
        'info':
            {
                'duration': '//*[@id="duration"]',
                'message_time_col': 1,
                'message_text_col': 7,
                'message_first_index': 2,
                'messages': lambda row, col: f'//*[@id="tb"]/tbody/tr[{row}]/td[{col}]',
            },
        'detectors':
            {
                'tof_dead': '//*[@id="det"]/tbody/tr[2]/td[3]',
                'btow_dead': '//*[@id="det"]/tbody/tr[3]/td[3]',
                'trigger_dead': '//*[@id="det"]/tbody/tr[4]/td[3]',
                'etow_dead': '//*[@id="det"]/tbody/tr[5]/td[3]',
                'esmd_dead': '//*[@id="det"]/tbody/tr[6]/td[3]',
                'tpx_dead': '//*[@id="det"]/tbody/tr[7]/td[3]',
                'mtd_dead': '//*[@id="det"]/tbody/tr[8]/td[3]',
                'gmt_dead': '//*[@id="det"]/tbody/tr[9]/td[3]',
                'l4_dead': '//*[@id="det"]/tbody/tr[10]/td[3]',
                'etof_dead': '//*[@id="det"]/tbody/tr[11]/td[3]',
                'itpc_dead': '//*[@id="det"]/tbody/tr[12]/td[3]',
                'fcs_dead': '//*[@id="det"]/tbody/tr[13]/td[3]',
                'stgc_dead': '//*[@id="det"]/tbody/tr[14]/td[3]',
                'fst_dead': '//*[@id="det"]/tbody/tr[15]/td[3]',
            },
    }

    return xpaths


def switch_frame(driver, xframe):
    """
    # Switch to xframe, returning to top level frame first. This seems to take longer than other actions?
    :param driver: Selenium driver
    :param xframe: Xpath of frame to switch to
    :return:
    """

    driver.switch_to.default_content()
    frame = driver.find_element(By.XPATH, xframe)
    driver.switch_to.frame(frame)


def click_button(driver, xframe, xbutton, num_click=1, click_pause=0.2):
    """
    Click button at xbutton xpath. Click num_click times with click_pause wait in between.
    :param driver: Chrome driver to webpage
    :param xframe: xpath for frame the button is in
    :param xbutton: xpath for the button
    :param num_click: Number of times to click button
    :param click_pause: Lenghth of time to pause between button clicks (seconds)
    :return:
    """

    switch_frame(driver, xframe)
    button = driver.find_element(By.XPATH, xbutton)
    for i in range(num_click):
        button.click()
        sleep(click_pause)


def read_field(driver, xframe, xfield):
    """
    Read text of given field
    :param driver: Chrome driver for webpage
    :param xframe: xpath for frame field is in
    :param xfield: xpath for field
    :return:
    """

    switch_frame(driver, xframe)
    field = driver.find_element(By.XPATH, xfield)
    return field.text


def read_dets(driver, xframe, xdets):
    """
    Read each detector dead time in xdets. Return these dead times
    :param driver: Chrome driver for webpage
    :param xframe: xpath to frame the detector dead times are in
    :param xdets: Dictionary of {detector names: detector dead time xpaths}
    :return: Dictionary of {detector names: detector dead times}
    """

    switch_frame(driver, xframe)
    dets_read = []
    for det, xdet in xdets.items():
        dets_read.append(driver.find_element(By.XPATH, xdet).text)
    return dets_read


def check_duration(duration, min_s):
    """
    Check if run duration field is in running state and longer than min_s seconds
    :param duration: Duration string from DAQ Monitor field
    :param min_s: Minimum number of seconds running. Return false if running time less than this
    :return: True if running for longer than min_s, else False
    """

    duration = duration.split(',')
    if len(duration) == 4:
        duration = [int(x.strip().strip(y)) for x, y in zip(duration, [' days', ' hr', ' min', ' s'])]
        duration = duration[0] * 24 * 60 * 60 + duration[1] * 60 * 60 + duration[2] * 60 + duration[3]  # Convert to s
        if duration > min_s:
            return True
    return False


def check_run_end(driver, xframe, xinfos, run_stop_text, run_end_window, num_messages=5):
    """
    Check to see if the run has ended recently
    :param driver: Chrome driver to webpage
    :param xframe: xpath for frame of the daq messages
    :param xinfos: Dictionary of info which includes xpaths for DAQ messages
    :param run_stop_text: String indicating a run stop message on the DAQ
    :param run_end_window: Window in which to consider run recently stopped (seconds)
    :param num_messages: Number of messages in the DAQ to check for run stop message
    :return: True if run stopped recently, False if not
    """

    switch_frame(driver, xframe)
    for message_num in range(num_messages):
        row_index = xinfos['message_first_index'] + message_num
        message = driver.find_element(By.XPATH, xinfos['messages'](row_index, xinfos['message_text_col'])).text
        if message[:len(run_stop_text)] == run_stop_text:
            stop_time = driver.find_element(By.XPATH, xinfos['messages'](row_index, xinfos['message_time_col'])).text
            stop_time = dt.combine(dt.now().date(), dt.strptime(stop_time, '%H:%M:%S').time())
            stopped_seconds = (dt.now() - stop_time).total_seconds()
            while stopped_seconds < 0:
                stopped_seconds += 24 * 60 * 60  # Correct for wrongly assuming message time is today. Get nearest day.
            if stopped_seconds < run_end_window:
                return True
    return False


if __name__ == '__main__':
    main()
