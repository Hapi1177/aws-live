from flask import Flask, render_template, redirect, request, session
from flask_session import Session
from pymysql import connections
from datetime import *
import os
import boto3
import hashlib
from config import *

app = Flask(__name__)
app.secret_key = 'CloudAssingment'

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


@app.route("/")
def index():
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
    return render_template('admin.html')

@app.route("/loginProcess", methods=['GET', 'POST'])
def loginProcess():
    email = request.form['User_email']
    pwd = hashlib.md5(request.form['User_pwd'].encode())
    pwd = pwd.hexdigest()
    
    cursor = db_conn.cursor()

    cursor.execute("SELECT * FROM User WHERE User_email = '" + email + "' AND User_pwd = '" + str(pwd) + "' AND User_role='"+session['role']+"' AND Status='Active'")
    check_login = cursor.fetchall()
    cursor.close()

    if not check_login:
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
            cursor.close()
            session['id'] = row[0]
            return render_template('lecturer.html', row=row)

        elif session['role'] == 'Company':
            cursor.execute("SELECT Company_Id FROM Company WHERE Company_email = '" + email + "'")
            row = cursor.fetchall()
            cursor.close()
            session['id'] = row[0]
            return render_template('company.html', row=row)

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
    cursor = db_conn.cursor()

    cursor.execute("SELECT Job.Job_id, Job_title, Company_name, Progress_status \
                    FROM StudentCompany, Job, Company \
                    WHERE Job.Job_id = StudentCompany.Job_id AND Company.Company_id = StudentCompany.Company_id \
                    AND Stud_id = %s", (session['id'],))
    rows = cursor.fetchall()
    cursor.close()

    return render_template('student.html', rows=rows)

@app.route("/StudentLogBook", methods=['GET', 'POST'])
def StudentLogBook():
    return render_template('studentLogbook.html')
    
@app.route("/submitLogbook", methods=['GET', 'POST'])
def submitLogbook():
    cursor = db_conn.cursor()
    stud_id = session['id']
    month = request.form['radio']

    current_datetime  = datetime.now()
    submission_date = current_datetime.strftime("%d-%m-%Y")
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
            
        
            insert_stud_sql = "INSERT INTO Student VALUES (%s, %s, %s, %s, %s, " + stud_cgpa + ", %s, %s, '', '', 'Active')"
            insert_studacc_sql = "INSERT INTO User VALUES (%s, %s, 'Student', 'Pending')"
            cursor = db_conn.cursor()
        
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
                stud_image_file_name_in_s3 = "simg" + str(stud_id) + "_img"
                stud_resume_file_name_in_s3 = "srm" + str(stud_id) + "_pdf"
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


@app.route("/manageLecturer", methods=['GET', 'POST'])
def manageLecturer():
    if session['action'] != '':
        if session['action'] == 'SignUp':
            lec_id = request.form['Lec_id']
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
                cursor.execute(insert_lecacc_sql, (lec_email, lec_pwd))
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
            lec_email = request.form['Lec_email']
            lec_phoneNo = request.form['Lec_phoneNo']
            lec_faculty = request.form['Lec_faculty']
            lec_department = request.form['Lec_department']
            lec_img = request.files['Lec_img']
        
        
            update_sql = "UPDATE Student SET Lec_name = %s, Lec_email = %s, Lec_phoneNo = %s, Lec_faculty = %s, Lec_department = %s WHERE Lec_id='" + lec_id + "'"
            cursor = db_conn.cursor()
        
            try:
                cursor.execute(update_sql, (lec_name, lec_email, lec_phoneNo, lec_faculty, lec_department))
                db_conn.commit()
                # Uplaod image file in S3 #
                lec_image_file_name_in_s3 = "limg" + str(lec_id) + "_img"
        
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
    cursor = db_conn.cursor()
    current_datetime  = datetime.now()
    today_date = current_datetime.strftime("%d-%m-%Y")
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
    cursor = db_conn.cursor()
    current_datetime  = datetime.now()
    today_date = current_datetime.strftime("%d-%m-%Y")
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
    return render_template('companyAddJob.html', row=row)



@app.route("/manageCompany", methods=['GET', 'POST'])
def manageCompany():
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

def show_image(bucket):
    s3_client = boto3.client('s3')
    public_urls = []
    try:
        for item in s3_client.list_objects(Bucket=bucket)['Contents']:
            presigned_url = s3_client.generate_presigned_url('get_object', Params = {'Bucket': bucket, 'Key': item['Key']}, ExpiresIn = 1000)
            public_urls.append(presigned_url)
    except Exception as e:
        pass
    # print("[INFO] : The contents inside show_image = ", public_urls)
    return public_urls

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
    cursor = db_conn.cursor()

    cursor.execute("SELECT Student_intern_status FROM Student WHERE Stud_id=%s", (session['id'],))
    check_status = cursor.fetchall()
    if check_status[0] != 'Intern':
        cursor.execute("SELECT Job.Job_id, Job_title, Company_name, Salary FROM Job, Company WHERE Job.Company_id = Company.Company_id AND Job_status = 'Available' \
                        AND Job_id NOT IN (SELECT Job.Job_id FROM Job, StudentCompany WHERE Job.Job_id = StudentCompany.Job_id AND Stud_id = %s AND (Progress_status = 'Pending' OR Progress_status = 'Active'))", (session['id'],))
        rows = cursor.fetchall()
        cursor.close()
    else:
        rows = ((),)

    return render_template('applyIntern.html', rows=rows)

@app.route("/JobDetails/<int:JobId>")
def JobDetails(JobId):
    cursor = db_conn.cursor()

    cursor.execute("SELECT * FROM Job WHERE Job_id = " + str(JobId) + "")
    row = cursor.fetchall()
    cursor.close()
    return render_template('companyJobDetail.html', row=row)

@app.route("/AddJobProcess", methods=['GET', 'POST'])
def AddJobProcess():
    job_title = request.form['Job_title']
    job_description = request.form['Job_description']
    job_requirement = request.form['Job_requirement']
    job_apply_deadline = datetime.strptime(request.form['Job_apply_deadline'])
    job_apply_deadline = job_apply_deadline.strftime("%d-%m-%Y")
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
def ApproveStudent():
    cursor = db_conn.cursor()

    current_datetime  = datetime.now()
    start_date = current_datetime.strftime("%d-%m-%Y")
    end_date = current_datetime + timedelta(days = 90)
    end_date = end_date.strftime("%d-%m-%Y")

    cursor.execute("UPDATE StudentCompany SET Progress_status = 'Active', Intern_end_date = '" + end_date + "', Intern_start_date = '" + start_date + "' WHERE Stud_id='" + Stud_Id + "' AND Job_id = " + str(JobId) + "")
    cursor.execute("UPDATE Student SET Student_intern_status = 'Intern' WHERE Stud_id='" + Stud_Id + "'")
    db_conn.commit()
    cursor.close()

    print("Intern approved!")

    return render_template('applicant.html')

# @app.route("/showStudProcess", methods=['GET', 'POST'])
# def showAllStudProcess():
    # cursor = db_conn.cursor()

    # cursor.execute('SELECT * FROM Student')
    # rows = cursor.fetchall()
    # cursor.close()

    # return render_template('showAllStud.html', rows=rows)
#
# @app.route("/showStudDetail")
# def showStudDetailProcess():
    # cursor = db_conn.cursor()
    # stud_id = request.args.get('Stud_id')

    # cursor.execute("SELECT * FROM Student WHERE Stud_id='" + stud_id + "'")
    # row = cursor.fetchall()
    # cursor.close()

    # s3 = boto3.resource('s3')

    # r = s3.Bucket(custombucket).get_object(
    #     Bucket=custombucket,
    #     Key=row['Stud_img']
    # )

    # r2 = s3.Bucket(custombucket).get_object(
    #     Bucket=custombucket,
    #     Key=row['Stud_resume']
    # )

    # stud_img_data = r['Body'].read()
    # stud_resume_data = r2['Body'].read()

    # return render_template('showStudDetail.html', row=row, stud_img_data, stud_resume_data)
#
#
# @app.route("/lecLogin", methods=['GET', 'POST'])
# def lecLogin():
#     return render_template('lecLogin.html')
#
#
# @app.route("/lecLoginProcess", methods=['GET', 'POST'])
# def lecLoginProcess():
#     lec_email = request.form['Lec_email']
#     lec_pwd = hashlib.md5(request.form['Lec_pwd'].encode())
#
#     cursor = db_conn.cursor()
#
#     cursor.execute(
#         "SELECT * FROM User WHERE User_email = '" + lec_email + "' AND User_pwd = '" + lec_pwd + "' AND User_role='Lecturer' AND Status='Active'")
#     check_login = cursor.fetchall()
#     cursor.close()
#
#     if check_login == '':
#         return "User email or password is wrong"
#     else:
#         cursor = db_conn.cursor()
#
#         cursor.execute(
#             "SELECT * FROM Lecturer WHERE Lec_email = '" + lec_email + "'")
#         lec_row = cursor.fetchall()
#         cursor.close()
#
#     return render_template('lecProfile.html', lec_row)
#
#
# @app.route("/lecSignup")
# def lecSignup():
#     return render_template('lecSignup.html')
#
#
# @app.route("/addLecAccProcess", methods=['GET', 'POST'])
# def addLecAccProcess():
    # lec_id = request.form['Lec_id']
    # lec_name = request.form['Lec_name']
    # lec_email = request.form['Lec_email']
    # lec_phoneNo = request.form['Lec_phoneNo']
    # lec_faculty = request.form['Lec_faculty']
    # lec_department = request.form['Lec_department']
    # lec_img = request.files['Lec_img']

    # lec_pwd = hashlib.md5(request.form['Lec_pwd'].encode())

    # insert_lec_sql = "INSERT INTO Lecturer VALUES (%s, %s, %s, %s, %s, %s, %s, 'Active')"
    # insert_lecacc_sql = "INSERT INTO User VALUES (%s, %s, 'Lecturer', 'Inactive')"
    # cursor = db_conn.cursor()

    # if lec_img.filename == "":
    #     return "Please select a file"

    # try:
    #     lec_image_file_name_in_s3 = "lec-id-image-" + str(lec_id) + "_image_file"

    #     cursor.execute(insert_lec_sql, (lec_id, lec_name, lec_email, lec_phoneNo, lec_faculty, lec_department, lec_image_file_name_in_s3))
    #     cursor.execute(insert_lecacc_sql, (lec_email, lec_pwd))
    #     db_conn.commit()
    #     # Uplaod image file in S3 #
    #     s3 = boto3.resource('s3')

    #     try:
    #         print("Data inserted in MySQL RDS... uploading files to S3...")
    #         s3.Bucket(custombucket).put_object(Key=lec_image_file_name_in_s3, Body=lec_img)
    #         bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
    #         s3_location = (bucket_location['LocationConstraint'])

    #         if s3_location is None:
    #             s3_location = ''
    #         else:
    #             s3_location = '-' + s3_location

    #         object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
    #             s3_location,
    #             custombucket,
    #             lec_image_file_name_in_s3)

    #     except Exception as e:
    #         return str(e)

    # finally:
    #     cursor.close()

    # print("successfully Sign Up!")

    # return render_template('lecLogin.html')


# @app.route("/updateLec", methods=['GET', 'POST'])
# def updateLec():
#     cursor = db_conn.cursor()
#     lec_id = request.args.get('Lec_id')

#     cursor.execute("SELECT * FROM Lecturer WHERE Lec_id='" + lec_id + "'")
#     row = cursor.fetchall()
#     cursor.close()

#     return render_template('updateLec.html', row=row)
#
#
# @app.route("/updateLecProcess", methods=['GET', 'POST'])
# def updateLecProcess():
    # lec_id = request.form['Lec_id']
    # lec_name = request.form['Lec_name']
    # lec_email = request.form['Lec_email']
    # lec_phoneNo = request.form['Lec_phoneNo']
    # lec_faculty = request.form['Lec_faculty']
    # lec_department = request.form['Lec_department']
    # lec_img = request.files['Lec_img']


    # update_sql = "UPDATE Student SET Lec_name = %s, Lec_email = %s, Lec_phoneNo = %s, Lec_faculty = %s, Lec_department = %s WHERE Lec_id='" + lec_id + "'"
    # cursor = db_conn.cursor()

    # if lec_img.filename != "":
    #     lec_img = request.files['Lec_img']

    # try:
    #     cursor.execute(update_sql, (lec_name, lec_email, lec_phoneNo, lec_faculty, lec_department))
    #     db_conn.commit()
    #     # Uplaod image file in S3 #
    #     lec_image_file_name_in_s3 = "lec-id-image-" + str(lec_id) + "_image_file"

    #     s3 = boto3.resource('s3')

    #     try:
    #         if lec_img.filename != "":
    #             s3.Bucket(custombucket).put_object(Key=lec_image_file_name_in_s3, Body=lec_img)
    #             bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
    #             s3_location = (bucket_location['LocationConstraint'])

    #             if s3_location is None:
    #                 s3_location = ''
    #             else:
    #                 s3_location = '-' + s3_location

    #             object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
    #                 s3_location,
    #                 custombucket,
    #                 lec_image_file_name_in_s3)

    #     except Exception as e:
    #         return str(e)

    # finally:
    #     cursor.close()

    # print("Update done...")
    # return render_template('updateLec.html')
#
#
# @app.route("/showAllLecProcess", methods=['GET', 'POST'])
# def showAllLecProcess():
#     cursor = db_conn.cursor()
#
#     cursor.execute('SELECT * FROM Lecturer')
#     rows = cursor.fetchall()
#     cursor.close()
#
#     return render_template('showAllLec.html', rows=rows)
#
#
# @app.route("/showLecDetail")
# def showLecDetailProcess():
#     cursor = db_conn.cursor()
#     lec_id = request.args.get('Lec_id')
#
#     cursor.execute("SELECT * FROM Lecturer WHERE Lec_id=" + lec_id + "")
#     row = cursor.fetchall()
#     cursor.close()
#
#     s3 = boto3.resource('s3')
#
#     r = s3.Bucket(custombucket).get_object(
#         Bucket=custombucket,
#         Key=row['Lec_img']
#     )
#
#     lec_img_data = r['Body'].read()
#
#     return render_template('showLecDetail.html', row=row, lec_img_data)
#
#
# @app.route("/adminLogin", methods=['GET', 'POST'])
# def adminLogin():
#     return render_template('adminLogin.html')
#
#
# @app.route("/adminLoginProcess", methods=['GET', 'POST'])
# def adminLoginProcess():
#     admin_email = request.form['Admin_email']
#     admin_pwd = hashlib.md5(request.form['Admin_pwd'].encode())
#
#     cursor = db_conn.cursor()
#
#     cursor.execute(
#         "SELECT * FROM User WHERE User_email = '" + admin_email + "' AND User_pwd = '" + admin_pwd + "' AND User_role='Administrator' AND Status='Active'")
#     check_login = cursor.fetchall()
#     cursor.close()
#
#     if check_login == '':
#         return "User email or password is wrong"
#     else:
#         cursor = db_conn.cursor()
#
#         cursor.execute(
#             "SELECT * FROM Administrator WHERE Admin_email = '" + admin_email + "'")
#         admin_row = cursor.fetchall()
#         cursor.close()
#
#     return render_template('adminProfile.html', admin_row)
#
# @app.route("/updateAdmin", methods=['GET', 'POST'])
# def updateAdmin():
    # cursor = db_conn.cursor()
    # admin_id = request.args.get('Admin_id')

    # cursor.execute("SELECT * FROM Administrator WHERE Admin_id=" + admin_id + "")
    # row = cursor.fetchall()
    # cursor.close()
#
#     return render_template('updateAdmin.html', row=row)
#
#
# @app.route("/updateAdminProcess", methods=['GET', 'POST'])
# def updateAdminProcess():
#     admin_id = request.form['Admin_id']
#     admin_name = request.form['Admin_name']
#     admin_email = request.form['Admin_email']
#     admin_phoneNo = request.form['Admin_phoneNo']
#
#
#     update_sql = "UPDATE Student SET Admin_name = %s, Admin_email = %s, Admin_phoneNo = %s WHERE Lec_id=" + admin_id + ""
#     cursor = db_conn.cursor()
#
#     cursor.execute(update_sql, (admin_name, admin_email, admin_phoneNo))
#     db_conn.commit()
#     cursor.close()
#
#     print("Update done...")
#     return render_template('updateAdmin.html')
#
# @app.route("/showAdminDetailProcess")
# def showAdminDetailProcess():
#     cursor = db_conn.cursor()
#     admin_id = request.args.get('Admin_id')
#
#     cursor.execute("SELECT * FROM Administrator WHERE Admin_id=" + admin_id + "")
#     row = cursor.fetchall()
#     cursor.close()
#
#     return render_template('showAdminDetail.html', row=row)
#
# @app.route("/companyLogin", methods=['GET', 'POST'])
# def companyLogin():
#     return render_template('companyLogin.html')
#
#
# @app.route("/companyLoginProcess", methods=['GET', 'POST'])
# def companyLoginProcess():
#     company_email = request.form['Company_email']
#     company_pwd = hashlib.md5(request.form['Company_pwd'].encode())
#
#     cursor = db_conn.cursor()
#
#     cursor.execute(
#         "SELECT * FROM User WHERE User_email = '" + company_email + "' AND User_pwd = '" + company_pwd + "' AND User_role='Company' AND Status='Active'")
#     check_login = cursor.fetchall()
#     cursor.close()
#
#     if check_login == '':
#         return "User email or password is wrong"
#     else:
#         cursor = db_conn.cursor()
#
#         cursor.execute(
#             "SELECT * FROM Company WHERE Company_email = '" + company_email + "'")
#         company_row = cursor.fetchall()
#         cursor.close()
#
#     return render_template('companyProfile.html', company_row)
#
#
# @app.route("/companySignup")
# def companySignup():
#     return render_template('companySignup.html')
#
#
# @app.route("/addCompanyAccProcess", methods=['GET', 'POST'])
# def addCompanyAccProcess():
    # cursor = db_conn.cursor()

    # cursor.execute('SELECT MAX(Company_id) FROM Company')
    # id_num = cursor.fetchall()
    # cursor.close()

    # if id_num == '':
    #     company_id = 1
    # else:
    #     company_id = int(id_num) + 1

    # company_name = request.form['Company_name']
    # company_description = request.form['Company_description']
    # company_phoneNo = request.form['Company_phoneNo']
    # company_address = request.form['Company_address']
    # company_email = request.form['Company_email']
    # company_logo_img = request.files['Company_logo_img']

    # company_pwd = hashlib.md5(request.form['Company_pwd'].encode())

    # insert_company_sql = "INSERT INTO Company VALUES (%d, %s, %s, %s, %s, %s, 'Active', %s)"
    # insert_companyacc_sql = "INSERT INTO User VALUES (%s, %s, 'Company', 'Inactive')"
    # cursor = db_conn.cursor()

    # if company_logo_img.filename == "":
    #     return "Please select a file"

    # try:
    #     company_logo_image_file_name_in_s3 = "company-id-image-" + str(company_id) + "_image_file"

    #     cursor.execute(insert_company_sql, (company_id, company_name, company_description, company_phoneNo, company_address, company_email, company_logo_image_file_name_in_s3))
    #     cursor.execute(insert_companyacc_sql, (company_email, company_pwd))
    #     db_conn.commit()
    #     # Uplaod image file in S3 #
    #     s3 = boto3.resource('s3')

    #     try:
    #         print("Data inserted in MySQL RDS... uploading files to S3...")
    #         s3.Bucket(custombucket).put_object(Key=company_logo_image_file_name_in_s3, Body=company_logo_img)
    #         bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
    #         s3_location = (bucket_location['LocationConstraint'])

    #         if s3_location is None:
    #             s3_location = ''
    #         else:
    #             s3_location = '-' + s3_location

    #         object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
    #             s3_location,
    #             custombucket,
    #             company_logo_image_file_name_in_s3)

    #     except Exception as e:
    #         return str(e)

    # finally:
    #     cursor.close()

    # print("successfully Sign Up!")
#
#     return render_template('companyLogin.html')
#
#
# @app.route("/updateCompany", methods=['GET', 'POST'])
# def updateCompany():
#     cursor = db_conn.cursor()
#     company_id = request.args.get('Company_id')
#
#     cursor.execute("SELECT * FROM Company WHERE Company_id=" + company_id + "")
#     row = cursor.fetchall()
#     cursor.close()
#
#     return render_template('updateCompany.html', row=row)
#
#
# @app.route("/updateCompanyProcess", methods=['GET', 'POST'])
# def updateCompanyProcess():
    # company_id = request.form['Company_id']
    # company_name = request.form['Company_name']
    # company_email = request.form['Company_email']
    # company_phoneNo = request.form['Company_phoneNo']
    # company_address = request.form['Company_address']
    # company_email = request.form['Company_email']
    # company_logo_img = request.files['Company_logo_img']


    # update_sql = "UPDATE Company SET Company_name = %s, Company_email = %s, Company_phoneNo = %s, Company_address = %s, Company_email = %s WHERE Company_id=" + company_id + ""
    # cursor = db_conn.cursor()

    # try:
    #     cursor.execute(update_sql, (company_name, company_email, company_phoneNo, company_address, company_email))
    #     db_conn.commit()
    #     # Uplaod image file in S3 #
    #     company_logo_image_file_name_in_s3 = "company-id-image-" + str(company_id) + "_image_file"

    #     s3 = boto3.resource('s3')

    #     try:
    #         if company_logo_img.filename != "":
    #             s3.Bucket(custombucket).put_object(Key=company_logo_image_file_name_in_s3, Body=company_logo_img)
    #             bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
    #             s3_location = (bucket_location['LocationConstraint'])

    #             if s3_location is None:
    #                 s3_location = ''
    #             else:
    #                 s3_location = '-' + s3_location

    #             object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
    #                 s3_location,
    #                 custombucket,
    #                 company_logo_image_file_name_in_s3)

    #     except Exception as e:
    #         return str(e)

    # finally:
    #     cursor.close()

    # print("Update done...")
#     return render_template('updateCompany.html')
#
#
# @app.route("/showAllCompanyProcess", methods=['GET', 'POST'])
# def showAllCompanyProcess():
#     cursor = db_conn.cursor()
#
#     cursor.execute("SELECT * FROM Company WHERE Company_status = 'Active'")
#     rows = cursor.fetchall()
#     cursor.close()
#
#     return render_template('showAllCompany.html', rows=rows)
#
#
# @app.route("/showCompanyDetail")
# def showCompanyDetail():
#     cursor = db_conn.cursor()
#     company_id = request.args.get('Company_id')
#
#     cursor.execute("SELECT * FROM Company WHERE Company_id=" + company_id + "")
#     row = cursor.fetchall()
#     cursor.close()
#
#     s3 = boto3.resource('s3')
#
#     r = s3.Bucket(custombucket).get_object(
#         Bucket=custombucket,
#         Key=row['Company_logo_img']
#     )
#
#     company_img_data = r['Body'].read()
#
#     return render_template('showCompanyDetail.html', row=row, company_img_data)
#

#

#
#
# @app.route("/showInternApplicant")
# def showInternApplicant():
#     cursor = db_conn.cursor()
#     company_id = request.args.get('Company_id')
#
#     cursor.execute("SELECT Student.Stud_id, StudentCompany.Job_id, Stud_name, Stud_email, Stud_phoneNo, Stud_resume, Job_title "
#                    "FROM Student, StudentCompany, Job "
#                    "WHERE Student.Stud_id = StudentCompany.Stud_id "
#                    "AND StudentCompany.Job_id = Job.Job_id AND Progress_status = 'Pending' AND Stud_intern_status = 'Inactive'")
#     rows = cursor.fetchall()
#     cursor.close()
#
#     s3 = boto3.resource('s3')
#     stud_resume_data = []
#
#     for row in rows:
#         r = s3.Bucket(custombucket).get_object(
#             Bucket=custombucket,
#             Key=row['Stud_resume']
#         )
#         stud_resume_data.append(r['Body'].read())
#
#     return render_template('internApplicant.html', rows=rows, stud_resume_data)
#
# @app.route("/showInternOppurnity")
# def showInternOppurnity():
    # cursor = db_conn.cursor()

    # cursor.execute("SELECT * FROM Job WHERE Job_status = 'Available'")
    # rows = cursor.fetchall()
    # cursor.close()

    # return render_template('showInternOppurnity.html', rows=rows)
#
# @app.route("/showCurrentIntern")
# def showCurrentIntern():
#     company_id = request.args.get('Company_id')
#     cursor = db_conn.cursor()
#
    # cursor.execute(
    #     "SELECT Student.Stud_id, StudentCompany.Job_id, Stud_name, Stud_email, Job_title, Intern_start_date, Intern_end_date "
    #     "FROM Student, StudentCompany, Company, Job "
    #     "WHERE Student.Stud_id = StudentCompany.Stud_id "
    #     "AND StudentCompany.Job_id = Job.Job_id AND StudentCompany.Company_id = Company_Company_id "
    #     "AND Progress_status = 'Pending' AND Stud_intern_status = 'Inactive' AND Company.Company_id = '" + company_id + "'")
#     rows = cursor.fetchall()
#     cursor.close()
#
#     return render_template('showCurrentIntern.html', rows=rows)
#

#
# @app.route("/internApproveProgress")
# def internApproveProgress():
#     cursor = db_conn.cursor()
#     stud_id = request.args.get('Stud_id')
#     job_id = request.args.get('Job_id')
#
#     cursor.execute("SELECT Intern_start_date, Job_duration FROM StudentCompany, Job WHERE StudentCompany.Job_id = Job.Job_id AND Stud_id='" + stud_id + "' AND StudentCompany.Job_id = " + job_id + "")
#     row = cursor.fetchall()
#     start_date = row['Intern_start_date']
#     job_duration = row['Job_duration']
#
#     end_date = start_date + timedelta(days=job_duration * 30)
#
#     cursor.execute("UPDATE StudentCompany SET Progress_status = 'Done', Intern_end_date = " + end_date + " WHERE Stud_id='" + stud_id + "' AND Job_id = " + job_id + "")
#     db_conn.commit()
#     cursor.close()
#
#     print("Intern approved!")
#
#     return render_template('companyProfile.html')
#
# @app.route("/logbookSubmissionProcess")
# def logbookSubmissionProcess():
    # cursor = db_conn.cursor()

    # cursor.execute('SELECT MAX(Logbook_id) FROM Logbook')
    # id_num = cursor.fetchall()

    # if id_num == '':
    #     logbook_id = 1
    # else:
    #     logbook_id = int(id_num) + 1

    # stud_id = request.form['Stud_id']
    # submission_date = date.today()
    # logbook_pdf = request.files['Logbook_pdf']

    # insert_logbook_sql = "INSERT INTO Logbook VALUES (%d, %s, " + submission_date + ", %s)"
    # if logbook_pdf.filename == "":
    #     return "Please select a file"

    # try:
    #     logbook_file_name_in_s3 = "logbook-id-image-" + str(logbook_id) + "_pdf_file"

    #     cursor.execute(insert_company_sql, (logbook_id, stud_id, logbook_file_name_in_s3))
    #     db_conn.commit()
    #     # Uplaod image file in S3 #
    #     s3 = boto3.resource('s3')

    #     try:
    #         print("Data inserted in MySQL RDS... uploading files to S3...")
    #         s3.Bucket(custombucket).put_object(Key=logbook_file_name_in_s3, Body=logbook_pdf)
    #         bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
    #         s3_location = (bucket_location['LocationConstraint'])

    #         if s3_location is None:
    #             s3_location = ''
    #         else:
    #             s3_location = '-' + s3_location

    #         object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
    #             s3_location,
    #             custombucket,
    #             logbook_file_name_in_s3)

    #     except Exception as e:
    #         return str(e)

    # finally:
    #     cursor.close()

    # print("Submitted")

    # return render_template('logbookSubmission.html')
#
# @app.route("/showLogbook")
# def showLogbook():
#     lec_id = request.args.get('Lec_id')
#     cursor = db_conn.cursor()
#
#     cursor.execute(
#         "SELECT Logbook_id, Stud_id, Stud_name, Logbook_pdf, Submission_date "
#         "FROM Logbook, Student, Lecturer "
#         "WHERE Student.Stud_id = Logbook.Stud_id AND Student.Lec_id = '" + lec_id + "'")
#     rows = cursor.fetchall()
#     cursor.close()
#
#     s3 = boto3.resource('s3')
#     logbook_pdf_data = []
#
#     for row in rows:
#         r = s3.Bucket(custombucket).get_object(
#             Bucket=custombucket,
#             Key=row['Logbook_pdf']
#         )
#         logbook_pdf_data.append(r['Body'].read())
#
#     return render_template('showLogbook.html', rows=rows, logbook_pdf_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

