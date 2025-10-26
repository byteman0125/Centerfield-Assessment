"""
CloudWatch logging handler.
"""
import logging
import boto3
from datetime import datetime
from django.conf import settings


class CloudWatchHandler(logging.Handler):
    """Custom logging handler for AWS CloudWatch."""
    
    def __init__(self, log_group, log_stream=None, region_name=None):
        super().__init__()
        self.log_group = log_group
        self.log_stream = log_stream or f"django-{datetime.now().strftime('%Y-%m-%d')}"
        self.region_name = region_name or settings.AWS_REGION
        self.client = None
        self.enabled = False
        
        # Only initialize if AWS credentials are properly configured
        if (settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY and 
            settings.AWS_ACCESS_KEY_ID.strip() and settings.AWS_SECRET_ACCESS_KEY.strip()):
            try:
                self.client = boto3.client(
                    'logs',
                    region_name=self.region_name,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                self.enabled = True
                self._ensure_log_group_exists()
                self._ensure_log_stream_exists()
            except Exception as e:
                # If we can't initialize, just disable CloudWatch logging
                import sys
                sys.stderr.write(f"CloudWatch handler disabled: {e}\n")
                self.enabled = False
    
    def _ensure_log_group_exists(self):
        """Ensure the log group exists."""
        try:
            self.client.create_log_group(logGroupName=self.log_group)
        except self.client.exceptions.ResourceAlreadyExistsException:
            pass
    
    def _ensure_log_stream_exists(self):
        """Ensure the log stream exists."""
        try:
            self.client.create_log_stream(
                logGroupName=self.log_group,
                logStreamName=self.log_stream
            )
        except self.client.exceptions.ResourceAlreadyExistsException:
            pass
    
    def emit(self, record):
        """Emit a log record to CloudWatch."""
        if not self.enabled or not self.client:
            return
            
        try:
            log_entry = self.format(record)
            
            # Get next sequence token
            response = self.client.describe_log_streams(
                logGroupName=self.log_group,
                logStreamNamePrefix=self.log_stream
            )
            
            sequence_token = None
            for stream in response['logStreams']:
                if stream['logStreamName'] == self.log_stream:
                    sequence_token = stream.get('uploadSequenceToken')
                    break
            
            # Create log event
            log_event = {
                'timestamp': int(record.created * 1000),  # CloudWatch expects milliseconds
                'message': log_entry
            }
            
            # Send to CloudWatch
            put_kwargs = {
                'logGroupName': self.log_group,
                'logStreamName': self.log_stream,
                'logEvents': [log_event]
            }
            
            if sequence_token:
                put_kwargs['sequenceToken'] = sequence_token
            
            self.client.put_log_events(**put_kwargs)
            
        except Exception as e:
            # Fallback to basic logging if CloudWatch fails
            import sys
            sys.stderr.write(f"CloudWatch logging error: {e}\n")
            sys.stderr.write(f"Original log: {self.format(record)}\n")
