"""
Main application module for the upscaling service.
Implements FastAPI app, RabbitMQ consumer, and job processing logic with Cloudinary integration.
"""

import json
import asyncio
import logging
import traceback
from typing import Dict, Any, Optional

import aio_pika
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection

from app.config import (
    RABBITMQ_URL,
    CONSUME_QUEUE_NAME,
    CONSUME_EXCHANGE_NAME,
    CONSUME_ROUTING_KEY,
    SPRING_BOOT_CALLBACK_URL_TEMPLATE,
    validate_config,
    SERVICE_HOST,
    SERVICE_PORT
)
from app.processing import perform_upscaling
from app.dto import JobMessageDTO, JobStatusUpdateRequestDTO, JobStatus
from app.cloudinary_config import *  # Initialize Cloudinary configuration

# Configure logging
logger = logging.getLogger(__name__)

# Create the FastAPI application
app = FastAPI(
    title="Upscaling Service",
    description="Microservice for AI-powered image upscaling using Real-ESRGAN with Cloudinary integration",
    version="0.2.0",
)

# Global variables for the RabbitMQ connection and HTTP client
rabbitmq_connection: Optional[AbstractRobustConnection] = None
http_client: Optional[httpx.AsyncClient] = None

@app.on_event("startup")
async def startup_event():
    """Initialize connections and start the RabbitMQ consumer on application startup."""
    global http_client
    
    try:
        # Validate configuration
        validate_config()
        
        # Create HTTP client for callbacks
        http_client = httpx.AsyncClient(timeout=30.0)
        
        # Start RabbitMQ consumer
        asyncio.create_task(start_rabbitmq_consumer())
        
        logger.info("Upscaling Service with Cloudinary started successfully")
    except Exception as e:
        logger.error(f"Failed to start the service: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on application shutdown."""
    global rabbitmq_connection, http_client
    
    logger.info("Shutting down the service...")
    
    # Close HTTP client
    if http_client:
        await http_client.aclose()
        http_client = None
    
    # Close RabbitMQ connection
    if rabbitmq_connection:
        await rabbitmq_connection.close()
        rabbitmq_connection = None
    
    logger.info("Service shutdown completed")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check RabbitMQ connection status
    rabbitmq_status = "connected" if rabbitmq_connection and not rabbitmq_connection.is_closed else "disconnected"
    
    return JSONResponse(
        content={
            "status": "healthy" if rabbitmq_status == "connected" else "degraded",
            "services": {
                "rabbitmq": rabbitmq_status,
                "cloudinary": "configured",
                "realesrgan": "available"
            }
        },
        status_code=200 if rabbitmq_status == "connected" else 503
    )

async def send_status_update(job_id: str, status_update: JobStatusUpdateRequestDTO) -> bool:
    """
    Send a status update to the Spring Boot backend.
    
    Args:
        job_id: The ID of the job being processed
        status_update: The status update payload
    
    Returns:
        bool: True if the callback was successful, False otherwise
    """
    global http_client
    
    if not http_client:
        logger.error("HTTP client not initialized")
        return False
    
    # Construct callback URL - template no longer includes /status
    callback_url = f"{SPRING_BOOT_CALLBACK_URL_TEMPLATE.format(job_id=job_id)}/status"
    
    try:
        logger.info(f"Sending {status_update.status} callback for job {job_id} to {callback_url}")
        
        response = await http_client.post(
            callback_url,
            json=status_update.dict(exclude_none=True),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        
        # Log the actual payload being sent
        logger.info(f"Callback payload: {status_update.dict(exclude_none=True)}")
        
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Callback successful for job {job_id}: {response.status_code}")
            return True
        else:
            logger.error(f"Callback failed for job {job_id}: {response.status_code} - {response.text}")
            return False
            
    except httpx.RequestError as e:
        logger.error(f"Callback request error for job {job_id}: {e}")
        return False

async def process_message(message: AbstractIncomingMessage) -> None:
    """
    Process a message from RabbitMQ.
    
    Args:
        message: The incoming message from RabbitMQ
    """
    job_id = "unknown"
    
    try:
        # Parse the message body as JSON
        message_body = message.body.decode("utf-8")
        message_data = json.loads(message_body)
        
        # Validate the message structure using Pydantic
        job_dto = JobMessageDTO(**message_data)
        job_id = job_dto.jobId
        
        logger.info(f"Received job {job_id} of type {job_dto.jobType}")
        logger.info(f"Image URL: {job_dto.imageStoragePath}")
        
        # Only process UPSCALE job type
        if job_dto.jobType != "UPSCALE":
            logger.warning(f"Ignoring job {job_id} with unsupported type: {job_dto.jobType}")
            # Acknowledge the message to remove it from the queue
            await message.ack()
            return
        
        # Send PROCESSING status update
        processing_status = JobStatusUpdateRequestDTO(status=JobStatus.PROCESSING)
        await send_status_update(job_id, processing_status)
        
        # Perform upscaling with Cloudinary integration
        try:
            processed_image_url, processing_params = await perform_upscaling(
                job_id,
                job_dto.imageStoragePath,  # This is now a Cloudinary URL
                job_dto.jobConfig or {}
            )
            
            # Send COMPLETED status update with Cloudinary URL
            completed_status = JobStatusUpdateRequestDTO(
                status=JobStatus.COMPLETED,
                processedStoragePath=processed_image_url,  # Cloudinary URL
                processingParams=processing_params
            )
            await send_status_update(job_id, completed_status)
            
            # Acknowledge the message on successful processing
            await message.ack()
            logger.info(f"Job {job_id} completed successfully with Cloudinary integration")
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            logger.error(traceback.format_exc())
            
            # Send FAILED status update
            failed_status = JobStatusUpdateRequestDTO(
                status=JobStatus.FAILED,
                errorMessage=str(e)
            )
            await send_status_update(job_id, failed_status)
            
            # Negative acknowledge without requeuing for unrecoverable errors
            await message.nack(requeue=False)
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse message as JSON: {e}")
        # This is an unrecoverable error, so don't requeue
        await message.nack(requeue=False)
        
    except Exception as e:
        logger.error(f"Unexpected error processing message: {str(e)}")
        logger.error(traceback.format_exc())
        # For unexpected errors, don't requeue to avoid potential infinite loops
        await message.nack(requeue=False)

async def start_rabbitmq_consumer() -> None:
    """
    Connect to RabbitMQ and start consuming messages.
    Implements retry logic for connection failures.
    """
    global rabbitmq_connection
    
    retry_delay = 5  # seconds
    max_retries = 12  # 1 minute at 5 second intervals
    retries = 0
    
    while retries < max_retries:
        try:
            # Connect to RabbitMQ
            logger.info(f"Connecting to RabbitMQ at {RABBITMQ_URL}")
            
            rabbitmq_connection = await aio_pika.connect_robust(RABBITMQ_URL)
            
            # Create a channel
            channel = await rabbitmq_connection.channel()
            
            # Set QoS to process one message at a time
            await channel.set_qos(prefetch_count=1)
            
            # Declare the exchange
            exchange = await channel.declare_exchange(
                CONSUME_EXCHANGE_NAME,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            # Declare the queue
            queue = await channel.declare_queue(
                CONSUME_QUEUE_NAME,
                durable=True
            )
            
            # Bind the queue to the exchange using the routing key
            await queue.bind(
                exchange=exchange,
                routing_key=CONSUME_ROUTING_KEY
            )
            
            logger.info(f"Connected to RabbitMQ, consuming from queue: {CONSUME_QUEUE_NAME}")
            logger.info("Cloudinary integration enabled for image processing")
            
            # Start consuming messages
            await queue.consume(process_message)
            
            # Keep the connection alive
            while True:
                await asyncio.sleep(1)
                if rabbitmq_connection.is_closed:
                    break
            
            logger.info("RabbitMQ connection closed")
            
        except aio_pika.exceptions.AMQPError as e:
            logger.error(f"RabbitMQ connection error: {e}")
            
            retries += 1
            
            if retries < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds... (Attempt {retries}/{max_retries})")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to RabbitMQ after {max_retries} attempts")
                break
                
        except Exception as e:
            logger.error(f"Unexpected error in RabbitMQ consumer: {e}")
            logger.error(traceback.format_exc())
            break