from selenium import webdriver
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
import time

def main():
    # UCI Schedule of Classes URL
    url = "https://www.reg.uci.edu/perl/WebSoc/"

    sample_dept = "CompSci"
    sample_course_num = "122A"

    # loads the driver executable
    driver = webdriver.Chrome('web_drivers/chromedriver.exe') 

    # loads the website on Google Chrome
    driver.get(url)

    # choose a department and then hit the Display Web Results button
    drop_down = Select(driver.find_element_by_name("Dept"))
    drop_down.select_by_visible_text('COMPSCI . . . . Computer Science')
    time.sleep(1)

    # click the text results button
    results_button = driver.find_element_by_css_selector('[value="Display Text Results"]')
    results_button.click()
    
    # use BeautifulSoup to scrape only the desired text
    temp_html = driver.page_source
    soup = BeautifulSoup(temp_html, 'html.parser')
    results = soup.find("pre")
    text = results.string
    
    # find beginning of desired block
    begin = text.find(sample_dept + "  " + sample_course_num)
    text = text[begin:]
    text = text[text.find("CCode"):]

    # find end of desired block
    end = text[len(sample_dept):].find(sample_dept)

    # get final desired block of text ready for parsing
    text = text[:end]

    # help split a little easier
    lines = text.replace(", ", "-").split('\n')

    seats_available = 0

    for line in lines:
        items = line.split()

        # make sure it's an actual class and not a note
        if not items[0].isnumeric(): 
            continue

        # ensure it's a lecture and not a discussion
        if items[1] != "LEC":
            continue

        # get key info from each line
        max = items[-7]
        current = items[-6]
        status = items[-1]

        # for the special case where enrollment is staggered
        if len(current) > 3:
            current = current[:current.find('/')]

        # add seats if applicable
        if status != "FULL":
            seats_available += int(max) - int(current)
        
    print(f'Number of seats available in {sample_dept} {sample_course_num}: {seats_available}')

    time.sleep(3)

    driver.quit()

if __name__ == "__main__":
    main()