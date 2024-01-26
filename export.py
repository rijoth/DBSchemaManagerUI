@app.route("/db_graph")
def db_graph():
    if ('user' in session):
        cursor = con.cursor()
        sql = """ select to_char(sysdate,'MON-YYYY'),
          sum(d.bytes+t.bytes)/1024/1024/1024 physical_size,sum(s.bytes)/1024/1024/1024 logical_size
          from dual,dba_data_files d,dba_temp_files t,dba_segments s """
        cursor.execute(sql)
        # Generate the figure **without using pyplot**.
        x = []
        y = []
        z = []

        show below script in code
        for value in cursor:
            x.append(value[0])
            y.append(int(value[1]))
            z.append(int(value[2]))

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

@app.route("/export_schema/<schema_name>")
def export_schema(schema_name):
    if ('user' in session):
        schema_exist = False
        client = docker.from_env()
        containers = client.containers.list()
        container = client.containers.get('1ef81781c214')
        cursor = con.cursor()
        sql = """ select username from dba_users """
        cursor.execute(sql)
        for schema in cursor:
            if name == schema:
                schema_exist = True
        result = container.exec_run(cmd='sh /root/export_schema.sh')
        return render_template('export_schema.html', data = result)


@app.route("/export_schema_result")
def export_schema_result():
    if ('user' in session):
        return render_template('export_schema_result.html')


