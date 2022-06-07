"""A script to collect data from a MongoDB instance and email a report of that data"""

from email.message import EmailMessage
from email.headerregistry import Address
from email.utils import make_msgid
import smtplib
import os
import json
import boto3
from pymongo import MongoClient


def get_secret() -> dict:
    """Retrieves the various keys from AWS secrets manager"""
    secret_name = "*****************"
    region_name = "*****************"

    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    secret = get_secret_value_response["SecretString"]
    return json.loads(secret)


def main(event, context):
    """This is executed when run from the command line"""
    print(f"Received event: {event}\nReceived Context: {context}")
    ####################################################################################################
    ############################## Customize Report Generation Settings ################################
    ####################################################################################################
    # Must define secrets first.
    secrets = get_secret()

    ## Set database settings here
    ## All variables in this section must be set.
    db_user = secrets["db_user"]
    db_pass = secrets["db_pass"]
    seed_db_host = "DBSEEDHOSTNAMEHERE"
    db_port = "27017"  # Must be string
    srv_mode = True
    # Clustername not needed if in srv_mode
    cluster_name = "CLUSTERNAMEHERE"
    database_name = "DATABASENAMEHERE"
    db_collection = "COLLECTIONNAMEHERE"

    ## Define the DB query here
    # Format is 'query["FIELDNAME"] = "VALUE"' where FIELDNAME is the name of the mongo field to search and VALUE is the value you want to match.
    # Example: query["status"] = "Active"
    # Numeric fields should have an int passed instead of a unicode string (i.e., you might have to call int())
    # Example: query["_id"] = 95303080015199
    query = {}  # <------ Initialize query. No touch.
    query["FIELDNAME"] = "VALUE"  # <----- Specify DB query here

    # Configure which fields to show/project here
    # Format is 'projection["FIELDNAME"] = "$FIELDNAME"' where FIELDNAME is the name of the mongo field to project.
    # Example: projection["_id"] = "$_id"
    projection = {}  # <------ Initialize query. No touch.
    projection["FIELDNAME"] = "$FIELDNAME"
    projection["FIELDNAME"] = "$FIELDNAME"
    projection["FIELDNAME"] = "$FIELDNAME"

    # Set "report_name" to a human friendly name/blurb to remind the recipient what it's for.
    report_name = "REPORT NAME HERE"

    # Set the SMTP relay hostname
    smtp_server = "SMTP HOST TO SEND EMAIL WITH"

    # Set "field_list" to be the header labels for each column in your CSV file or email table. This MUST match the order of results provided by mongo.
    field_list = ["_id", "name", "type", "etc..."]

    # Set attach_csv to "True" if you want to attach a CSV file of the results. You almost certainly want to do this.
    attach_csv = True

    # Set results_in_email to "True" if you want the results sent in the body of the email in table form. (In spite of attach_csv setting)
    results_in_email = True

    # set results_in_email_count to the number of results you want to display in the body of the email.
    # Unless you know 100% for sure that there's not tons of results, probably best to limit this
    # number to something small, like 10. Set to '0' to have no limit.
    # Use with caution because you'll end up with a HUGE email if the count is high.
    results_in_email_count = 10

    # Set testing_mode to True and instead of sending an email
    # the script will print (results_in_email_count) results to the console.
    testing_mode = False

    # Who should the email appear to be from?
    email_from = "EMAILFROM@DOMAIN.COM"

    # Who should we send the email TO?
    # This list can be however long. Comma separated values
    email_to = ["EMAILTO1@DOMAIN.COM", "EMAILTO2@DOMAIN.COM"]

    ####################################################################################################
    ################################ No further customizations needed ##################################
    ####################################################################################################

    ## Collect data from mongo
    if srv_mode:
        uri = f"mongodb+srv://{db_user}:{db_pass}@{seed_db_host}/?readPreference=secondary"
    else:
        uri = f"mongodb://{db_user}:{db_pass}@{seed_db_host}:{db_port}/?replicaSet={cluster_name}&readPreference=secondary"

    with MongoClient(uri) as client:
        database = client[database_name]
        collection = database[db_collection]
        cursor = collection.find(query, projection=projection)
        result_list = []
        for row in cursor:
            result_list.append(row)

    if attach_csv:
        os.chdir("/tmp")  # Required for running in Lambda

        with open("results.csv", "wt", encoding="UTF-8") as csv_file:
            # Write the first header row
            csv_file.write(",".join(field_list) + "\n")

        # Re-open in append mode for adding further rows
        with open("results.csv", "at", encoding="UTF-8") as csv_file:
            # Iterate through each result (row), fill in missing values, add a comma after, and combine each
            for row in result_list:
                new_line = ""
                for key in field_list:
                    if key not in row:
                        row[key] = ""
                    new_line = new_line + '"' + str(row[key]) + '"' + ","
                # Write our row to the file, minus the last comma, and add a new line
                csv_file.write(new_line[:-1] + "\n")

    if not results_in_email:
        message = (
            "<html>\n<head></head>\n<body>\n<p>"
            + report_name
            + "</p>\n\n<p>Please see attached CSV file.</p>\n</body>\n</html>\n"
        )
    else:
        message = ""
        counter = results_in_email_count + 1
        for row in result_list:
            newlist = []
            if results_in_email_count != 0:
                counter -= 1
            else:
                counter += 1  # Just increase the count, no biggie
            if counter > 0:
                for key in field_list:
                    if key not in row:
                        row[key] = ""
                    row[key] = str(row[key])
                    newlist.append(
                        f'<td style="border: 1px solid black; border-collapse: collapse;">{row[key]}</td>\n'
                    )
                # Results with { and } cause the email process to wig out.
                for index, value in enumerate(newlist):
                    if "{" in value or "}" in value:
                        right_brace_stripped = value.replace("}", "\\")
                        left_brace_stripped = right_brace_stripped.replace("{", "\\")
                        newlist[index] = left_brace_stripped
                message = message + "<tr>\n" + "".join(newlist) + "</tr>\n"

        email_headers = [
            f'<th style="border: 1px solid black; border-collapse: collapse;">{x}</th>\n'
            for x in field_list
        ]
        if results_in_email_count != 0:
            header_header = f'<html>\n<head></head>\n<body>\n<p>Here is the data for: {report_name}.<br />\nA sample of {results_in_email_count} rows of data is shown here. See attached CSV for full results.</p>\n<table style="width:100%; border: 1px solid black; border-collapse: collapse;">\n<thead>\n<tr>\n'
        else:
            header_header = f'<html>\n<head></head>\n<body>\n<p>Here is the data for the {report_name} report. Total records found: {counter - 1}</p>\n<table style="width:100%; border: 1px solid black; border-collapse: collapse;">\n<thead>\n<tr>\n'
        header_body = "".join(email_headers)
        header_footer = "</tr>\n</thead>\n<tbody>\n"
        message_header = header_header + header_body + header_footer
        message_footer = "</tbody>\n</table>\n</body>\n</html>"
        message = message_header + message + message_footer

    # Create the email message.
    to_list = []
    for address in email_to:
        to_list.append(Address(addr_spec=address))
    msg = EmailMessage()
    msg["Subject"] = report_name
    msg["From"] = email_from
    msg["To"] = to_list
    # In case recipient isn't viewing in html for some reason
    msg.set_content(report_name + "\n\nPlease see attached CSV file.")
    asparagus_cid = make_msgid()
    msg.add_alternative(
        message.format(asparagus_cid=asparagus_cid[1:-1]), subtype="html"
    )  # note that we needed to peel the <> off the msgid for use in the html.

    if attach_csv:
        csv_file = open("results.csv", "r", encoding="UTF-8").read()
        msg.add_attachment(csv_file, filename="results.csv")

    # Connect to the mail server and send the message
    if testing_mode:
        print(message)
    else:
        server = smtplib.SMTP(smtp_server, 25)
        server.ehlo()
        server.send_message(msg)
        server.quit()
    return
