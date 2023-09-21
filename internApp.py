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
        User_role = 'Administrator'
        Status = 'Active'

        insert_admin_sql = "INSERT INTO Administrator VALUES (1, 'Lim Wen Yuan', 'lwy123@gmail.com', '012-3456789', 'Y')"
        insert_useracc_sql = "INSERT INTO User VALUES (%s, %s, %s, %s)"
        cursor = db_conn.cursor()

        cursor.execute(insert_admin_sql)
        cursor.execute(insert_useracc_sql, (User_email, User_pwd, User_role, Status))
        db_conn.commit()
        cursor.close()

    return render_template('index.html')

@app.route("/Signout")
def Signout():
    session.pop('id', None)
    session.pop('role', None)
    return render_template('index.html')

@app.route("/login/<string:role>", methods=['GET'])
def login(role):
    session['role'] = role
    return render_template('login.html')

@app.route("/studLoginProcess", methods=['GET', 'POST'])
def studLoginProcess():
    stud_email = request.form['User_email']
    stud_pwd = hashlib.md5(request.form['User_pwd'].encode())

    cursor = db_conn.cursor()

    cursor.execute("SELECT * FROM User WHERE User_email = '" + stud_email + "' AND User_pwd = '" + stud_pwd + "' AND User_role='Student' AND Status='Active'")
    check_login = cursor.fetchall()
    cursor.close()

    if check_login == '':
        return "User email or password is wrong"
    else:
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM Student WHERE Stud_email = '" + stud_email + "'")
        stud_row = cursor.fetchall()
        cursor.close()

        session['id'] = stud_row['Stud_id']

    return render_template('student.html', stud_row)

@app.route("/Signup")
def Signup():
    session['action'] = 'SignUp'
    if 'role' in session:
        role = session['role']

    cursor = db_conn.cursor()
    
    if role == 'Student':
        cursor.execute("SELECT * FROM Student WHERE Stud_id='" + str(id) + "'")
        row = cursor.fetchall()
        cursor.close()
        return render_template('studentSignUp.html', row=row)
    elif role == 'Lecturer':
        return render_template('lecturerSignUp.html', row=row)
    elif role == 'Company':
        return render_template('companySignUp.html', row=row)

@app.route("/manageStudent", methods=['GET', 'POST'])
def manageStudent():
    if session['action'] != '':
        if session['action'] == 'SignUp':
            stud_id = request.form['Stud_id']
            stud_name = request.form['Stud_name']
            stud_email = request.form['User_email']
            stud_phoneNo = request.form['Stud_phoneNo']
            stud_programme = request.form['Stud_programme']
            stud_cgpa = request.form['Stud_cgpa']
            stud_img = request.files['Stud_img']
            stud_resume = request.files['Stud_resume']
            stud_pwd = hashlib.md5(request.form['User_pwd'].encode())
        
            insert_stud_sql = "INSERT INTO Student VALUES (%s, %s, %s, %s, %s, %.2f, %s, %s, '', '', 'Active')"
            insert_studacc_sql = "INSERT INTO User VALUES (%s, %s, 'Student', 'Inactive')"
            cursor = db_conn.cursor()
        
            if stud_img.filename == "" or stud_resume == "":
                return "Please select a file"
        
            try:
                stud_image_file_name_in_s3 = "stud-id-image-" + str(stud_id) + "_image_file"
                stud_resume_file_name_in_s3 = "stud-id-resume-" + str(stud_id) + "_pdf_file"
        
                cursor.execute(insert_stud_sql, (stud_id, stud_name, stud_email, stud_phoneNo, stud_programme, stud_cgpa, stud_img, stud_image_file_name_in_s3, stud_resume_file_name_in_s3))
                cursor.execute(insert_studacc_sql, (stud_email, stud_pwd))
                db_conn.commit()
                # Uplaod image file in S3 #
                s3 = boto3.resource('s3')
        
                try:
                    print("Data inserted in MySQL RDS... uploading files to S3...")
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
            stud_id = request.form['Stud_id']
            stud_name = request.form['Stud_name']
            stud_phoneNo = request.form['Stud_phoneNo']
            stud_programme = request.form['Stud_programme']
            stud_cgpa = request.form['Stud_cgpa']
            stud_img = request.files['Stud_img']
            stud_resume = request.files['Stud_resume']
        
            update_sql = "UPDATE Student SET Stud_name = %s, Stud_phoneNo = %s, Stud_programme = %s, Stud_cgpa = %.2f WHERE Stud_id='" + stud_id + "'"
            cursor = db_conn.cursor()
        
            if stud_img.filename != "":
                stud_img = request.files['Stud_img']
            if stud_resume.filename != "":
                stud_resume = request.files['Stud_resume']
        
            try:
        
                cursor.execute(update_sql, (stud_name, stud_phoneNo, stud_programme, stud_cgpa))
                db_conn.commit()
                # Uplaod image file in S3 #
                stud_image_file_name_in_s3 = "stud-id-image-" + str(stud_id) + "_image_file"
                stud_resume_file_name_in_s3 = "stud-id-resume-" + str(stud_id) + "_pdf_file"
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

# @app.route("/Update", methods=['GET', 'POST'])
# def updateStud():
#     cursor = db_conn.cursor()
#     if 'id' in session:
#         id = session['id']

#     if 'role' in session:
#         role = session['role']

#     session['action'] = 'Update'

#     if role == 'Student':
#         cursor.execute("SELECT * FROM Student WHERE Stud_id='" + id + "'")
#         row = cursor.fetchall()
#         cursor.close()
#         return render_template('updateStud.html', row=row)

# @app.route("/showStudProcess", methods=['GET', 'POST'])
# def showAllStudProcess():
#     cursor = db_conn.cursor()
#
#     cursor.execute('SELECT * FROM Student')
#     rows = cursor.fetchall()
#     cursor.close()
#
#     return render_template('showAllStud.html', rows=rows)
#
# @app.route("/showStudDetail")
# def showStudDetailProcess():
#     cursor = db_conn.cursor()
#     stud_id = request.args.get('Stud_id')
#
#     cursor.execute("SELECT * FROM Student WHERE Stud_id='" + stud_id + "'")
#     row = cursor.fetchall()
#     cursor.close()
#
#     s3 = boto3.resource('s3')
#
#     r = s3.Bucket(custombucket).get_object(
#         Bucket=custombucket,
#         Key=row['Stud_img']
#     )
#
#     r2 = s3.Bucket(custombucket).get_object(
#         Bucket=custombucket,
#         Key=row['Stud_resume']
#     )
#
#     stud_img_data = r['Body'].read()
#     stud_resume_data = r2['Body'].read()
#
#     return render_template('showStudDetail.html', row=row, stud_img_data, stud_resume_data)
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
#     lec_id = request.form['Lec_id']
#     lec_name = request.form['Lec_name']
#     lec_email = request.form['Lec_email']
#     lec_phoneNo = request.form['Lec_phoneNo']
#     lec_faculty = request.form['Lec_faculty']
#     lec_department = request.form['Lec_department']
#     lec_img = request.files['Lec_img']
#
#     lec_pwd = hashlib.md5(request.form['Lec_pwd'].encode())
#
#     insert_lec_sql = "INSERT INTO Lecturer VALUES (%s, %s, %s, %s, %s, %s, %s, 'Active')"
#     insert_lecacc_sql = "INSERT INTO User VALUES (%s, %s, 'Lecturer', 'Inactive')"
#     cursor = db_conn.cursor()
#
#     if lec_img.filename == "":
#         return "Please select a file"
#
#     try:
#         lec_image_file_name_in_s3 = "lec-id-image-" + str(lec_id) + "_image_file"
#
#         cursor.execute(insert_lec_sql, (lec_id, lec_name, lec_email, lec_phoneNo, lec_faculty, lec_department, lec_image_file_name_in_s3))
#         cursor.execute(insert_lecacc_sql, (lec_email, lec_pwd))
#         db_conn.commit()
#         # Uplaod image file in S3 #
#         s3 = boto3.resource('s3')
#
#         try:
#             print("Data inserted in MySQL RDS... uploading files to S3...")
#             s3.Bucket(custombucket).put_object(Key=lec_image_file_name_in_s3, Body=lec_img)
#             bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
#             s3_location = (bucket_location['LocationConstraint'])
#
#             if s3_location is None:
#                 s3_location = ''
#             else:
#                 s3_location = '-' + s3_location
#
#             object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
#                 s3_location,
#                 custombucket,
#                 lec_image_file_name_in_s3)
#
#         except Exception as e:
#             return str(e)
#
#     finally:
#         cursor.close()
#
#     print("successfully Sign Up!")
#
#     return render_template('lecLogin.html')
#
#
# @app.route("/updateLec", methods=['GET', 'POST'])
# def updateLec():
#     cursor = db_conn.cursor()
#     lec_id = request.args.get('Lec_id')
#
#     cursor.execute("SELECT * FROM Lecturer WHERE Lec_id='" + lec_id + "'")
#     row = cursor.fetchall()
#     cursor.close()
#
#     return render_template('updateLec.html', row=row)
#
#
# @app.route("/updateLecProcess", methods=['GET', 'POST'])
# def updateLecProcess():
#     lec_id = request.form['Lec_id']
#     lec_name = request.form['Lec_name']
#     lec_email = request.form['Lec_email']
#     lec_phoneNo = request.form['Lec_phoneNo']
#     lec_faculty = request.form['Lec_faculty']
#     lec_department = request.form['Lec_department']
#     lec_img = request.files['Lec_img']
#
#
#     update_sql = "UPDATE Student SET Lec_name = %s, Lec_email = %s, Lec_phoneNo = %s, Lec_faculty = %s, Lec_department = %s WHERE Lec_id='" + lec_id + "'"
#     cursor = db_conn.cursor()
#
#     if lec_img.filename != "":
#         lec_img = request.files['Lec_img']
#
#     try:
#         cursor.execute(update_sql, (lec_name, lec_email, lec_phoneNo, lec_faculty, lec_department))
#         db_conn.commit()
#         # Uplaod image file in S3 #
#         lec_image_file_name_in_s3 = "lec-id-image-" + str(lec_id) + "_image_file"
#
#         s3 = boto3.resource('s3')
#
#         try:
#             if lec_img.filename != "":
#                 s3.Bucket(custombucket).put_object(Key=lec_image_file_name_in_s3, Body=lec_img)
#                 bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
#                 s3_location = (bucket_location['LocationConstraint'])
#
#                 if s3_location is None:
#                     s3_location = ''
#                 else:
#                     s3_location = '-' + s3_location
#
#                 object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
#                     s3_location,
#                     custombucket,
#                     lec_image_file_name_in_s3)
#
#         except Exception as e:
#             return str(e)
#
#     finally:
#         cursor.close()
#
#     print("Update done...")
#     return render_template('updateLec.html')
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
#     cursor = db_conn.cursor()
#     admin_id = request.args.get('Admin_id')
#
#     cursor.execute("SELECT * FROM Administrator WHERE Admin_id=" + admin_id + "")
#     row = cursor.fetchall()
#     cursor.close()
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
#     cursor = db_conn.cursor()
#
#     cursor.execute('SELECT MAX(Company_id) FROM Company')
#     id_num = cursor.fetchall()
#     cursor.close()
#
#     if id_num == '':
#         company_id = 1
#     else:
#         company_id = int(id_num) + 1
#
#     company_name = request.form['Company_name']
#     company_description = request.form['Company_description']
#     company_phoneNo = request.form['Company_phoneNo']
#     company_address = request.form['Company_address']
#     company_email = request.form['Company_email']
#     company_logo_img = request.files['Company_logo_img']
#
#     company_pwd = hashlib.md5(request.form['Company_pwd'].encode())
#
#     insert_company_sql = "INSERT INTO Company VALUES (%d, %s, %s, %s, %s, %s, 'Active', %s)"
#     insert_companyacc_sql = "INSERT INTO User VALUES (%s, %s, 'Company', 'Inactive')"
#     cursor = db_conn.cursor()
#
#     if company_logo_img.filename == "":
#         return "Please select a file"
#
#     try:
#         company_logo_image_file_name_in_s3 = "company-id-image-" + str(company_id) + "_image_file"
#
#         cursor.execute(insert_company_sql, (company_id, company_name, company_description, company_phoneNo, company_address, company_email, company_logo_image_file_name_in_s3))
#         cursor.execute(insert_companyacc_sql, (company_email, company_pwd))
#         db_conn.commit()
#         # Uplaod image file in S3 #
#         s3 = boto3.resource('s3')
#
#         try:
#             print("Data inserted in MySQL RDS... uploading files to S3...")
#             s3.Bucket(custombucket).put_object(Key=company_logo_image_file_name_in_s3, Body=company_logo_img)
#             bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
#             s3_location = (bucket_location['LocationConstraint'])
#
#             if s3_location is None:
#                 s3_location = ''
#             else:
#                 s3_location = '-' + s3_location
#
#             object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
#                 s3_location,
#                 custombucket,
#                 company_logo_image_file_name_in_s3)
#
#         except Exception as e:
#             return str(e)
#
#     finally:
#         cursor.close()
#
#     print("successfully Sign Up!")
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
#     company_id = request.form['Company_id']
#     company_name = request.form['Company_name']
#     company_email = request.form['Company_email']
#     company_phoneNo = request.form['Company_phoneNo']
#     company_address = request.form['Company_address']
#     company_email = request.form['Company_email']
#     company_logo_img = request.files['Company_logo_img']
#
#
#     update_sql = "UPDATE Company SET Company_name = %s, Company_email = %s, Company_phoneNo = %s, Company_address = %s, Company_email = %s WHERE Company_id=" + company_id + ""
#     cursor = db_conn.cursor()
#
#     try:
#         cursor.execute(update_sql, (company_name, company_email, company_phoneNo, company_address, company_email))
#         db_conn.commit()
#         # Uplaod image file in S3 #
#         company_logo_image_file_name_in_s3 = "company-id-image-" + str(company_id) + "_image_file"
#
#         s3 = boto3.resource('s3')
#
#         try:
#             if company_logo_img.filename != "":
#                 s3.Bucket(custombucket).put_object(Key=company_logo_image_file_name_in_s3, Body=company_logo_img)
#                 bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
#                 s3_location = (bucket_location['LocationConstraint'])
#
#                 if s3_location is None:
#                     s3_location = ''
#                 else:
#                     s3_location = '-' + s3_location
#
#                 object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
#                     s3_location,
#                     custombucket,
#                     company_logo_image_file_name_in_s3)
#
#         except Exception as e:
#             return str(e)
#
#     finally:
#         cursor.close()
#
#     print("Update done...")
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
# @app.route("/adminApproveProgress")
# def adminApproveProgress():
#     cursor = db_conn.cursor()
#     user_email = request.args.get('User_email')
#
#     cursor.execute("UPDATE User SET Status = 'Active' WHERE User_email=" + user_email + "")
#     db_conn.commit()
#     cursor.close()
#
#     print("User account approved!")
#
#     return render_template('adminProfile.html')
#
# @app.route("/addJobProgress")
# def addJobProgress():
#     cursor = db_conn.cursor()
#
#     cursor.execute('SELECT MAX(Job_id) FROM Job')
#     id_num = cursor.fetchall()
#     cursor.close()
#
#     if id_num == '':
#         job_id = 1
#     else:
#         job_id = int(id_num) + 1
#
#     job_title = request.form['Job_title']
#     job_description = request.form['Job_description']
#     job_requirement = request.form['Job_requirement']
#     job_apply_deadline = request.form['Job_apply_deadline']
#     job_status = request.form['Job_status']
#     job_duration = request.files['Job_duration']
#     company_id = request.args.get('Company_id')
#
#     insert_job_sql = "INSERT INTO Job VALUES (%d, %s, %s, %s, %s, %s, %d, '" + company_id + "')"
#     cursor = db_conn.cursor()
#
#     cursor.execute(insert_job_sql, (job_id, job_title, job_description, job_requirement, job_apply_deadline, job_status, job_duration))
#
#     db_conn.commit()
#
#     cursor.close()
#
#     print("Successfully Created!")
#
#     return render_template('companyProfile.html')
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
#     cursor = db_conn.cursor()
#
#     cursor.execute("SELECT * FROM Job WHERE Job_status = 'Available'")
#     rows = cursor.fetchall()
#     cursor.close()
#
#     return render_template('showInternOppurnity.html', rows=rows)
#
# @app.route("/showCurrentIntern")
# def showCurrentIntern():
#     company_id = request.args.get('Company_id')
#     cursor = db_conn.cursor()
#
#     cursor.execute(
#         "SELECT Student.Stud_id, StudentCompany.Job_id, Stud_name, Stud_email, Job_title, Intern_start_date, Intern_end_date "
#         "FROM Student, StudentCompany, Company, Job "
#         "WHERE Student.Stud_id = StudentCompany.Stud_id "
#         "AND StudentCompany.Job_id = Job.Job_id AND StudentCompany.Company_id = Company_Company_id "
#         "AND Progress_status = 'Pending' AND Stud_intern_status = 'Inactive' AND Company.Company_id = '" + company_id + "'")
#     rows = cursor.fetchall()
#     cursor.close()
#
#     return render_template('showCurrentIntern.html', rows=rows)
#
# @app.route("/applyInternshipProcess")
# def applyInternshipProcess():
#     cursor = db_conn.cursor()
#     stud_id = request.args.get('Stud_id')
#     company_id = request.args.get('Company_id')
#     job_id = request.args.get('Job_id')
#
#     insert_job_sql = "INSERT INTO StudentCompany VALUES (%s, %d, %d, 'Pending', '', '')"
#     cursor = db_conn.cursor()
#
#     cursor.execute(insert_job_sql,(stud_id, company_id, job_id))
#
#     db_conn.commit()
#     cursor.close()
#
#     return render_template('internApplicant.html')
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
#     cursor = db_conn.cursor()
#
#     cursor.execute('SELECT MAX(Logbook_id) FROM Logbook')
#     id_num = cursor.fetchall()
#
#     if id_num == '':
#         logbook_id = 1
#     else:
#         logbook_id = int(id_num) + 1
#
#     stud_id = request.form['Stud_id']
#     submission_date = date.today()
#     logbook_pdf = request.files['Logbook_pdf']
#
#     insert_logbook_sql = "INSERT INTO Logbook VALUES (%d, %s, " + submission_date + ", %s)"
#     if logbook_pdf.filename == "":
#         return "Please select a file"
#
#     try:
#         logbook_file_name_in_s3 = "logbook-id-image-" + str(logbook_id) + "_pdf_file"
#
#         cursor.execute(insert_company_sql, (logbook_id, stud_id, logbook_file_name_in_s3))
#         db_conn.commit()
#         # Uplaod image file in S3 #
#         s3 = boto3.resource('s3')
#
#         try:
#             print("Data inserted in MySQL RDS... uploading files to S3...")
#             s3.Bucket(custombucket).put_object(Key=logbook_file_name_in_s3, Body=logbook_pdf)
#             bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
#             s3_location = (bucket_location['LocationConstraint'])
#
#             if s3_location is None:
#                 s3_location = ''
#             else:
#                 s3_location = '-' + s3_location
#
#             object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
#                 s3_location,
#                 custombucket,
#                 logbook_file_name_in_s3)
#
#         except Exception as e:
#             return str(e)
#
#     finally:
#         cursor.close()
#
#     print("Submitted")
#
#     return render_template('logbookSubmission.html')
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

