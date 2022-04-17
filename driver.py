import traceback
import time
import pickle
import smtplib
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from config import *

chrome_options = Options()
chrome_options.add_argument("--headless")

driver = Chrome(options=chrome_options)

emailtext = """\
From: %s
To: %s
Subject: SkywardBot

MSG""" % (FROM_EMAIL, TO_EMAIL)

def check_grades():
  print('Checking for new grades...')

  try:
    driver.get('https://www2.nwrdc.wa-k12.net/scripts/cgiip.exe/WService=wmercers71/fwemnu01.w')
    driver.find_elements_by_id("login")[0].send_keys(SKYWARD_USERNAME)
    driver.find_elements_by_id("password")[0].send_keys(SKYWARD_PASSWORD)
    driver.find_elements_by_id("bLogin")[0].click()
    time.sleep(2)
    driver.switch_to.window(driver.window_handles[1])

    # Click "Gradebook"
    driver.find_elements_by_xpath("//a[@class='sf_navMenuItem']")[2].click()

    time.sleep(2) # TODO - while True loop until doesn't return no element found exception?

    classes = driver.find_elements_by_xpath("//a[@id='showGradeInfo' and @data-bkt='SEM 1']") # NOTE update for SEM 2

    index = 0
    for class_grade in classes:
      class_grade.click()

      time.sleep(2)

      instructor = driver.find_element_by_xpath('//span[@class="fXs"]//parent::span/a[2]').text

      assignments = []

      for assignment in driver.find_elements_by_xpath("//a[@id='showAssignmentInfo']"): # includes every single class for some reason
        if assignment.text:
          assignments.append(assignment.text)

      current_assignments = []

      try:
        f = open(instructor + str(index) + ".dump", 'rb')
      
        current_assignments = pickle.load(f)
        
        f.close()
      except FileNotFoundError:
        pass

      diff = list(set(assignments) - set(current_assignments))

      if len(diff) > 0:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(FROM_EMAIL, EMAIL_PASSWORD) # app-specific generated password

        for assignment in diff:
          grade = ''

          try:
            grade = driver.find_elements_by_xpath("//a[text() = '%s']/parent::td/parent::tr/td[@class='aRt']" % assignment)[1].text
          except IndexError:
            continue

          parts = grade.split(' out of ')

          msg = emailtext.replace('MSG', '%s has just graded %s as %s, or %s%%.' % (instructor, assignment, grade, str(round(float(parts[0]) / float(parts[1]) * 100, 2))))

          server.sendmail(FROM_EMAIL, TO_EMAIL, msg)

        server.close()
      
        f = open(instructor + str(index) + ".dump", 'wb')

        pickle.dump(assignments, f)

        f.close()
      
      close_buttons = driver.find_elements_by_class_name('sf_DialogClose')

      close_buttons[len(close_buttons) - 1].click()

      time.sleep(1)

      index += 1

    driver.quit()
  except Exception:
    traceback.print_exc()
    driver.quit()

scheduler = BlockingScheduler()
scheduler.add_job(check_grades, CronTrigger.from_crontab('0 8,12,16,20 * JAN SUN,MON-FRI')) # TODO update for SEM 2
scheduler.start()
