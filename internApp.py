from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
from config import *

app = Flask(__name__)

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb

)
output = {}
table = 'company'


@app.route("/")
def index():
    return render_template('index.html')

@app.route("/signup")
    return render_template('signup.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

