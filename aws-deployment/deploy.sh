#!/bin/bash

# AWS Fargate Deployment Script for Wake-up Call Service
set -e

# Configuration
REGION="us-east-1"
CLUSTER_NAME="wakeupcall-cluster"
SERVICE_NAME="wakeupcall-service"
TASK_FAMILY="wakeupcall-app"
ECR_REPOSITORY="wakeupcall"
IMAGE_TAG="latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment to AWS Fargate...${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install it first.${NC}"
    exit 1
fi

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${YELLOW}AWS Account ID: ${ACCOUNT_ID}${NC}"

# Build and push Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t ${ECR_REPOSITORY}:${IMAGE_TAG} .

echo -e "${YELLOW}Tagging image for ECR...${NC}"
docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}

# Login to ECR
echo -e "${YELLOW}Logging into ECR...${NC}"
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# Create ECR repository if it doesn't exist
echo -e "${YELLOW}Creating ECR repository if needed...${NC}"
aws ecr describe-repositories --repository-names ${ECR_REPOSITORY} --region ${REGION} || \
aws ecr create-repository --repository-name ${ECR_REPOSITORY} --region ${REGION}

# Push image to ECR
echo -e "${YELLOW}Pushing image to ECR...${NC}"
docker push ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}

# Update task definition with correct image URI
echo -e "${YELLOW}Updating task definition...${NC}"
sed "s/ACCOUNT-ID/${ACCOUNT_ID}/g; s/REGION/${REGION}/g" task-definition.json > task-definition-updated.json

# Register new task definition
echo -e "${YELLOW}Registering task definition...${NC}"
TASK_DEFINITION_ARN=$(aws ecs register-task-definition \
    --cli-input-json file://task-definition-updated.json \
    --region ${REGION} \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo -e "${GREEN}New task definition ARN: ${TASK_DEFINITION_ARN}${NC}"

# Update ECS service
echo -e "${YELLOW}Updating ECS service...${NC}"
aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service ${SERVICE_NAME} \
    --task-definition ${TASK_DEFINITION_ARN} \
    --region ${REGION} > /dev/null

echo -e "${GREEN}Deployment initiated successfully!${NC}"
echo -e "${YELLOW}Monitor the deployment in the AWS Console or run:${NC}"
echo -e "aws ecs describe-services --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME} --region ${REGION}"

# Cleanup
rm -f task-definition-updated.json

echo -e "${GREEN}Deployment completed!${NC}"
