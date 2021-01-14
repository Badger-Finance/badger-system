import logging
import boto3
from botocore.exceptions import ClientError

""""
From: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html#presigned-urls
assuming IAM user using AWS Signature Version 4 is the caller in which case the url is valid for 7 days
see: https://aws.amazon.com/premiumsupport/knowledge-center/presigned-url-s3-bucket-expiration/
"""

def create_presigned_url(fileName, expiration=604800):
    """Generate a presigned URL to share an S3 object
    :param fileName: ...
    :param expiration: Time in seconds for the presigned URL to remain valid. One week.
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client('s3')

    bucket_name = 'badger-json'
    upload_file_key = 'rewards/' + fileName
    try:
        response = s3_client.generate_presigned_url('get_object', # AWS method to be used for presigned URL
                                                     Params={'Bucket': bucket_name,
                                                            'Key': upload_file_key},
                                                    ExpiresIn=expiration)
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response
