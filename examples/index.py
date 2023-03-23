import pyodbc
import os
import json


def lambda_handler(event, context):
    
    # Retrieve connection information from configuration file
    #connection_detail = get_connection_info("connection.config")

    #ip = connection_detail["ip"]
    #port = connection_detail["port"]
    #namespace = connection_detail["namespace"]
    #username = connection_detail["username"]
    #password = connection_detail["password"]

    # Overrides for Portal
    ip = os.environ.get('IRISHOST')
    port = os.environ.get('IRISPORT')
    namespace = os.environ.get('NAMESPACE')
    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')
    
    #ip="35.77.83.113"
    #port="1972"
    #namespace="USER"
    #username="SuperUser"
    #password="SYS"

    print("ip: " + ip)
    print("port: " + str(port))
    print("namespace: " + namespace)
    print("username: " + username)
    print("password: " + password)

    # Create connection to InterSystems IRIS
    connection=pyodbc.connect("DRIVER={InterSystems IRIS ODBC35};SERVER="+ip+";PORT="+port+";DATABASE="+namespace+";UID="+username+";PWD="+password)
    connection.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
    connection.setencoding(encoding='utf-8')

    print("Connected to InterSystems IRIS")

    # preparating query string
    query="select Name,Email from Test.Person"
    cursor=connection.cursor()
    cursor.execute(query)
    rows=cursor.fetchall()
    data=[]
    for row in rows:
        data.append(list(row))
        print(",".join(row))

    returnjson=json.dumps(data,ensure_ascii=False)

    cursor.close()
    connection.close()
    return returnjson

def get_connection_info(file_name):
    # Initial empty dictionary to store connection details
    connections = {}

    # Open config file to get connection info
    with open(file_name) as f:
        lines = f.readlines()
        for line in lines:
            # remove all white space (space, tab, new line)
            line = ''.join(line.split())

            # get connection info
            connection_param, connection_value = line.split(":")
            connections[connection_param] = connection_value
    
    return connections