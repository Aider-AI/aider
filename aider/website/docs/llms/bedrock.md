---
parent: Connecting to LLMs
nav_order: 560
---

# Amazon Bedrock

Aider can connect to models provided by Amazon Bedrock.
You will need to have an AWS account with access to the Bedrock service.

To configure Aider to use the Amazon Bedrock API, you need to set up your AWS credentials.
This can be done using the AWS CLI or by setting environment variables.

## AWS CLI Configuration

If you haven't already, install the [AWS CLI](https://aws.amazon.com/cli/) and configure it with your credentials:

```bash
aws configure
```

This will prompt you to enter your AWS Access Key ID, Secret Access Key, and default region.

## Environment Variables

Alternatively, you can set the following environment variables:

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=your_preferred_region
```

You can add these to your `.env` file or your shell's configuration file (e.g., `.bashrc` or `.zshrc`).

## Running Aider with Bedrock

Once your AWS credentials are set up, you can run Aider with the `--model` command line switch, specifying the Bedrock model you want to use:

```bash
aider --model bedrock/anthropic.claude-v2
```

Or you can use the [yaml config](/docs/config/aider_conf.html) to set the model to any of the 
models supported by Amazon Bedrock.

Example `.aider.conf.yml` file:

```yaml
model: bedrock/anthropic.claude-v2
```

## Available Models

As of now, Aider supports the following Bedrock models:

- `bedrock/anthropic.claude-v2`
- `bedrock/anthropic.claude-v1`
- `bedrock/anthropic.claude-instant-v1`

Make sure you have access to these models in your AWS account before attempting to use them with Aider.

## Troubleshooting

If you encounter any issues, ensure that:

1. Your AWS credentials are correctly set up and have the necessary permissions to access Bedrock.
2. You're in a region where the Bedrock service and the specific model you're trying to use are available.
3. Your AWS account has been granted access to the Bedrock service and the specific model you're attempting to use.

For more information on Amazon Bedrock and its models, refer to the [official AWS documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html).
