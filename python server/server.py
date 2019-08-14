from flask import Flask, render_template, request, jsonify
import urllib3, requests, json
import json
import os

import numpy as np

import pandas as pd
from botocore.client import Config
import ibm_boto3

import collections

app = Flask(__name__, static_url_path='')

# On IBM Cloud Cloud Foundry, get the port number from the environment variable PORT
# When running this app on the local machine, default the port to 8000
port = int(os.getenv('PORT', 8001))

# Paste your Watson Machine Learning service apikey here
# Use the rest of the code sample as written
apikey = "JbIJi4XmJINM6pj69bPCjD72y1_sQ1tkCSkmIoAcCBAA"
ml_instance_id = "6b55548c-27a1-4a18-83ca-45f891063a38"

# Get an IAM token from IBM Cloud
url     = "https://iam.bluemix.net/oidc/token"
headers = { "Content-Type" : "application/x-www-form-urlencoded" }
data    = "apikey=" + apikey + "&grant_type=urn:ibm:params:oauth:grant-type:apikey"
IBM_cloud_IAM_uid = "bx"
IBM_cloud_IAM_pwd = "bx"
response  = requests.post( url, headers=headers, data=data, auth=( IBM_cloud_IAM_uid, IBM_cloud_IAM_pwd ) )
iam_token = response.json()["access_token"]

print(iam_token)


# NOTE: generate iam_token and retrieve ml_instance_id based on provided documentation	
header = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + iam_token, 'ML-Instance-ID': ml_instance_id}


@app.route('/')
def root():
    # get_all()
    return 'test'

def get_all():
    client = ibm_boto3.client(service_name='s3',
    ibm_api_key_id='hUMUltqH12As3Af7PldapeiD0tZGJw5V6_Rld-OfY2Da',
    ibm_auth_endpoint="https://iam.ng.bluemix.net/oidc/token",
    config=Config(signature_version='oauth'),
    endpoint_url='https://s3.us.cloud-object-storage.appdomain.cloud') # replaced with updated public us-geo

    body = client.get_object(Bucket='bundlerecommenderkmeansmodel-donotdelete-pr-0iekkdo3dtqsqh',Key='customer_activities_agg.csv')['Body']

    return pd.read_csv(body)

# example id = 3175
@app.route('/api/recommend/<customerid>', methods=['GET'])
def get_recommend(customerid):
    print (customerid) #customer id

    data_all = get_all()

        # # Get list of all products
    product_cols = list(data_all.columns.values)[2:]
    products_all = sorted([x.replace('sum(', '').replace(')', '') for x in product_cols])
    # # print(products_all)

    # df.loc[df['column_name'] == some_value]
    # print(data_all[product_cols])
    value_all = data_all[product_cols].values.tolist()
    # print(value_all)

    ## Find all clusters for all customers

    # # # NOTE: manually define and pass the array(s) of values to be scored in the next line
    payload_scoring_all = {"fields": product_cols, "values": value_all}

    response_scoring_all = requests.post('https://us-south.ml.cloud.ibm.com/v3/wml_instances/6b55548c-27a1-4a18-83ca-45f891063a38/deployments/5776b1de-5248-4443-a6af-42a08b400705/online', json=payload_scoring_all, headers=header)
    cluster_all = json.loads(response_scoring_all.text)['values']
    # print(cluster_all)

    ## Customer Cluster
    value_customer = data_all[data_all['visitorid'] == int(customerid)].values.tolist()[0][2:]
    # print(value_customer)

    # # # NOTE: manually define and pass the array(s) of values to be scored in the next line
    payload_scoring_customer = {"fields": product_cols, "values": [value_customer]}

    response_scoring_customer = requests.post('https://us-south.ml.cloud.ibm.com/v3/wml_instances/6b55548c-27a1-4a18-83ca-45f891063a38/deployments/5776b1de-5248-4443-a6af-42a08b400705/online', json=payload_scoring_customer, headers=header)
    cluster_customer = json.loads(response_scoring_customer.text)['values']
    # print(cluster_customer[-1][-1])

    ## Find all customer belonging to the same cluster
    cluster_same = [x[0:-2] for x in cluster_all if x[-1] == cluster_customer[-1][-1]]
    # print(cluster_same)

    ## Get popular products in the cluster (Sum all items and order items in desc order)
    product_cluster_sum = [sum(x) for x in zip(*cluster_same)]
    # print([sum(x) for x in zip(*cluster_same)])

    product_dict = dict(zip(products_all, product_cluster_sum))
    product_sorted = sorted(((value, key) for (key,value) in product_dict.items()), reverse=True)
    # print(product_sorted)
    
    # Remove items not used by any customers in the cluster
    print('POPULAR PRODUCTS IN CLUSTER:')
    products_cluster = [x[1] for x in product_sorted if x[0]>0]
    print(products_cluster)

    ## Filter out products the user has already purchased
    products_customer = [products_all[i] for i, v in enumerate(cluster_customer[-1][0:-2]) if v>0]
    print(products_customer)

    print('RECOMMENDED BUNDLES:')
    recommended_products = [x for x in products_cluster if x not in products_customer]
    print([x for x in products_cluster if x not in products_customer])

    return json.dumps(recommended_products)
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
