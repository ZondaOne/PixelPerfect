"""
Main application module for the background removal service.
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
from app.processing import perform_background_removal, ImageProcessingError
from app.dto import JobMessageDTO, JobStatusUpdateRequestDTO, JobStatus
from app.cloudinary_config import *  # Initialize Cloudinary configuration

# Configure logging
logger = logging.getLogger(__name__)

# Create the FastAPI application
app = FastAPI(
    title="Background Removal Service",
    description="Microservice for AI-powered background removal from images with Cloudinary integration",
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
        
        logger.info("Background Removal Service with Cloudinary started successfully")
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
                "cloudinary": "configured"
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
    
    callback_url = SPRING_BOOT_CALLBACK_URL_TEMPLATE.format(job_id=job_id)
    
    try:
        logger.info(f"Sending {status_update.status} callback for job {job_id} to {callback_url}")
        
        response = await http_client.post(
            callback_url,
            json=status_update.dict(exclude_none=True)
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

MAX_RETRIES = 3  # Máximo número de intentos permitidos

async def process_message(message: AbstractIncomingMessage) -> None:
    """
    Process a message from RabbitMQ with retry logic and status updates visible to frontend.
    
    Args:
        message: The incoming message from RabbitMQ
    """
    job_id = "unknown"
    retry_count = 0

    while retry_count <= MAX_RETRIES:
        try:
            # Parse the message body as JSON
            message_body = message.body.decode("utf-8")
            message_data = json.loads(message_body)

            # Validate the message structure using Pydantic
            job_dto = JobMessageDTO(**message_data)
            job_id = job_dto.jobId

            logger.info(f"Received job {job_id} of type {job_dto.jobType} (attempt {retry_count + 1})")
            logger.info(f"Image URL: {job_dto.imageStoragePath}")

            # Only process BG_REMOVAL job type
            if job_dto.jobType != "BG_REMOVAL":
                logger.warning(f"Ignoring job {job_id} with unsupported type: {job_dto.jobType}")
                await message.ack()
                return

            # Enviar estado PROCESSING en el primer intento, RETRYING en los siguientes
            if retry_count == 0:
                status_update = JobStatusUpdateRequestDTO(status=JobStatus.PROCESSING)
            else:
                status_update = JobStatusUpdateRequestDTO(
                    status=JobStatus.RETRYING,
                    processingParams={"retryCount": retry_count}
                )
            await send_status_update(job_id, status_update)
            
            

            # Perform background removal with Cloudinary integration
            processed_image_url, processing_params = await perform_background_removal(
                job_id,
                job_dto.imageStoragePath,  # This is now a Cloudinary URL
                job_dto.jobConfig or {}
            )

            # Send COMPLETED status update with Cloudinary URL
            completed_status = JobStatusUpdateRequestDTO(
                status=JobStatus.COMPLETED,
                processedStoragePath=processed_image_url,
                processingParams=processing_params
            )
            await send_status_update(job_id, completed_status)

            # Acknowledge the message on successful processing
            await message.ack()
            logger.info(f"Job {job_id} completed successfully on attempt {retry_count + 1}")
            return  # Salir después de éxito

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message as JSON: {e}")
            await message.nack(requeue=False)
            return  # No reintentar si el JSON es inválido
        
      

        except Exception as e:
            retry_count += 1
            logger.error(f"Error processing job {job_id} on attempt {retry_count}: {e}")
            logger.error(traceback.format_exc())

            if retry_count > MAX_RETRIES:
                # Enviar estado FAILED y no reintentar más
                failed_status = JobStatusUpdateRequestDTO(
                    status=JobStatus.FAILED,
                    errorMessage=str(e)
                )
                await send_status_update(job_id, failed_status)
                await message.nack(requeue=False)
                return
            else:
                # Enviar estado RETRYING y esperar un poco antes de reintentar
                retry_status = JobStatusUpdateRequestDTO(
                    status=JobStatus.RETRYING,
                    processingParams={"retryCount": retry_count},
                    errorMessage=str(e)
                )
                await send_status_update(job_id, retry_status)
                await asyncio.sleep(2)  # Espera opcional antes de reintentar

        # Si hay error inesperado fuera del try, no queremos que quede el mensaje sin ack/nack
    # En caso extremo, nack sin requeue
    await message.nack(requeue=False)


async def start_rabbitmq_consumer() -> None:
    """
    Connect to RabbitMQ and start consuming messages.
    Implements retry logic for connection failures and automatic reconnection.
    """
    global rabbitmq_connection
    
    while True:  # Loop principal para reconexión automática
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
                
                # Reset retry counter on successful connection
                retries = 0
                
                # Keep the connection alive with better monitoring
                try:
                    while not rabbitmq_connection.is_closed:
                        await asyncio.sleep(10)  # Check every 10 seconds
                        
                        # Heartbeat check - try to get connection info
                        try:
                            await rabbitmq_connection.channel()
                        except:
                            logger.warning("Connection heartbeat failed, breaking loop")
                            break
                            
                except asyncio.CancelledError:
                    logger.info("Consumer task cancelled")
                    break
                
                logger.warning("RabbitMQ connection lost, attempting to reconnect...")
                break  # Sale del retry loop para reconectar
                
            except aio_pika.exceptions.AMQPError as e:
                logger.error(f"RabbitMQ connection error: {e}")
                
                retries += 1
                
                if retries < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds... (Attempt {retries}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Failed to connect to RabbitMQ after {max_retries} attempts, waiting 60s before retry")
                    await asyncio.sleep(60)  # Wait longer before trying the whole process again
                    break
                    
            except Exception as e:
                logger.error(f"Unexpected error in RabbitMQ consumer: {e}")
                logger.error(tracecode.format_exc())
                await asyncio.sleep(30)  # Wait before retrying
                break
        
       
        logger.info("Attempting to reconnect to RabbitMQ...")
        await asyncio.sleep(5)