---
parent: Connecting to LLMs
nav_order: 560
---

# Amazon Bedrock

Aider can connect to models provided by Amazon Bedrock.
You will need to have an AWS account with access to the Bedrock service.

To configure Aider to use the Amazon Bedrock API, you need to set up your AWS credentials.
This can be done using the AWS CLI or by setting environment variables.

## Select a Model from Amazon Bedrock

Before you can use a model through Amazon Bedrock, you must "enable" the model under the **Model
Access** screen in the AWS Management Console.
To find the `Model ID`, open the **Model Catalog** area in the Bedrock console, select the model 
you want to use, and the find the `modelId` property under the "Usage" heading.

### Bedrock Inference Profiles

Amazon Bedrock has added support for a new feature called [cross-region "inference profiles."](https://aws.amazon.com/about-aws/whats-new/2024/09/amazon-bedrock-knowledge-bases-cross-region-inference/)
Some models hosted in Bedrock _only_ support these inference profiles.
If you're using one of these models, then you will need to use the `Inference Profile ID` 
instead of the `Model ID` from the **Model Catalog** screen, in the AWS Management Console.
For example, the Claude Sonnet 3.7 model, release in February 2025, exclusively supports
inference through inference profiles. To use this model, you would use the 
`us.anthropic.claude-3-7-sonnet-20250219-v1:0` Inference Profile ID.
In the Amazon Bedrock console, go to Inference and Assessment ➡️ Cross-region Inference
to find the `Inference Profile ID` value.

If you attempt to use a `Model ID` for a model that exclusively supports the Inference Profile
feature, you will receive an error message like the following:

> litellm.BadRequestError: BedrockException - b'{"message":"Invocation of model ID
anthropic.claude-3-7-sonnet-20250219-v1:0 with on-demand throughput isn\xe2\x80\x99t supported. Retry your
request with the ID or ARN of an inference profile that contains this model."}'

## AWS CLI Configuration

If you haven't already, install the [AWS CLI](https://aws.amazon.com/cli/) and configure it with your credentials:

```bash
aws configure
```

This will prompt you to enter your AWS Access Key ID, Secret Access Key, and default region.

## Environment Variables

Alternatively, you can set the following environment variables:

```bash
export AWS_REGION=your_preferred_region

# For user authentication
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key

# For profile authentication
export AWS_PROFILE=your-profile
```

You can add these to your 
[.env file](/docs/config/dotenv.html).

### Set Environment Variables with PowerShell

If you're using PowerShell on MacOS, Linux, or Windows, you can set the same AWS configuration environment variables with these commands.

```pwsh
$env:AWS_ACCESS_KEY_ID = 'your_access_key'
$env:AWS_SECRET_ACCESS_KEY = 'your_secret_key'
$env:AWS_REGION = 'us-west-2'   # Put whichever AWS region that you'd like, that the Bedrock service supports.
```

## Install boto3

The AWS Bedrock provider requires the `boto3` package in order to function correctly:

```bash
pip install boto3
```

To use aider installed via `pipx` with AWS Bedrock, you must add the `boto3` dependency to aider's virtual environment by running

```bash
pipx inject aider-chat boto3
```

You must install `boto3` dependency to aider's virtual environment installed via one-liner or uv by running

```bash
uv tool run --from aider-chat pip install boto3
```


## Running Aider with Bedrock

Once your AWS credentials are set up, you can run Aider with the `--model` command line switch, specifying the Bedrock model you want to use:

```bash
aider --model bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0
```

Sometimes it seems to help if you prefix the model name with "us.":

```bash
aider --model bedrock/us.anthropic.claude-3-5-sonnet-20240620-v1:0
```


## Available Models

To see some models available via Bedrock, run:

```bash
aider --list-models bedrock/
```

Make sure you have access to these models in your AWS account before attempting to use them with Aider.

# More info

For more information on Amazon Bedrock and its models, refer to the [official AWS documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html).

Also, see the 
[litellm docs on Bedrock](https://litellm.vercel.app/docs/providers/bedrock).
