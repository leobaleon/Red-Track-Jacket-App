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
import json, os, requests, time
from functools import wraps

# UCI Schedule of Classes URL
url = "https://www.reg.uci.edu/perl/WebSoc/"

# get Twilio credentials from environment variables
account_sid = os.environ['ACCOUNT_SID']
auth_token = os.environ['AUTH_TOKEN']

# connect to Twilio API
client = Client(account_sid, auth_token)

def sendMessage(reply, to_):
    message = client.messages \
        .create(
            from_='+18182908210',
            to=to_,
            body=reply
        )
    print(f"\"{reply}\" sent to {to_}")

app = Flask(__name__)

def validate_twilio_request(f):
    """Validates that incoming requests genuinely originated from Twilio"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Create an instance of the RequestValidator class
        validator = RequestValidator(auth_token)

        # Validate the request using its URL, POST data,
        # and X-TWILIO-SIGNATURE header
        request_valid = validator.validate(
            request.url,
            request.form,
            request.headers.get('X-TWILIO-SIGNATURE', ''))

        # Continue processing the request if it's valid, return a 403 error if
        # it's not
        if request_valid:
            return f(*args, **kwargs)
        else:
            return abort(403)
    return decorated_function

@app.route('/',  methods=['POST'])
@validate_twilio_request
def incoming_message():
    # print(request.is_json)
    # print(content)

    content = request.get_json()
    reply = getInfo(content['Body'])
    sendMessage(reply, content['From'])

    response = app.response_class(
        response = json.dumps("Success!"),
        status=200,
        mimetype='application/json'
    )

    return response

def getInfo(course):
    # course = course.split()

    sample_dept = "CompSci"
    sample_course_num = course

    # loads the driver executable
    driver = webdriver.Chrome('web_drivers/chromedriver.exe') 

    # loads the website on Google Chrome
    driver.get(url)

    # choose a department and then hit the Display Web Results button
    drop_down = Select(driver.find_element_by_name("Dept"))
    drop_down.select_by_visible_text('COMPSCI . . . . Computer Science')

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
        
    driver.quit()

    return "Number of seats available in " + sample_dept + " " + sample_course_num + ": " + str(seats_available)