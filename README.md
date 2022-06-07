# Email Reports

A python script to generate reports based on the contents of a mongoDB database.

## QuickStart
1. Modify script:
   1. Set mongo DB settings
      1. username
      2. password
      3. seed host (some host in the cluster)
      4. DB port
      5. cluster name
      6. database name
      7. collection name
      8. Query
      9. Projection
   2. Set Report Settings
      1. Field List
      2. Email From
      3. Email To
      4. SMTP Hostname
2. Upload to a host/lambda function
   1. Must have network access to DB to query
   2. Must have network access to SMTP host
3. Schedule with EventBridge or Crontab as needed

## SlowStart
The file `lambda_function.py` contains the code needed to run the report as an AWS Lambda function. The code is well commented and there are several variables that need to be tweaked to generate the report that you want so read the code and comments closely. Sample data is included for your reference.

### **Requirements**
This script has a few requirements:
1. Access to the DB to query
   1. Network Access
   2. A user with read access to the data
   3. The "seed" host - Basically any host in the cluster
   4. The replicate set/cluster name.
      1. Run `rs.status().set` on the mongo shell to find this
   5. Obviously, both the DB and collection to search
   6. Obviously, a query, which you should make sure is indexed
   7. Semi-Optionally, a projection to decide which fields to show
      1. Having no projection might require some code skills atm
2. Some mandatory script settings
   1. A "fieldlist". Basically a list of column headers.
      1. Right now the order must match the output of mongo or it wont match with your data. Still working on making this easier.
   2. An SMTP server
      1. Network Access
3. Some script settings - See the code comments for more information
   1. A report name
   2. Email "From" address
   3. Email "To" address
   4. Attach CSV Yes/No
   5. Results in Email Yes/No
   6. Number of Results in Email
   7. Testing Mode Yes/No
4. Python 3.6+
   1. The `pymongo` python module.
5. To be scheduled somehow.

Note that you should make sure to at least enable a CSV attachment **or** results in email or you'll get an email with no results in the body and no CSV file, meaning no report.

See the sections below for your use case for more details/specifics on requirements.
### **lambda_function.py**
Schedule your Lambda function using the EventBridge system in AWS.

AWS Lambda functions which require non-standard Python modules must have those modules and their code uploaded as part of a .zip package, or included as a "layer". See https://docs.aws.amazon.com/lambda/latest/dg/python-package.html for more information.  

AWS Lambda functions pass both an "event" and "context" object into the handler function which you must configure in AWS. The default is "lambda_handler" but here we use "main". So either configure your Lambda to use "main" instead, or change main to "lambda_handler". Any code not in the handler function or not called BY the handler function will not be executed, so keep this in mind.