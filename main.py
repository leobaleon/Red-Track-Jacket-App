# web scraping
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup

# flask server
from flask import Flask, request, Response, abort

# twilio
from twilio.rest import Client
from twilio.request_validator import RequestValidator

# misc
import json, os, requests, time, threading, concurrent.futures
from functools import wraps

# UCI Schedule of Classes URL
url = "https://www.reg.uci.edu/perl/WebSoc/"

# get Twilio credentials from environment variables
account_sid = os.environ['ACCOUNT_SID']
auth_token = os.environ['AUTH_TOKEN']

# connect to Twilio API
client = Client(account_sid, auth_token)

# this function expects a string for the body to reply with and another string
# to designate which phone number to send it to
def send_message(reply, to_) -> None:
    message = client.messages \
        .create(
            from_='+18182908210',
            to=to_,
            body=reply
        )
    print(f"\"{reply}\" sent to {to_}")

app = Flask(__name__)

# this function validates that any HTTP requests are valid and coming from Twilio
def validate_twilio_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Create an instance of the RequestValidator class
        validator = RequestValidator(auth_token)

        # Validate the request using its URL, POST data, and X-TWILIO-SIGNATURE header
        request_valid = validator.validate(
            request.url,
            request.form,
            request.headers.get('X-TWILIO-SIGNATURE', ''))

        # Continue processing the request if it's valid, return a 403 error if it's not
        if request_valid:
            return f(*args, **kwargs)
        else:
            return abort(403)

    return decorated_function

# whenever an HTTP request is made to this server, it will get routed to this function,
# but only after it has been validated by the validate_twilio_request() function
# the incoming_message() function reads the data sent to this server, then parses it to
# get the appropriate info needed to begin web scraping
@app.route('/',  methods=['POST'])
@validate_twilio_request
def incoming_message() ->  dict:
    # parse the data received
    content = request.get_json()

    # begin a new thread and begin getting the requested info
    future = concurrent.futures.ThreadPoolExecutor().submit(getInfo, content['Body'])
    reply = future.result()

    # reply with the corresponding info
    send_message(reply, content['From'])

    response = app.response_class(
        response = json.dumps("Success!"),
        status=200,
        mimetype='application/json'
    )

    return response

def get_actual_webpage_source(driver) -> dict:
    # loads the website on Google Chrome
    driver.get(url)

    # choose a department and then hit the Display Web Results button
    drop_down = Select(driver.find_element_by_name("Dept"))
    drop_down.select_by_visible_text('COMPSCI . . . . Computer Science')

    # click the text results button
    results_button = driver.find_element_by_css_selector('[value="Display Text Results"]')
    results_button.click()

    return driver.page_source

def get_lines_of_text(text, dept, course_num) -> str:
    # find beginning of desired block
    begin = text.find(dept + "  " + course_num)

    if begin == '-1':
        return begin

    text = text[begin:]
    text = text[text.find("CCode"):]

    # find end of desired block
    end = text[len(dept):].find(dept)

    # get final desired block of text ready for parsing
    text = text[:end]

    # help split a little easier
    return text.replace(", ", "-").split('\n')

def get_seats(lines) -> int:
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
        
    return seats_available

def getInfo(course_num) -> str:
    dept = "CompSci"

    # loads the driver executable
    driver = webdriver.Chrome('web_drivers/chromedriver.exe') 

    # perform the necessary webpage interactions to load the desired
    # text results of the appropriate courses
    temp_html = get_actual_webpage_source(driver)

    # close Chrome as soon as it's no longer needed
    driver.quit()

    # use BeautifulSoup to scrape only the desired text
    soup = BeautifulSoup(temp_html, 'html.parser')
    
    # get clean lines of text from scraped text
    lines = get_lines_of_text(soup.find("pre").string, dept, course_num)

    if lines[0] == '':
        return f"I'm sorry, {dept} {course_num} is not available this quarter. Try another course number."

    # get the total number of seats available for this course
    seats_available = get_seats(lines)

    return "Number of seats available in " + dept + " " + course_num + ": " + str(seats_available)