from flask import Flask, render_template, redirect, request, session, flash
from flask_session import Session
from pymysql import connections
from datetime import *
import os
import boto3
import hashlib
import random
from config import *

app = Flask(__name__)
app.secret_key = 'CloudAssingment'

bucket = custombucket
region = customregion

def create_connection():
    db_conn = connections.Connection(
        host=customhost,
        port=3306,
        user=customuser,
        password=custompass,
        db=customdb
    )
    return db_conn
    
output = {}

@app.route("/")
def index():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    cursor.execute('SELECT * FROM User')
    check_admin = cursor.fetchall()
    cursor.close()
    
    if not check_admin:
        User_email = 'lwy123@gmail.com'
        default_pwd = 'Bait3273'
        User_pwd = hashlib.md5(default_pwd.encode())
        User_pwd = User_pwd.hexdigest()
        User_role = 'Administrator'
        Status = 'Active'

        insert_admin_sql = "INSERT INTO Administrator VALUES ('Lim Wen Yuan', 'lwy123@gmail.com', '012-3456789', 'Y')"
        insert_useracc_sql = "INSERT INTO User VALUES (%s, %s, %s, %s)"
        cursor = db_conn.cursor()

        cursor.execute(insert_admin_sql)
        cursor.execute(insert_useracc_sql, (User_email, User_pwd, User_role, Status))
        db_conn.commit()
        cursor.close()

    return render_template('index.html')

@app.route("/logout")
def logout():
    session.pop('id', None)
    session.pop('role', None)
    return render_template('index.html')

@app.route("/login/<string:role>", methods=['GET'])
def login(role):
    session['role'] = role
    return render_template('login.html')

@app.route("/admin")
def admin():
    db_conn = create_connection()
    all_rows = []
    cursor = db_conn.cursor()
    cursor.execute("SELECT Stud_Id, Stud_name,Stud_email,Stud_phoneNo,Stud_programme,Stud_CGPA \
                    FROM Student S JOIN User U ON (S.Stud_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Stud_rows = cursor.fetchall()
    all_rows.append(Stud_rows)
    
    cursor.execute("SELECT Lec_Id, Lec_name,Lec_email,Lec_phoneNo, Lec_faculty , Lec_Department \
                    FROM Lecturer L JOIN User U ON (L.Lec_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Lec_rows = cursor.fetchall()
    all_rows.append(Lec_rows)
    
    cursor.execute("SELECT Company_Id, Company_name, Company_email, Company_phoneNo,Company_Address \
                    FROM Company C JOIN User U ON (C.Company_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Company_rows = cursor.fetchall()
    all_rows.append(Company_rows)
    cursor.close()
    
    return render_template('admin.html', rows=all_rows)

@app.route("/loginProcess", methods=['GET', 'POST'])
def loginProcess():
    db_conn = create_connection()
    email = request.form['User_email']
    pwd = hashlib.md5(request.form['User_pwd'].encode())
    pwd = pwd.hexdigest()
    
    cursor = db_conn.cursor()

    cursor.execute("SELECT * FROM User WHERE User_email = '" + email + "' AND User_pwd = '" + str(pwd) + "' AND User_role='"+session['role']+"' AND Status='Active'")
    check_login = cursor.fetchall()
    cursor.close()

    if not check_login:
        flash('User email or password is wrong....', 'alert')
        return render_template('login.html')
    else:
        cursor = db_conn.cursor()

        if session['role'] == 'Student':
            cursor.execute("SELECT Stud_Id FROM Student WHERE Stud_email = '" + email + "'")
            row = cursor.fetchall()
            cursor.close()
            session['id'] = row[0]

            cursor = db_conn.cursor()

            cursor.execute("SELECT Job.Job_id, Job_title, Company_name, Progress_status \
                            FROM StudentCompany, Job, Company \
                            WHERE Job.Job_id = StudentCompany.Job_id AND Company.Company_id = StudentCompany.Company_id \
                            AND Stud_id = %s", (session['id'],))
            rows = cursor.fetchall()
            cursor.close()
            return render_template('student.html', rows=rows)

        elif session['role'] == 'Lecturer':
            cursor.execute("SELECT Lec_Id FROM Lecturer WHERE Lec_email = '" + email + "'")
            row = cursor.fetchall()
            session['id'] = row[0]
            cursor.execute("SELECT Student.Stud_Id, Stud_name, Stud_programme, Stud_cgpa, Stud_email \
                            FROM Student \
                            WHERE Lec_id = %s", session['id'])
            rows = cursor.fetchall()
            cursor.close()
            return render_template('lecturer.html', rows=rows)

        elif session['role'] == 'Company':
            cursor.execute("SELECT Company_Id FROM Company WHERE Company_email = '" + email + "'")
            row = cursor.fetchall()

            session['id'] = row[0]
            current_datetime  = datetime.now()
            today_date = current_datetime.strftime("%Y-%m-%d")
            cursor.execute("SELECT Student.Stud_id, Stud_name, Stud_email, Stud_phoneNo, Intern_start_date, Intern_end_date, Job_title \
                    FROM Student, StudentCompany, Job \
                    WHERE Student.Stud_id = StudentCompany.Stud_id AND StudentCompany.Company_id = " + str(session['id'][0]) + " AND StudentCompany.Job_id = Job.Job_id \
                    AND Progress_status='Active' AND Intern_end_date > '" + today_date + "' \
                    ORDER BY Intern_start_date")
            rows = cursor.fetchall()
            cursor.close()
            return render_template('company.html', rows=rows)

        elif session['role'] == 'Administrator':
            cursor.execute("SELECT Admin_Id FROM Administrator WHERE Admin_email = '" + email + "'")
            row = cursor.fetchall()
            session['id'] = row[0]

            all_rows = []

            cursor.execute("SELECT Stud_Id, Stud_name,Stud_email,Stud_phoneNo,Stud_programme,Stud_CGPA \
                            FROM Student S JOIN User U ON (S.Stud_email = U.User_email) \
                            WHERE Status = 'Pending'")
            Stud_rows = cursor.fetchall()
            all_rows.append(Stud_rows)

            cursor.execute("SELECT Lec_Id, Lec_name,Lec_email,Lec_phoneNo, Lec_faculty , Lec_Department \
                            FROM Lecturer L JOIN User U ON (L.Lec_email = U.User_email) \
                            WHERE Status = 'Pending'")
            Lec_rows = cursor.fetchall()
            all_rows.append(Lec_rows)

            cursor.execute("SELECT Company_Id, Company_name, Company_email, Company_phoneNo,Company_Address \
                            FROM Company C JOIN User U ON (C.Company_email = U.User_email) \
                            WHERE Status = 'Pending'")
            Company_rows = cursor.fetchall()
            all_rows.append(Company_rows)
            cursor.close()
            
            return render_template('admin.html', rows=all_rows)

    return render_template('login.html')

@app.route("/student", methods=['GET', 'POST'])
def student():
    db_conn = create_connection()
    cursor = db_conn.cursor()

    cursor.execute("SELECT Job.Job_id, Job_title, Company_name, Progress_status \
                    FROM StudentCompany, Job, Company \
                    WHERE Job.Job_id = StudentCompany.Job_id AND Company.Company_id = StudentCompany.Company_id \
                    AND Stud_id = %s", (session['id'],))
    rows = cursor.fetchall()
    cursor.close()

    return render_template('student.html', rows=rows)

@app.route("/studentDetail/<string:Id>", methods=['GET', 'POST'])
def studentDetail(Id):
    db_conn = create_connection()
    cursor = db_conn.cursor()
    if session['role'] == "Company":
        cursor.execute("SELECT * FROM Student WHERE Stud_id=%s", Id)
        row = cursor.fetchall()
        cursor.close()
        
    elif session['role'] == "Lecturer":
        cursor.execute("SELECT * FROM Student WHERE Stud_id=%s", Id)
        Stud_row = cursor.fetchall()

        cursor.execute("SELECT * FROM Student WHERE Stud_intern_status = 'Intern' AND Stud_id=%s", Id)
        check_intern = cursor.fetchall()

        stud_img_data = show_specific_bucket(custombucket, Stud_row[0][6])
        stud_resume_data = show_specific_bucket(custombucket, Stud_row[0][7])

        if check_intern:
            cursor.execute("SELECT Company_name, Job_title FROM StudentCompany, Company, Job \
                            WHERE StudentCompany.Company_id = Company.Company_id \
                            AND StudentCompany.Job_id = Job.Job_id AND \
                            Progress_status = 'Active' AND Stud_id=%s", Id)
            Company_row = cursor.fetchall()
        
            cursor.execute("SELECT month,LogBook_pdf FROM Logbook WHERE Stud_id=%s", Id)
            LogBook_rows = cursor.fetchall()
            cursor.close()
    
            LogBook1 = ''
            LogBook2 = ''
            LogBook3 = ''
            
            if LogBook_rows:
                for logBook in LogBook_rows:
                    if logBook[0] == 1:
                        LogBook1 = show_specific_bucket(custombucket, logBook[1])
                    elif logBook[0] == 2:
                        LogBook2 = show_specific_bucket(custombucket, logBook[1])
                    elif logBook[0] == 3:
                        LogBook3 = show_specific_bucket(custombucket, logBook[1])
            
        
            all_row = []
            all_row.append(Stud_row)
            all_row.append(stud_img_data)
            all_row.append(stud_resume_data)
            all_row.append(Company_row[0][0])
            all_row.append(Company_row[0][1])
            all_row.append(LogBook1)
            all_row.append(LogBook2)
            all_row.append(LogBook3)
        else:
            all_row = []
            all_row.append(Stud_row)
            all_row.append(stud_img_data)
            all_row.append(stud_resume_data)
        

    return render_template('studentProfile.html', row=all_row)

@app.route("/StudentLogBook", methods=['GET', 'POST'])
def StudentLogBook():
    return render_template('studentLogbook.html')
    
@app.route("/submitLogbook", methods=['GET', 'POST'])
def submitLogbook():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    stud_id = session['id']
    month = request.form['radio']

    current_datetime  = datetime.now()
    submission_date = current_datetime.strftime("%Y-%m-%d")
    logbook_pdf = request.files['Logbook_pdf']

    insert_logbook_sql = "INSERT INTO Logbook(Stud_id, month, Logbook_pdf, Submission_date) VALUES (%s, " + month + ", %s, '" + submission_date + "')"
    if logbook_pdf.filename == "":
        return "Please select a file"

    try:
        logbook_file_name_in_s3 = "logbimg-" + stud_id[0] + "-" + str(month) + "_pdf"

        cursor.execute(insert_logbook_sql, (stud_id, logbook_file_name_in_s3))
        db_conn.commit()
        # Uplaod image file in S3 #
        s3 = boto3.resource('s3')

        try:
            s3.Bucket(custombucket).put_object(Key=logbook_file_name_in_s3, Body=logbook_pdf)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                logbook_file_name_in_s3)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("Submitted")
    cursor = db_conn.cursor()

    cursor.execute("SELECT Job_title, Company_name, Progress_status \
                    FROM StudentCompany, Job, Company \
                    WHERE Job.Job_id = StudentCompany.Job_id AND Company.Company_id = StudentCompany.Company_id \
                    AND Stud_id = %s", (session['id'],))
    rows = cursor.fetchall()
    cursor.close()
    return render_template('student.html', rows=rows)

@app.route("/Signup")
def Signup():
    session['action'] = 'SignUp'
    role = session['role']
    
    if role == 'Student':
        row = ((),)
        return render_template('studentSignUp.html', row=row)
    elif role == 'Lecturer':
        row = ((),)
        return render_template('lecturerSignUp.html', row=row)
    elif role == 'Company':
        row = ((),)
        return render_template('companySignUp.html', row=row)

@app.route("/manageStudent", methods=['GET', 'POST'])
def manageStudent():
    db_conn = create_connection()
    if session['action'] != '':
        if session['action'] == 'SignUp':
            stud_id = request.form['Stud_Id']
            stud_name = request.form['Stud_name']
            stud_email = request.form['Stud_email']
            stud_phoneNo = request.form['Stud_phoneNo']
            stud_programme = request.form['Stud_programme']
            stud_cgpa = request.form['Stud_cgpa']
            stud_img = request.files['Stud_img']
            stud_resume = request.files['Stud_resume']
            stud_pwd = hashlib.md5(request.form['Stud_pass'].encode())

            cursor = db_conn.cursor()

            cursor.execute("SELECT Lec_id FROM Lecturer WHERE Lec_status='Active'")
            lec_ids = cursor.fetchall()
            lec_id = random.choice(lec_ids[0])
            
            insert_stud_sql = "INSERT INTO Student VALUES (%s, %s, %s, %s, %s, " + stud_cgpa + ", %s, %s, '', '" + lec_id + "', 'Active')"
            insert_studacc_sql = "INSERT INTO User VALUES (%s, %s, 'Student', 'Pending')"

            if stud_img.filename == "" or stud_resume == "":
                return "Please select a file"
        
            try:
                stud_image_file_name_in_s3 = "simg" + str(stud_id) + "_img"
                stud_resume_file_name_in_s3 = "srm" + str(stud_id) + "_pdf"
        
                cursor.execute(insert_stud_sql, (stud_id, stud_name, stud_email, stud_phoneNo, stud_programme, stud_image_file_name_in_s3, stud_resume_file_name_in_s3))
                cursor.execute(insert_studacc_sql, (stud_email, stud_pwd.hexdigest()))
                db_conn.commit()
                # Uplaod image file in S3 #
                s3 = boto3.resource('s3')
        
                try:
                    s3.Bucket(custombucket).put_object(Key=stud_image_file_name_in_s3, Body=stud_img)
                    bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
                    s3_location = (bucket_location['LocationConstraint'])
        
                    if s3_location is None:
                        s3_location = ''
                    else:
                        s3_location = '-' + s3_location
        
                    object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                        s3_location,
                        custombucket,
                        stud_image_file_name_in_s3)
        
                    s3.Bucket(custombucket).put_object(Key=stud_resume_file_name_in_s3, Body=stud_resume)
                    object_url2 = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                        s3_location,
                        custombucket,
                        stud_resume_file_name_in_s3)
        
                except Exception as e:
                    return str(e)
        
            finally:
                cursor.close()
        
            print("successfully Sign Up!")
            return render_template('login.html')
        elif session['action'] == 'Edit':
            stud_id = session['id']
            stud_name = request.form['Stud_name']
            stud_phoneNo = request.form['Stud_phoneNo']
            stud_programme = request.form['Stud_programme']
            stud_cgpa = request.form['Stud_cgpa']
            stud_img = request.files['Stud_img']
            stud_resume = request.files['Stud_resume']
        
            update_sql = "UPDATE Student SET Stud_name = %s, Stud_phoneNo = %s, Stud_programme = %s, Stud_cgpa = " + stud_cgpa + " WHERE Stud_id=%s"
            cursor = db_conn.cursor()
        
            try:
        
                cursor.execute(update_sql, (stud_name, stud_phoneNo, stud_programme, (stud_id,)))
                db_conn.commit()
                # Uplaod image file in S3 #
                stud_image_file_name_in_s3 = "simg" + str(stud_id[0]) + "_img"
                stud_resume_file_name_in_s3 = "srm" + str(stud_id[0]) + "_pdf"
                s3 = boto3.resource('s3')
        
                try:
                    if stud_img.filename != "":
                        s3.Bucket(custombucket).put_object(Key=stud_image_file_name_in_s3, Body=stud_img)
                        bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
                        s3_location = (bucket_location['LocationConstraint'])
        
                        if s3_location is None:
                            s3_location = ''
                        else:
                            s3_location = '-' + s3_location
        
                        object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                            s3_location,
                            custombucket,
                            stud_image_file_name_in_s3)
        
                    if stud_resume.filename != "":
                        s3.Bucket(custombucket).put_object(Key=stud_resume_file_name_in_s3, Body=stud_resume)
                        bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
                        s3_location = (bucket_location['LocationConstraint'])
        
                        if s3_location is None:
                            s3_location = ''
                        else:
                            s3_location = '-' + s3_location
        
                        object_url2 = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                            s3_location,
                            custombucket,
                            stud_resume_file_name_in_s3)
        
                except Exception as e:
                    return str(e)
        
            finally:
                cursor.close()
        
            print("Update done...")
            return render_template('student.html')


@app.route("/lecturer")
def lecturer():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    cursor.execute("SELECT Student.Stud_Id, Stud_name, Stud_programme, Stud_cgpa, Stud_email \
                            FROM Student \
                            WHERE Lec_id = %s", session['id'])
    rows = cursor.fetchall()
    cursor.close()
    return render_template('lecturer.html', rows=rows)

@app.route("/manageLecturer", methods=['GET', 'POST'])
def manageLecturer():
    db_conn = create_connection()
    if session['action'] != '':
        if session['action'] == 'SignUp':
            lec_id = request.form['Lec_Id']
            lec_name = request.form['Lec_name']
            lec_email = request.form['Lec_email']
            lec_phoneNo = request.form['Lec_phoneNo']
            lec_faculty = request.form['Lec_faculty']
            lec_department = request.form['Lec_department']
            lec_img = request.files['Lec_img']
        
            lec_pwd = hashlib.md5(request.form['Lec_pass'].encode())
        
            insert_lec_sql = "INSERT INTO Lecturer VALUES (%s, %s, %s, %s, %s, %s, %s, 'Active')"
            insert_lecacc_sql = "INSERT INTO User VALUES (%s, %s, 'Lecturer', 'Pending')"
            cursor = db_conn.cursor()
        
            if lec_img.filename == "":
                return "Please select a file"
        
            try:
                lec_image_file_name_in_s3 = "limg" + str(lec_id) + "_img"
        
                cursor.execute(insert_lec_sql, (lec_id, lec_name, lec_email, lec_phoneNo, lec_faculty, lec_department, lec_image_file_name_in_s3))
                cursor.execute(insert_lecacc_sql, (lec_email, lec_pwd.hexdigest()))
                db_conn.commit()
                # Uplaod image file in S3 #
                s3 = boto3.resource('s3')
        
                try:
                    print("Data inserted in MySQL RDS... uploading files to S3...")
                    s3.Bucket(custombucket).put_object(Key=lec_image_file_name_in_s3, Body=lec_img)
                    bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
                    s3_location = (bucket_location['LocationConstraint'])
        
                    if s3_location is None:
                        s3_location = ''
                    else:
                        s3_location = '-' + s3_location
        
                    object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                        s3_location,
                        custombucket,
                        lec_image_file_name_in_s3)
        
                except Exception as e:
                    return str(e)
        
            finally:
                cursor.close()
        
            print("successfully Sign Up!")
            return render_template('login.html')
        elif session['action'] == 'Edit':
            lec_id = session['id']
            lec_name = request.form['Lec_name']
            lec_phoneNo = request.form['Lec_phoneNo']
            lec_faculty = request.form['Lec_faculty']
            lec_department = request.form['Lec_department']
            lec_img = request.files['Lec_img']
        
        
            update_sql = "UPDATE Lecturer SET Lec_name = %s, Lec_phoneNo = %s, Lec_faculty = %s, Lec_department = %s WHERE Lec_id=%s"
            cursor = db_conn.cursor()
        
            try:
                cursor.execute(update_sql, (lec_name, lec_email, lec_phoneNo, lec_faculty, lec_department, (lec_id,)))
                db_conn.commit()
                # Uplaod image file in S3 #
                lec_image_file_name_in_s3 = "limg" + str(lec_id[0]) + "_img"
        
                s3 = boto3.resource('s3')
        
                try:
                    if lec_img.filename != "":
                        s3.Bucket(custombucket).put_object(Key=lec_image_file_name_in_s3, Body=lec_img)
                        bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
                        s3_location = (bucket_location['LocationConstraint'])
        
                        if s3_location is None:
                            s3_location = ''
                        else:
                            s3_location = '-' + s3_location
        
                        object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                            s3_location,
                            custombucket,
                            lec_image_file_name_in_s3)
        
                except Exception as e:
                    return str(e)
        
            finally:
                cursor.close()
        
            print("Update done...")
            return render_template('lecturer.html')


@app.route("/company", methods=['GET', 'POST'])
def company():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    current_datetime  = datetime.now()
    today_date = current_datetime.strftime("%Y-%m-%d")
    cursor.execute("SELECT Student.Stud_id, Stud_name, Stud_email, Stud_phoneNo, Intern_start_date, Intern_end_date, Job_title \
                    FROM Student, StudentCompany, Job \
                    WHERE Student.Stud_id = StudentCompany.Stud_id AND StudentCompany.Company_id = " + str(session['id'][0]) + " AND StudentCompany.Job_id = Job.Job_id \
                    AND Progress_status='Active' AND Intern_end_date > '" + today_date + "' \
                    ORDER BY Intern_start_date")
    
    rows = cursor.fetchall()
    cursor.close()

    return render_template('company.html', rows=rows)

@app.route("/applicant", methods=['GET', 'POST'])
def applicant():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    current_datetime  = datetime.now()
    today_date = current_datetime.strftime("%Y-%m-%d")
    cursor.execute("SELECT Student.Stud_id, Stud_name, Stud_email, Stud_phoneNo, Stud_programme, Stud_cgpa, Job_title, Job.Job_id \
                    FROM Student, StudentCompany, Job \
                    WHERE Student.Stud_id = StudentCompany.Stud_id AND StudentCompany.Company_id = " + str(session['id'][0]) + " AND StudentCompany.Job_id = Job.Job_id \
                    AND Progress_status = 'Pending' AND Job_apply_deadline >= '" + today_date + "' \
                    ORDER BY Student.Stud_id")
    
    rows = cursor.fetchall()
    cursor.close()

    return render_template('applicant.html', rows=rows)

@app.route("/job", methods=['GET', 'POST'])
def job():
    row = ((),)
    session['action'] = 'Add'
    return render_template('companyAddJob.html', row=row)



@app.route("/manageCompany", methods=['GET', 'POST'])
def manageCompany():
    db_conn = create_connection()
    if session['action'] != '':
        if session['action'] == 'SignUp':
            cursor = db_conn.cursor()
            company_name = request.form['Company_name']
            company_description = request.form['Company_Description']
            company_phoneNo = request.form['Company_phoneNo']
            company_address = request.form['Company_address']
            company_email = request.form['Company_email']
            company_logo_img = request.files['Company_logo_img']
        
            company_pwd = hashlib.md5(request.form['Company_pass'].encode())
        
            insert_company_sql = "INSERT INTO Company(Company_name, Company_description, Company_phoneNo, Company_address, Company_email, Company_status, Company_logo_img) VALUES (%s, %s, %s, %s, %s, 'Active', %s)"
            insert_companyacc_sql = "INSERT INTO User VALUES (%s, %s, 'Company', 'Pending')"
            cursor = db_conn.cursor()
        
            if company_logo_img.filename == "":
                return "Please select a file"
        
            try:
                company_logo_image_file_name_in_s3 = "cimg" + company_name + "_img"
        
                cursor.execute(insert_company_sql, (company_name, company_description, company_phoneNo, company_address, company_email, company_logo_image_file_name_in_s3))
                cursor.execute(insert_companyacc_sql, (company_email, company_pwd.hexdigest()))
                db_conn.commit()
                # Uplaod image file in S3 #
                s3 = boto3.resource('s3')
        
                try:
                    print("Data inserted in MySQL RDS... uploading files to S3...")
                    s3.Bucket(custombucket).put_object(Key=company_logo_image_file_name_in_s3, Body=company_logo_img)
                    bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
                    s3_location = (bucket_location['LocationConstraint'])
        
                    if s3_location is None:
                        s3_location = ''
                    else:
                        s3_location = '-' + s3_location
        
                    object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                        s3_location,
                        custombucket,
                        company_logo_image_file_name_in_s3)
        
                except Exception as e:
                    return str(e)
        
            finally:
                cursor.close()
        
            print("successfully Sign Up!")
            return render_template('login.html')
        elif session['action'] == 'Edit':
            company_id = session['id']
            company_name = request.form['Company_name']
            company_phoneNo = request.form['Company_phoneNo']
            company_address = request.form['Company_address']
            company_logo_img = request.files['Company_logo_img']
        
        
            update_sql = "UPDATE Company SET Company_phoneNo = %s, Company_address = %s WHERE Company_id=" + str(company_id[0]) + ""
            cursor = db_conn.cursor()
        
            try:
                cursor.execute(update_sql, (company_phoneNo, company_address))
                db_conn.commit()
                # Uplaod image file in S3 #
                company_logo_image_file_name_in_s3 = "cimg" + company_name + "_img"
        
                s3 = boto3.resource('s3')
        
                try:
                    if company_logo_img.filename != "":
                        s3.Bucket(custombucket).put_object(Key=company_logo_image_file_name_in_s3, Body=company_logo_img)
                        bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
                        s3_location = (bucket_location['LocationConstraint'])
        
                        if s3_location is None:
                            s3_location = ''
                        else:
                            s3_location = '-' + s3_location
        
                        object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                            s3_location,
                            custombucket,
                            company_logo_image_file_name_in_s3)
        
                except Exception as e:
                    return str(e)
        
            finally:
                cursor.close()
        
            print("Update done...")
            return render_template('company.html')

@app.route("/adminApproveStudent/<string:Id>")
def adminApproveStudent(Id):
    db_conn = create_connection()
    cursor = db_conn.cursor()
    
    cursor.execute("SELECT Stud_email FROM Student WHERE Stud_id = '" + Id + "'")
    email = cursor.fetchall()
    email = email[0]
    cursor.execute("UPDATE User SET Status = 'Active' WHERE User_email=%s", (email,))
    db_conn.commit()

    all_rows = []

    cursor.execute("SELECT Stud_Id, Stud_name,Stud_email,Stud_phoneNo,Stud_programme,Stud_CGPA \
                    FROM Student S JOIN User U ON (S.Stud_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Stud_rows = cursor.fetchall()
    all_rows.append(Stud_rows)

    cursor.execute("SELECT Lec_Id, Lec_name,Lec_email,Lec_phoneNo, Lec_faculty , Lec_Department \
                    FROM Lecturer L JOIN User U ON (L.Lec_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Lec_rows = cursor.fetchall()
    all_rows.append(Lec_rows)

    cursor.execute("SELECT Company_Id, Company_name, Company_email, Company_phoneNo,Company_Address \
                    FROM Company C JOIN User U ON (C.Company_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Company_rows = cursor.fetchall()
    all_rows.append(Company_rows)

    cursor.close()

    print("User account approved!")

    return render_template('admin.html', rows=all_rows)

@app.route("/adminApproveLecturer/<string:Id>")
def adminApproveLecturer(Id):
    db_conn = create_connection()
    cursor = db_conn.cursor()
    
    cursor.execute("SELECT Lec_email FROM Lecturer WHERE Lec_id = '" + Id + "'")
    email = cursor.fetchall()
    email = email[0]
    cursor.execute("UPDATE User SET Status = 'Active' WHERE User_email=%s", (email,))
    db_conn.commit()

    all_rows = []

    cursor.execute("SELECT Stud_Id, Stud_name,Stud_email,Stud_phoneNo,Stud_programme,Stud_CGPA \
                    FROM Student S JOIN User U ON (S.Stud_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Stud_rows = cursor.fetchall()
    all_rows.append(Stud_rows)

    cursor.execute("SELECT Lec_Id, Lec_name,Lec_email,Lec_phoneNo, Lec_faculty , Lec_Department \
                    FROM Lecturer L JOIN User U ON (L.Lec_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Lec_rows = cursor.fetchall()
    all_rows.append(Lec_rows)

    cursor.execute("SELECT Company_Id, Company_name, Company_email, Company_phoneNo,Company_Address \
                    FROM Company C JOIN User U ON (C.Company_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Company_rows = cursor.fetchall()
    all_rows.append(Company_rows)

    cursor.close()

    print("User account approved!")

    return render_template('admin.html', rows=all_rows)


@app.route("/adminApproveCompany/<int:Id>")
def adminApproveCompany(Id):
    db_conn = create_connection()
    cursor = db_conn.cursor()
    
    cursor.execute("SELECT Company_email FROM Company WHERE Company_id = " + str(Id) + "")
    email = cursor.fetchall()
    email = email[0]
    cursor.execute("UPDATE User SET Status = 'Active' WHERE User_email=%s", (email,))
    db_conn.commit()

    all_rows = []

    cursor.execute("SELECT Stud_Id, Stud_name,Stud_email,Stud_phoneNo,Stud_programme,Stud_CGPA \
                    FROM Student S JOIN User U ON (S.Stud_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Stud_rows = cursor.fetchall()
    all_rows.append(Stud_rows)

    cursor.execute("SELECT Lec_Id, Lec_name,Lec_email,Lec_phoneNo, Lec_faculty , Lec_Department \
                    FROM Lecturer L JOIN User U ON (L.Lec_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Lec_rows = cursor.fetchall()
    all_rows.append(Lec_rows)

    cursor.execute("SELECT Company_Id, Company_name, Company_email, Company_phoneNo,Company_Address \
                    FROM Company C JOIN User U ON (C.Company_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Company_rows = cursor.fetchall()
    all_rows.append(Company_rows)

    cursor.close()

    print("User account approved!")

    return render_template('admin.html', rows=all_rows)

@app.route("/adminDeclineStudent/<string:Id>")
def adminDeclineStudent(Id):
    db_conn = create_connection()
    cursor = db_conn.cursor()
    
    cursor.execute("SELECT Stud_email FROM Student WHERE Stud_id = '" + Id + "'")
    email = cursor.fetchall()
    email = email[0]
    cursor.execute("UPDATE User SET Status = 'Inactive' WHERE User_email=%s", (email,))
    db_conn.commit()

    all_rows = []

    cursor.execute("SELECT Stud_Id, Stud_name,Stud_email,Stud_phoneNo,Stud_programme,Stud_CGPA \
                    FROM Student S JOIN User U ON (S.Stud_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Stud_rows = cursor.fetchall()
    all_rows.append(Stud_rows)

    cursor.execute("SELECT Lec_Id, Lec_name,Lec_email,Lec_phoneNo, Lec_faculty , Lec_Department \
                    FROM Lecturer L JOIN User U ON (L.Lec_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Lec_rows = cursor.fetchall()
    all_rows.append(Lec_rows)

    cursor.execute("SELECT Company_Id, Company_name, Company_email, Company_phoneNo,Company_Address \
                    FROM Company C JOIN User U ON (C.Company_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Company_rows = cursor.fetchall()
    all_rows.append(Company_rows)

    cursor.close()

    print("User account declined!")

    return render_template('admin.html', rows=all_rows)

@app.route("/adminDeclineLecturer/<string:Id>")
def adminDeclineLecturer(Id):
    db_conn = create_connection()
    cursor = db_conn.cursor()
    
    cursor.execute("SELECT Lec_email FROM Lecturer WHERE Lec_id = '" + Id + "'")
    email = cursor.fetchall()
    email = email[0]
    cursor.execute("UPDATE User SET Status = 'Inactive' WHERE User_email=%s", (email,))
    db_conn.commit()

    all_rows = []

    cursor.execute("SELECT Stud_Id, Stud_name,Stud_email,Stud_phoneNo,Stud_programme,Stud_CGPA \
                    FROM Student S JOIN User U ON (S.Stud_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Stud_rows = cursor.fetchall()
    all_rows.append(Stud_rows)

    cursor.execute("SELECT Lec_Id, Lec_name,Lec_email,Lec_phoneNo, Lec_faculty , Lec_Department \
                    FROM Lecturer L JOIN User U ON (L.Lec_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Lec_rows = cursor.fetchall()
    all_rows.append(Lec_rows)

    cursor.execute("SELECT Company_Id, Company_name, Company_email, Company_phoneNo,Company_Address \
                    FROM Company C JOIN User U ON (C.Company_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Company_rows = cursor.fetchall()
    all_rows.append(Company_rows)

    cursor.close()

    print("User account declined!")

    return render_template('admin.html', rows=all_rows)


@app.route("/adminDeclineCompany/<int:Id>")
def adminDeclineCompany(Id):
    db_conn = create_connection()
    cursor = db_conn.cursor()
    
    cursor.execute("SELECT Company_email FROM Company WHERE Company_id = " + Id + "")
    email = cursor.fetchall()
    email = email[0]
    cursor.execute("UPDATE User SET Status = 'Inactive' WHERE User_email=%s", (email,))
    db_conn.commit()

    all_rows = []

    cursor.execute("SELECT Stud_Id, Stud_name,Stud_email,Stud_phoneNo,Stud_programme,Stud_CGPA \
                    FROM Student S JOIN User U ON (S.Stud_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Stud_rows = cursor.fetchall()
    all_rows.append(Stud_rows)

    cursor.execute("SELECT Lec_Id, Lec_name,Lec_email,Lec_phoneNo, Lec_faculty , Lec_Department \
                    FROM Lecturer L JOIN User U ON (L.Lec_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Lec_rows = cursor.fetchall()
    all_rows.append(Lec_rows)

    cursor.execute("SELECT Company_Id, Company_name, Company_email, Company_phoneNo,Company_Address \
                    FROM Company C JOIN User U ON (C.Company_email = U.User_email) \
                    WHERE Status = 'Pending'")
    Company_rows = cursor.fetchall()
    all_rows.append(Company_rows)

    cursor.close()

    print("User account declined!")

    return render_template('admin.html', rows=all_rows)
    
@app.route("/edit", methods=['GET', 'POST'])
def edit():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    
    session['action'] = 'Edit'

    if session['role'] == "Student":
        cursor.execute("SELECT * FROM Student WHERE Stud_id=%s", (session['id'],))
        row = cursor.fetchall()
        cursor.close()
        return render_template('studentSignUp.html', row=row)
        
    elif session['role'] == 'Lecturer':
        cursor.execute("SELECT * FROM Lecturer WHERE Lec_id=%s", (session['id'],))
        row = cursor.fetchall()
        cursor.close()
        return render_template('lecturerSignUp.html', row=row)
        
    elif session['role'] == 'Company':
        cursor.execute("SELECT * FROM Company WHERE Company_id=" + str(session['id'][0]) + "")
        row = cursor.fetchall()
        cursor.close()
        return render_template('companySignUp.html', row=row)

def show_specific_bucket(bucket, key):
    presigned_url = ''
    s3_client = boto3.client('s3')
    try:
        presigned_url = s3_client.generate_presigned_url('get_object', Params = {'Bucket': bucket, 'Key': key}, ExpiresIn = 1000)
    except Exception as e:
        pass
        
    return presigned_url

@app.route("/StudentProfile", methods=['GET', 'POST'])
def StudentProfile():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    stud_id = session['id']

    cursor.execute("SELECT * FROM Student WHERE Stud_id=%s", (stud_id,))
    row = cursor.fetchall()
    cursor.close()

    stud_img_data = show_specific_bucket(custombucket, row[0][6])
    stud_resume_data = show_specific_bucket(custombucket, row[0][7])

    all_row = []
    all_row.append(row)
    all_row.append(stud_img_data)
    all_row.append(stud_resume_data)

    return render_template('studentProfile.html', row=all_row)

@app.route("/lecturerProfile", methods=['GET', 'POST'])
def lecturerProfile():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    lec_id = session['id']

    cursor.execute("SELECT * FROM Lecturer WHERE Lec_id=%s", (lec_id,))
    row = cursor.fetchall()
    cursor.close()

    lec_img_data = show_specific_bucket(custombucket, row[0][6])

    all_row = []
    all_row.append(row)
    all_row.append(lec_img_data)

    return render_template('lecturerProfile.html', row=all_row)

@app.route("/companyProfile", methods=['GET', 'POST'])
def companyProfile():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    company_id = session['id']

    cursor.execute("SELECT * FROM Company WHERE Company_id=" + str(company_id[0]) + "")
    row = cursor.fetchall()
    cursor.close()

    company_img_data = show_specific_bucket(custombucket, row[0][7])

    all_row = []
    all_row.append(row)
    all_row.append(company_img_data)

    return render_template('companyProfile.html', row=all_row)

@app.route("/ApplyJob/<int:JobId>")
def ApplyJob(JobId):
    db_conn = create_connection()
    cursor = db_conn.cursor()
    stud_id = session['id']
    job_id = JobId

    
    cursor = db_conn.cursor()
    cursor.execute("SELECT Company_id FROM Job WHERE Job_id=" + str(job_id) + "")
    company_id = cursor.fetchall()
    company_id = company_id[0]
    insert_jobapply_sql = "INSERT INTO StudentCompany VALUES (%s, " + str(company_id[0]) + ", " + str(job_id) + ", 'Pending', '', '')"
    cursor.execute(insert_jobapply_sql,(stud_id))

    db_conn.commit()
    cursor.close()

    return render_template('applyIntern.html')

@app.route("/applyIntern")
def applyIntern():
    db_conn = create_connection()
    cursor = db_conn.cursor()

    cursor.execute("SELECT Stud_intern_status FROM Student WHERE Stud_id=%s", (session['id'],))
    check_status = cursor.fetchall()
    if not check_status[0][0] == 'Intern':
        current_datetime  = datetime.now()
        today_date = current_datetime.strftime("%Y-%m-%d")
        cursor.execute("SELECT Job.Job_id, Job_title, Company_name, Salary FROM Job, Company WHERE Job.Company_id = Company.Company_id AND Job_status = 'Available' AND Job_apply_deadline > '" + today_date + "' \
                        AND Job_id NOT IN (SELECT Job.Job_id FROM Job, StudentCompany WHERE Job.Job_id = StudentCompany.Job_id AND Stud_id = %s AND (Progress_status = 'Pending' OR Progress_status = 'Active'))", (session['id'],))
        rows = cursor.fetchall()
        cursor.close()
        return render_template('applyIntern.html', rows=rows)
    else:
        flash('You cannot view or apply the intern as you are doing intern now....', 'alert')
        cursor = db_conn.cursor()

        cursor.execute("SELECT Job.Job_id, Job_title, Company_name, Progress_status \
                        FROM StudentCompany, Job, Company \
                        WHERE Job.Job_id = StudentCompany.Job_id AND Company.Company_id = StudentCompany.Company_id \
                        AND Stud_id = %s", (session['id'],))
        rows = cursor.fetchall()
        cursor.close()
        return render_template('student.html', rows=rows)

@app.route("/JobDetails/<int:JobId>")
def JobDetails(JobId):
    db_conn = create_connection()
    cursor = db_conn.cursor()

    cursor.execute("SELECT * FROM Job WHERE Job_id = " + str(JobId) + "")
    row = cursor.fetchall()
    cursor.close()
    return render_template('companyJobDetail.html', row=row)

@app.route("/AddJobProcess", methods=['GET', 'POST'])
def AddJobProcess():
    db_conn = create_connection()
    job_title = request.form['Job_title']
    job_description = request.form['Job_description']
    job_requirement = request.form['Job_requirement']
    job_apply_deadline = request.form['Job_apply_deadline']
    job_apply_deadline = job_apply_deadline.strftime("%Y-%m-%d")
    job_salary = request.form['Salary']
    company_id = session['id']

    insert_job_sql = "INSERT INTO Job(Job_title, Job_description, Job_requirement, Job_apply_deadline, Job_status, Company_id, Salary) VALUES (%s, %s, %s, %s, 'Available', " + str(company_id[0]) + ", " + str(job_salary) + ")"
    cursor = db_conn.cursor()

    cursor.execute(insert_job_sql, (job_title, job_description, job_requirement, job_apply_deadline))

    db_conn.commit()

    cursor.close()

    print("Successfully Created!")

    return render_template('company.html')

@app.route("/ApproveStudent/<string:Stud_Id>/<int:JobId>")
def ApproveStudent(Stud_Id, JobId):
    db_conn = create_connection()
    cursor = db_conn.cursor()

    current_datetime  = datetime.now()
    start_date = current_datetime.strftime("%Y-%m-%d")
    end_date = current_datetime + timedelta(days = 90)
    end_date = end_date.strftime("%Y-%m-%d")

    cursor.execute("UPDATE StudentCompany SET Progress_status = 'Active', Intern_end_date = '" + end_date + "', Intern_start_date = '" + start_date + "' WHERE Stud_id='" + Stud_Id + "' AND Job_id = " + str(JobId) + "")
    cursor.execute("UPDATE Student SET Stud_intern_status = 'Intern' WHERE Stud_id='" + Stud_Id + "'")
    db_conn.commit()
    cursor.close()

    print("Intern approved!")

    return render_template('applicant.html')

@app.route("/DeclineStudent/<string:Stud_Id>/<int:JobId>")
def DeclineStudent(Stud_Id, JobId):
    db_conn = create_connection()
    cursor = db_conn.cursor()

    cursor.execute("UPDATE StudentCompany SET Progress_status = 'Declined' WHERE Stud_id='" + Stud_Id + "' AND Job_id = " + str(JobId) + "")
    db_conn.commit()
    cursor.close()

    print("Intern approved!")

    return render_template('applicant.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

