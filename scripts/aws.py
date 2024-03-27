import boto3
import pandas as pd

# Initialize a session using Amazon S3
s3 = boto3.client('s3')
bucket_name = 'your-casinha' # S3 bucket name

# Function to check if object exists in S3 bucket
def object_exists(bucket, key):
    response = s3.list_objects_v2(Bucket=bucket, Prefix=key)
    for obj in response.get('Contents', []):
        if obj['Key'] == key:
            return True
    return False

# Function to download object from S3 and load into a string
def download_object(bucket, key):
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj['Body'].read()


# key = 'form_responses.csv'
# obj = s3.get_object(Bucket=bucket_name, Key=key)
# df = pd.read_csv(obj['Body'])

# print(df)

# print(s3.get_object(Bucket=bucket_name, Key=key)['Body'])

# print(obj['Body'].read())