"""Simple smoke test for Anthropic Claude via AWS Bedrock."""
import json
import boto3
from botocore.exceptions import ClientError

# Configuration - adjust these values
AWS_PROFILE = "tring-kavin"  # Your AWS profile name
AWS_REGION = "us-east-2"  # Your AWS region
MODEL_ID = "us.anthropic.claude-opus-4-5-20251101-v1:0"  # Claude Opus 4.5 inference profile ID

def test_bedrock_claude():
    """Test calling Claude via Bedrock."""
    try:
        # Create Bedrock client
        session = boto3.Session(profile_name=AWS_PROFILE)
        bedrock_client = session.client(
            service_name='bedrock-runtime',
            region_name=AWS_REGION
        )
        
        print(f"✓ Bedrock client created (region: {AWS_REGION}, profile: {AWS_PROFILE})")
        
        # Prepare request
        prompt = "Say 'Hello from Claude!' and tell me what 2+2 equals."
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "temperature": 0.7,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        print(f"✓ Sending request to model: {MODEL_ID}")
        
        # Invoke model
        response = bedrock_client.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(body),
            contentType='application/json',
            accept='application/json'
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        text = response_body['content'][0]['text']
        
        print(f"✓ Success! Response received:")
        print(f"\n{text}\n")
        
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        print(f"✗ AWS Error ({error_code}): {error_message}")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing AWS Bedrock with Anthropic Claude...\n")
    success = test_bedrock_claude()
    exit(0 if success else 1)