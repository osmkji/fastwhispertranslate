import json
import redis
import time
import signal
import threading
import logging
import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# Load .env file
load_dotenv()

from services.translator import TranslatorService
from services.exporter import ExporterService
from services.transcriber_service import TranscriberService

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - STT-WORKER - %(levelname)s - %(message)s'
)
logger = logging.getLogger('stt-worker')

shutdown_event = threading.Event()

def signal_handler(sig, frame):
    logger.info("Signal received. Shutting down worker gracefully after current job finishes...")
    shutdown_event.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def heartbeat_loop(r):
    while not shutdown_event.is_set():
        try:
            r.set('laravel-database-worker_last_ping', int(time.time()))
        except Exception as e:
            logger.error(f"Failed to ping Redis: {e}")
        time.sleep(10)

def main():
    # Load Redis config from environment
    redis_host = os.environ.get('REDIS_HOST', 'localhost')
    redis_port = int(os.environ.get('REDIS_PORT', 6379))
    redis_db = int(os.environ.get('REDIS_DB', 0))
    
    # Connect to Redis
    r = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
    
    # Initialize Services
    translator_service = TranslatorService()
    exporter_service = ExporterService()
    transcriber_service = TranscriberService()

    # Start heartbeat thread
    heartbeat_thread = threading.Thread(target=heartbeat_loop, args=(r,), daemon=True)
    heartbeat_thread.start()

    logger.info("STT Worker is starting with ThreadPoolExecutor... waiting for tasks.")

    # Initialize ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as executor:
        while not shutdown_event.is_set():
            try:
                # Block until a message is available (small timeout to check shutdown flag)
                result = r.blpop([
                    'laravel-database-transcription_requests', 
                    'laravel-database-translation_requests', 
                    'laravel-database-export_requests'
                ], timeout=2)
                
                if result:
                    queue_name, data = result
                    payload = json.loads(data)
                    
                    project_id = payload.get('project_id')
                    job_id = payload.get('job_id')
                    
                    # Push running status for transcription/translation jobs
                    if 'export_requests' not in queue_name:
                        running_payload = {
                            'status': 'running',
                            'project_id': project_id,
                            'job_id': job_id
                        }
                        r.rpush('laravel-database-transcription_results', json.dumps(running_payload))
                    
                    # Dispatch to appropriate service
                    if 'export_requests' in queue_name:
                        executor.submit(exporter_service.process, payload, r, shutdown_event)
                    elif 'translation_requests' in queue_name:
                        executor.submit(translator_service.process, payload, r)
                    else:
                        executor.submit(transcriber_service.process, payload, r)
                        
            except Exception as e:
                logger.error(f"Worker encountered an error in main loop: {e}")
                time.sleep(2)
                
        logger.info("Worker has shut down cleanly. Waiting for active threads to finish...")

if __name__ == '__main__':
    main()
