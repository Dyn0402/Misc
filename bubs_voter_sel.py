#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on March 30 10:24 AM 2020
Created in PyCharm
Created as Misc/bubs_voter_sel.py

@author: Dylan Neff, dylan
"""

import time
from selenium import webdriver
from BubsVoter import BubsVoter


def main():
    voter = BubsVoter()
    voter.vote()
    print('donzo')


def pizza_test():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('start-maxamized')
    chrome_options.add_argument('disable-infobars')
    driver = webdriver.Chrome('/home/dylan/Software/Web_Driver/chromedriver_linux64/chromedriver', options=chrome_options)
    driver.get('https://www.cincinnatimagazine.com/pizzamadness/')
    time.sleep(5)
    # input()
    #"//button[contains(@class,'Matchup-voteBar-voteButton') and contains(@aria-label,'Vote for Bub's Pizza Bar')]"  [@class='Matchup-voteBar-voteButton']
    # /html/body/div[1]/div[1]/div[7]/div[1]/div[2]/div/div[4]/form[2]/div[1]/div[2]/div[1]/div[2]/div[7]/div/div[2]/button
    # /html/body/div[1]/div[1]/div[7]/div[1]/div[2]/div/div[4]/form[2]/div[1]/div[2]/div[1]/div[2]/div[7]/div/div[2]/button
    # //*[@id="iFrameResizer0"]

    # /html/body/div[1]/div[1]/div[7]/div[1]/div[2]/div/div[4]/form[2]/div[1]/div[2]/div[1]/div[2]/div[7]/div/div[2]/button
    # body > div.VotionApp > div.BracketContainer > div.ContentArea.is-contentVisible > div.ContentArea-content > div.ContentPane.MatchupContentPane.is-visible > div > div.Matchups-round.is-visible > form:nth-child(4) > div.Matchup-content > div.Matchup-competitors > div.Matchup-competitorsMediaContainer > div.Matchup-competitor.var-left > div.Matchup-openForSelecting.Matchup-voteButtonContainer > div > div.SubmitButton-button > button
    # document.querySelector("body > div.VotionApp > div.BracketContainer > div.ContentArea.is-contentVisible > div.ContentArea-content > div.ContentPane.MatchupContentPane.is-visible > div > div.Matchups-round.is-visible > form:nth-child(4) > div.Matchup-content > div.Matchup-competitors > div.Matchup-competitorsMediaContainer > div.Matchup-competitor.var-left > div.Matchup-openForSelecting.Matchup-voteButtonContainer > div > div.SubmitButton-button > button")
    # button[@class='Matchup-voteBar-voteButton']
    iframes = driver.find_elements_by_xpath("//iframe[@id='iFrameResizer0']")
    print(iframes)
    driver.switch_to.frame(iframes[0])
    # vote_buttons = driver.find_elements_by_xpath("//button[@class='Matchup-voteBar-voteButton']")
    vote_buttons = driver.find_elements_by_xpath("//html//body//div[1]//div[1]//div[7]//div[1]//div[2]//div//div[4]//form[2]//div[1]//div[2]//div[1]//div[2]//div[7]//div//div[2]//button")
    print(vote_buttons)
    print(len(vote_buttons))
    vote_buttons[0].click()
    time.sleep(5)
    user_name_inputs = driver.find_elements_by_xpath('//*[@id="register-username"]')
    print(user_name_inputs)
    user_name_inputs[0].clear()
    user_name_inputs[0].send_keys("garywashere22")
    email_inputs = driver.find_elements_by_xpath('//*[@id="register-email"]')
    time.sleep(1)
    print(email_inputs)
    email_inputs[0].clear()
    email_inputs[0].send_keys("garywdafashere@gary.com")
    password_inputs = driver.find_elements_by_xpath('//*[@id="register-password"]')
    time.sleep(1)
    print(password_inputs)
    password_inputs[0].clear()
    password_inputs[0].send_keys("garygaraygagarygagy")
    submit_buttons = driver.find_elements_by_xpath("//html//body//div[1]//div[1]//div[7]//div[1]//div[3]//form//div[6]//div//div[2]//button")
    time.sleep(1)
    print(submit_buttons)
    submit_buttons[0].click()
    time.sleep(5)
    highlight(vote_buttons[0], 3, 'blue', 5)

    # iframes = driver.find_elements_by_css_selector('button.Matchup-voteBar-voteButton')

    # bubs_vote_button.click()
    # time.sleep(5)  # Let the user actually see something!
    driver.quit()
    print('donzo')


def highlight(element, effect_time, color, border):
    """Highlights (blinks) a Selenium Webdriver element"""
    driver = element._parent

    def apply_style(s):
        driver.execute_script("arguments[0].setAttribute('style', arguments[1]);",
                              element, s)
    original_style = element.get_attribute('style')
    apply_style("border: {0}px solid {1};".format(border, color))
    time.sleep(effect_time)
    apply_style(original_style)


def sel_test():
    driver = webdriver.Chrome('/home/dylan/Software/Web_Driver/chromedriver_linux64/chromedriver')  # Optional argument, if not specified will search path.
    driver.get('http://www.google.com/xhtml');
    time.sleep(5) # Let the user actually see something!
    search_box = driver.find_element_by_name('q')
    print(search_box)
    search_box.send_keys('ChromeDriver')
    search_box.submit()
    time.sleep(5) # Let the user actually see something!
    driver.quit()


if __name__ == '__main__':
    main()
