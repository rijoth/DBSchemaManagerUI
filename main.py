import os
import cx_Oracle
from flask import Flask, render_template, redirect, url_for, request, session


app = Flask(__name__)
app.secret_key = 'ItShouldBeAnythingButSecret'

# connection object
# con = cx_Oracle.connect('sys/pass123@0.0.0.0:1521/FREEPDB1', mode=cx_Oracle.SYSDBA)
con = None
is_con = False  # check if connected


@app.route('/')
def console():
    if ('user' in session):
        return redirect(url_for('home'))
    else:
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    global is_con
    global con
    error = None
    if request.method == 'POST':
        try:
            # getting user credentials from the form
            user = request.form['username']
            password = request.form['password']
            # DB tns details
            dsn_tns = cx_Oracle.makedsn("0.0.0.0", 1521, service_name="FREEPDB1")
            # DB connection
            con = cx_Oracle.connect(
                user=user,
                password=password,
                dsn=dsn_tns,
                mode=cx_Oracle.SYSDBA
            )
            is_con = True
            session['user'] = user
            return redirect(url_for('home'))
        except cx_Oracle.DatabaseError as e:
            error = "Oracle Database Error: %s" % (e)
    else:
        error = 'Invalid Credentials. Please try again.'
    return render_template('login.html', error=error)


@app.route("/home")
def home():
    if ('user' in session):
        cursor = con.cursor()
        sql = "select username, account_status, created from dba_users"
        cursor.execute(sql)
        return render_template('home.html', data=cursor)
    return 'you are not logged in'


@app.route('/schema/<name>')
def schema_details(name):
    if ('user' in session):
        cursor = con.cursor()
        sql = """
            select
            username,
            account_status,
            created,
            user_id,
            lock_date,
            expiry_date,
            default_tablespace,
            temporary_tablespace,
            profile
            from dba_users where username = :usrname
            """
        cursor.execute(sql, usrname=name)
        return render_template('schema_detail.html', data=cursor)
    return 'you are not logged in'


# unlock schema
@app.route('/unlock/<name>')
def unlock_schema(name):
    if ('user' in session):
        cursor = con.cursor()
        cursor.execute(f"alter user {name} account unlock")
        return redirect(url_for('schema_details', name=name))
    else:
        return 'you are not logged in'


# lock schema
@app.route('/lock/<name>')
def lock_schema(name):
    if ('user' in session):
        cursor = con.cursor()
        cursor.execute(f"alter user {name} account lock")
        return redirect(url_for('schema_details', name=name))
    else:
        return 'you are not logged in'


# logout
@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/login')


if __name__ == '__main__':
    app.run(port=int(os.environ.get('PORT', '8080')), debug=True)
