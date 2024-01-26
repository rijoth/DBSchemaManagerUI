import os
import base64
from io import BytesIO
import cx_Oracle
import docker
from flask import Flask, render_template, redirect, url_for, request, session
from matplotlib.figure import Figure


app = Flask(__name__)
app.secret_key = 'ItShouldBeAnythingButSecret'

# connection object
# con = cx_Oracle.connect('sys/pass123@0.0.0.0:1521/FREEPDB1', mode=cx_Oracle.SYSDBA)
con = None
is_con = False  # check if connected

# global variables
g_change_pass  = False


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


# home page
@app.route("/home")
def home():
    if ('user' in session):
        cursor = con.cursor()
        sql = "select username, account_status, created from dba_users order by username asc"
        cursor.execute(sql)
        return render_template('home.html', data=cursor)
    return 'you are not logged in'


# schema details 
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
        return render_template('schema_detail.html', data=cursor, change_pass=g_change_pass)
    return 'you are not logged in'


# schema object details
@app.route('/schema/<name>/<obj>')
def object_details(name, obj):
    if ('user' in session):
        cursor = con.cursor()
        sql = """
            select
            OBJECT_NAME,
            OBJECT_ID,
            CREATED,
            LAST_DDL_TIME,
            TIMESTAMP,
            STATUS,
            APPLICATION,
            DATA_OBJECT_ID,
            DEFAULT_COLLATION,
            OWNER
            from dba_objects where owner = :usrname and object_type = :obj_type
            """
        cursor.execute(sql, usrname=name, obj_type=obj)
        return render_template('obj_details.html', data=cursor, owner=name, obj=obj)
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


# create schema
@app.route("/create_schema", methods=['GET', 'POST'])
def create_schema():
    if ('user' in session):
        if request.method == 'POST':
            schema_name = request.form['schema_name']
            schema_pass = request.form['schema_pass']
            schema_pass_conf = request.form['schema_passConf']
            if schema_pass == schema_pass_conf:
                cursor = con.cursor()
                cursor.execute(f"create user {schema_name} identified by {schema_pass}")
                cursor.execute(f"grant create session to {schema_name}")
                # return 'done'  # replace this with proper setup later
                return redirect(url_for('schema_details', name=schema_name))
            else:
                return render_template('create_schema.html',
                                       error="Sorry, the password's entered doesn't match")
        else:
            cursor_ts = con.cursor()  # tablespace
            sql = """ select tablespace_name from dba_tablespaces """
            cursor_ts.execute(sql)
            return render_template('create_schema.html',
                                   data_ts=cursor_ts, error="")


# create schema
@app.route("/change_pass/<name>", methods=['GET', 'POST'])
def change_pass(name):
    if ('user' in session):
        if request.method == 'POST':
            schema_name = request.form['schema_name']
            schema_pass = request.form['schema_pass']
            cursor = con.cursor()
            cursor.execute(f"alter user {schema_name} identified by {schema_pass}")
            # return 'done'  # replace this with proper setup later
            g_change_pass = True
            return redirect(url_for('schema_details', name=schema_name))
        else:
            return render_template('change_pass.html', name=name)


@app.route("/export_schema")
def export_schema():
    if ('user' in session):
        cursor = con.cursor()
        sql = """ select username from dba_users """
        cursor.execute(sql)
        return render_template('export_schema.html', data = cursor)


@app.route("/export_schema_result")
def export_schema_result():
    if ('user' in session):
        return render_template('export_schema_result.html')


@app.route("/db_graph")
def db_graph():
    if ('user' in session):
        cursor = con.cursor()
        sql = """ select to_char(sysdate,'MON-YYYY'),
          sum(d.bytes+t.bytes)/1024/1024/1024 physical_size,sum(s.bytes)/1024/1024/1024 logical_size
          from dual,dba_data_files d,dba_temp_files t,dba_segments s """
        cursor.execute(sql)
        # Generate the figure **without using pyplot**.
        x = ['SEPT-23', 'OCT-23', 'NOV-23']
        y = [150, 180, 200]
        z = [100, 160, 230]

       # show below script in code
       # for value in cursor:
       #     x.append(value[0])
       #     y.append(int(value[1]))
       #     z.append(int(value[2]))

        fig = Figure()
        ax = fig.subplots()
        ax.set_title("DB Growth")
        ax.set_xlabel("Month")
        ax.set_ylabel("DB Size")
        ax.plot(x, y, color='g')
        ax.plot(x, z, color='orange')
        # Save it to a temporary buffer.
        buf = BytesIO()
        fig.savefig(buf, format="png")
        # Embed the result in the html output.
        data = base64.b64encode(buf.getbuffer()).decode("ascii")
        return render_template('db_graph.html', data=data)



# logout
@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/login')


if __name__ == '__main__':
    app.run(port=int(os.environ.get('PORT', '8080')), debug=True)
